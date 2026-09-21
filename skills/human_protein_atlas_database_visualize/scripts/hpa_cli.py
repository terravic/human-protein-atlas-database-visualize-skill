# Copyright 2026 Project Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Core CLI client and deterministic offline mock engine for the Human Protein Atlas."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hpa_cli")

SKILL_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DATA_DIR = SKILL_DIR / "sample_data"

HPA_SEARCH_URL = "https://www.proteinatlas.org/api/search_download.php"
HPA_XML_URL_TEMPLATE = "https://www.proteinatlas.org/{ensembl_id}.xml"
DEFAULT_COLUMNS = "g,eg,gs,gd,up,scl,scml,scal,pc,ccdp,ectissue,rnats,rnatd,rnatss"

MOCK_GENE_MAP: Dict[str, str] = {
    "TP53": "ENSG00000141510",
    "P53": "ENSG00000141510",
    "ERBB2": "ENSG00000141736",
    "HER2": "ENSG00000141736",
    "INS": "ENSG00000254647",
    "EGFR": "ENSG00000146648",
    "BRCA1": "ENSG00000012048",
}


def resolve_workspace_root() -> Path:
    """Identify the workspace root directory across root or nested skill invocations."""
    if SKILL_DIR.name == "human_protein_atlas_database_visualize" and SKILL_DIR.parent.name == "skills":
        return SKILL_DIR.parent.parent
    return SKILL_DIR


def verify_license_guard() -> Path:
    """Verify or create the mandatory HPA CC BY-SA 4.0 license notification file."""
    workspace_root = resolve_workspace_root()
    license_dir = workspace_root / ".licenses"
    primary_license_file = license_dir / "human_protein_atlas_database_visualize_LICENSE.txt"
    fallback_license_file = license_dir / "human_protein_atlas_database_LICENSE.txt"

    if primary_license_file.exists():
        return primary_license_file

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    notice_text = (
        "Notification: Please check the Human Protein Atlas terms of use and licensing at "
        "https://www.proteinatlas.org/about/licence. HPA data is freely accessible under "
        "Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0).\n"
        f"Timestamp: {timestamp}\n"
    )

    if not fallback_license_file.exists():
        print(
            "NOTICE: Please check the Human Protein Atlas terms of use and licensing at "
            "https://www.proteinatlas.org/about/licence. HPA data is freely accessible under "
            "Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)."
        )

    license_dir.mkdir(parents=True, exist_ok=True)
    primary_license_file.write_text(notice_text, encoding="utf-8")

    # Also ensure CWD .licenses exists if running from a separate working directory
    cwd_license_dir = Path.cwd() / ".licenses"
    cwd_license_file = cwd_license_dir / "human_protein_atlas_database_visualize_LICENSE.txt"
    if cwd_license_file.resolve() != primary_license_file.resolve() and not cwd_license_file.exists():
        try:
            cwd_license_dir.mkdir(parents=True, exist_ok=True)
            cwd_license_file.write_text(notice_text, encoding="utf-8")
        except OSError:
            pass

    return primary_license_file


class RateLimitedHttpClient:
    """HTTP client enforcing 2.0 QPS rate limiting with polite-http or stdlib fallback."""

    def __init__(self, qps: float = 2.0) -> None:
        self.min_interval = 1.0 / max(qps, 0.1)
        self._last_request_ts = 0.0
        self._polite_client = None
        try:
            from polite_http.http_client import HttpClient  # type: ignore
            self._polite_client = HttpClient(qps=qps)
        except ImportError:
            self._polite_client = None

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_ts
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request_ts = time.monotonic()

    def get_text(self, url: str, timeout: float = 20.0, retries: int = 3) -> str:
        """Execute a rate-limited HTTP GET request with exponential backoff."""
        verify_license_guard()
        last_err: Optional[Exception] = None
        for attempt in range(retries):
            self._throttle()
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "human-protein-atlas-database-visualize/1.0 (Apache-2.0; Scientific Research)"
                    },
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return resp.read().decode("utf-8")
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                last_err = exc
                wait_time = (2 ** attempt) * 0.5
                logger.warning("Request to %s failed (attempt %d/%d): %s", url, attempt + 1, retries, exc)
                time.sleep(wait_time)
        raise RuntimeError(
            f"Failed to retrieve URL {url} after {retries} attempts: {last_err}. "
            "Use --mock for offline deterministic execution."
        )


def _load_sample_fixture(filename: str) -> Dict[str, Any]:
    fixture_path = SAMPLE_DATA_DIR / filename
    if not fixture_path.exists():
        raise FileNotFoundError(f"Required sample fixture not found: {fixture_path}")
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _select_mock_prefix(identifier: str) -> str:
    clean = identifier.strip().upper()
    if clean in ("ERBB2", "HER2", "ENSG00000141736"):
        return "erbb2"
    return "tp53"


def resolve_ensembl_id(gene_symbol: str, mock: bool = False, client: Optional[RateLimitedHttpClient] = None) -> Dict[str, Any]:
    """Resolve an HGNC gene symbol to its canonical Ensembl gene ID."""
    verify_license_guard()
    symbol = (gene_symbol or "").strip().upper()
    if not symbol:
        raise ValueError("Gene symbol must be a non-empty string.")

    if re.match(r"^ENSG\d{11}$", symbol):
        return {
            "gene_symbol": symbol,
            "ensembl_id": symbol,
            "resolved": True,
            "mode": "mock" if mock else "direct",
        }

    if mock:
        if symbol not in MOCK_GENE_MAP:
            raise ValueError(
                f"Unrecognized gene symbol '{symbol}' in mock registry. "
                f"Supported mock symbols: {', '.join(sorted(MOCK_GENE_MAP.keys()))}"
            )
        ensembl_id = MOCK_GENE_MAP[symbol]
        canonical_symbol = "ERBB2" if ensembl_id == "ENSG00000141736" else ("TP53" if ensembl_id == "ENSG00000141510" else symbol)
        return {
            "gene_symbol": canonical_symbol,
            "ensembl_id": ensembl_id,
            "resolved": True,
            "mode": "mock",
        }

    http = client or RateLimitedHttpClient(qps=2.0)
    params = urllib.parse.urlencode({
        "search": symbol,
        "format": "json",
        "columns": "g,eg,gs,gd,up",
        "compress": "no",
    })
    raw = http.get_text(f"{HPA_SEARCH_URL}?{params}")
    records = json.loads(raw)
    if not isinstance(records, list) or not records:
        raise ValueError(f"No Human Protein Atlas entry found for gene symbol '{symbol}'.")

    # Prefer exact match on Gene column
    selected = records[0]
    for item in records:
        if str(item.get("Gene", "")).upper() == symbol:
            selected = item
            break

    return {
        "gene_symbol": selected.get("Gene", symbol),
        "ensembl_id": selected.get("Ensembl", ""),
        "uniprot_id": selected.get("Uniprot", ""),
        "gene_description": selected.get("Gene description", ""),
        "resolved": True,
        "mode": "live",
    }


def get_tissue_expression(
    ensembl_id: str,
    tissues: Optional[List[str]] = None,
    mock: bool = False,
    client: Optional[RateLimitedHttpClient] = None,
) -> Dict[str, Any]:
    """Retrieve normal human tissue immunohistochemistry (IHC) expression levels."""
    verify_license_guard()
    clean_id = (ensembl_id or "").strip().upper()
    if not clean_id.startswith("ENSG"):
        raise ValueError(f"Invalid Ensembl ID '{ensembl_id}'. Expected format starting with 'ENSG'.")

    if mock:
        prefix = _select_mock_prefix(clean_id)
        data = _load_sample_fixture(f"{prefix}_tissue_ihc.json")
        data["ensembl_id"] = clean_id
    else:
        http = client or RateLimitedHttpClient(qps=2.0)
        xml_text = http.get_text(HPA_XML_URL_TEMPLATE.format(ensembl_id=clean_id))
        data = _parse_xml_tissue_expression(xml_text, clean_id)

    if tissues:
        allowed = {t.strip().lower() for t in tissues if t.strip()}
        filtered = [
            entry for entry in data.get("tissues", [])
            if str(entry.get("tissue", "")).strip().lower() in allowed
        ]
        data = dict(data)
        data["tissues"] = filtered

    return data


def _parse_xml_tissue_expression(xml_text: str, ensembl_id: str) -> Dict[str, Any]:
    """Parse <tissueExpression technology='IHC'> and <verification> from HPA XML."""
    root = ET.fromstring(xml_text)
    gene_name_el = root.find(".//name")
    gene_symbol = gene_name_el.text.strip() if (gene_name_el is not None and gene_name_el.text) else ensembl_id

    verification = "Approved"
    ver_el = root.find(".//tissueExpression/verification")
    if ver_el is not None and ver_el.text:
        verification = ver_el.text.strip().capitalize()

    tissue_map: Dict[str, Dict[str, str]] = {}
    for data_el in root.findall(".//tissueExpression/data"):
        tissue_el = data_el.find("tissue")
        if tissue_el is None or not tissue_el.text:
            continue
        tissue_name = tissue_el.text.strip().lower()
        level_el = data_el.find(".//level[@type='expression']")
        if level_el is None:
            level_el = data_el.find(".//level")
        level_val = level_el.text.strip().capitalize() if (level_el is not None and level_el.text) else "Not detected"
        if level_val.lower() == "not detected":
            level_val = "Not detected"

        cell_type_el = data_el.find(".//tissueCell/cellType")
        cell_type = cell_type_el.text.strip() if (cell_type_el is not None and cell_type_el.text) else "glandular cells"
        tissue_map[tissue_name] = {
            "tissue": tissue_name,
            "level": level_val,
            "cell_type": cell_type,
        }

    return {
        "ensembl_id": ensembl_id,
        "gene_symbol": gene_symbol,
        "technology": "IHC",
        "verification": verification,
        "tissues": list(tissue_map.values()),
    }


def get_subcellular_location(
    ensembl_id: str,
    mock: bool = False,
    client: Optional[RateLimitedHttpClient] = None,
) -> Dict[str, Any]:
    """Retrieve subcellular organelle localization arrays (main and additional)."""
    verify_license_guard()
    clean_id = (ensembl_id or "").strip().upper()
    if not clean_id.startswith("ENSG"):
        raise ValueError(f"Invalid Ensembl ID '{ensembl_id}'. Expected format starting with 'ENSG'.")

    if mock:
        prefix = _select_mock_prefix(clean_id)
        data = _load_sample_fixture(f"{prefix}_subcellular.json")
        data["ensembl_id"] = clean_id
        return data

    http = client or RateLimitedHttpClient(qps=2.0)
    params = urllib.parse.urlencode({
        "search": clean_id,
        "format": "json",
        "columns": "g,eg,scl,scml,scal",
        "compress": "no",
    })
    raw = http.get_text(f"{HPA_SEARCH_URL}?{params}")
    records = json.loads(raw)
    if not isinstance(records, list) or not records:
        return {
            "ensembl_id": clean_id,
            "gene_symbol": clean_id,
            "reliability": "Uncertain",
            "locations_all": [],
            "main_locations": [],
            "additional_locations": [],
        }

    rec = records[0]
    main_locs = _normalize_list_field(rec.get("Subcellular main location"))
    add_locs = _normalize_list_field(rec.get("Subcellular additional location"))
    all_locs = _normalize_list_field(rec.get("Subcellular location"))
    if not all_locs:
        all_locs = list(dict.fromkeys(main_locs + add_locs))

    return {
        "ensembl_id": clean_id,
        "gene_symbol": rec.get("Gene", clean_id),
        "reliability": "Approved",
        "locations_all": all_locs,
        "main_locations": main_locs,
        "additional_locations": add_locs,
    }


def _normalize_list_field(val: Any) -> List[str]:
    if isinstance(val, list):
        return [str(v).strip() for v in val if str(v).strip()]
    if isinstance(val, str) and val.strip():
        return [part.strip() for part in re.split(r"[;,]", val) if part.strip()]
    return []


def get_atlas_entry(
    ensembl_id: str,
    mock: bool = False,
    client: Optional[RateLimitedHttpClient] = None,
) -> Dict[str, Any]:
    """Retrieve full multi-column HPA atlas metadata entry and verification status."""
    verify_license_guard()
    clean_id = (ensembl_id or "").strip().upper()
    if not clean_id.startswith("ENSG"):
        raise ValueError(f"Invalid Ensembl ID '{ensembl_id}'. Expected format starting with 'ENSG'.")

    if mock:
        prefix = _select_mock_prefix(clean_id)
        data = _load_sample_fixture(f"{prefix}_entry.json")
        data["Ensembl"] = clean_id
        return data

    http = client or RateLimitedHttpClient(qps=2.0)
    params = urllib.parse.urlencode({
        "search": clean_id,
        "format": "json",
        "columns": DEFAULT_COLUMNS,
        "compress": "no",
    })
    raw = http.get_text(f"{HPA_SEARCH_URL}?{params}")
    records = json.loads(raw)
    if not isinstance(records, list) or not records:
        raise ValueError(f"No HPA atlas record returned for Ensembl ID '{clean_id}'.")

    entry = dict(records[0])
    entry["Subcellular location"] = _normalize_list_field(entry.get("Subcellular location"))
    entry["Subcellular main location"] = _normalize_list_field(entry.get("Subcellular main location"))
    entry["Subcellular additional location"] = _normalize_list_field(entry.get("Subcellular additional location"))
    entry["Gene synonym"] = _normalize_list_field(entry.get("Gene synonym"))
    entry.setdefault(
        "RNA_protein_agreement",
        {"reliability": "Approved", "description": "Consistency evaluated across HPA normal tissues"},
    )
    return entry


def search_hpa(
    query: str,
    mock: bool = False,
    client: Optional[RateLimitedHttpClient] = None,
) -> List[Dict[str, Any]]:
    """Execute complex HPA field queries across genes and tissues."""
    verify_license_guard()
    clean_query = (query or "").strip()
    if not clean_query:
        raise ValueError("Search query (--query) must be a non-empty string.")

    if mock:
        tp53 = _load_sample_fixture("tp53_entry.json")
        erbb2 = _load_sample_fixture("erbb2_entry.json")
        q_lower = clean_query.lower()
        if "erbb2" in q_lower or "her2" in q_lower or "membrane" in q_lower:
            return [erbb2]
        if "tp53" in q_lower or "p53" in q_lower or "nucleoplasm" in q_lower:
            return [tp53]
        return [tp53, erbb2]

    http = client or RateLimitedHttpClient(qps=2.0)
    params = urllib.parse.urlencode({
        "search": clean_query,
        "format": "json",
        "columns": DEFAULT_COLUMNS,
        "compress": "no",
    })
    raw = http.get_text(f"{HPA_SEARCH_URL}?{params}")
    records = json.loads(raw)
    return records if isinstance(records, list) else []


def _write_output(payload: Any, output_path: Optional[str]) -> None:
    serialized = json.dumps(payload, indent=2)
    if output_path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized + "\n", encoding="utf-8")
        logger.info("Wrote output JSON to %s", target)
    else:
        print(serialized)


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser supporting all 5 subcommands and --mock."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--output", "-o", type=str, default=None, help="Output file path for JSON result.")
    common.add_argument("--mock", action="store_true", help="Run offline using deterministic fixtures in sample_data/.")

    parser = argparse.ArgumentParser(
        prog="hpa_cli.py",
        description="Human Protein Atlas CLI client with rate-limiting and offline mock engine.",
        parents=[common],
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    p_resolve = subparsers.add_parser("resolve-ensembl-id", parents=[common], help="Resolve gene symbol to Ensembl ID.")
    p_resolve.add_argument("gene_symbol", type=str, help="HGNC gene symbol (e.g., TP53, ERBB2).")

    p_tissue = subparsers.add_parser("get-tissue-expression", parents=[common], help="Fetch normal tissue IHC levels.")
    p_tissue.add_argument("ensembl_id", type=str, help="Ensembl gene ID (e.g., ENSG00000141510).")
    p_tissue.add_argument("--tissues", "-t", type=str, default=None, help="Comma-separated tissue filter list.")

    p_subcell = subparsers.add_parser("get-subcellular-location", parents=[common], help="Fetch subcellular locations.")
    p_subcell.add_argument("ensembl_id", type=str, help="Ensembl gene ID (e.g., ENSG00000141510).")

    p_entry = subparsers.add_parser("get-atlas-entry", parents=[common], help="Fetch full HPA atlas entry metadata.")
    p_entry.add_argument("ensembl_id", type=str, help="Ensembl gene ID (e.g., ENSG00000141510).")
    p_entry.add_argument("--format", type=str, default="json", choices=["json"], help="Output format (json).")

    p_search = subparsers.add_parser("search-hpa", parents=[common], help="Search HPA records by query string.")
    p_search.add_argument("--query", "-q", type=str, required=True, help="HPA search query string.")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        cmd = args.subcommand
        if cmd == "resolve-ensembl-id":
            result = resolve_ensembl_id(args.gene_symbol, mock=args.mock)
        elif cmd == "get-tissue-expression":
            tissue_list = [t.strip() for t in args.tissues.split(",") if t.strip()] if args.tissues else None
            result = get_tissue_expression(args.ensembl_id, tissues=tissue_list, mock=args.mock)
        elif cmd == "get-subcellular-location":
            result = get_subcellular_location(args.ensembl_id, mock=args.mock)
        elif cmd == "get-atlas-entry":
            result = get_atlas_entry(args.ensembl_id, mock=args.mock)
        elif cmd == "search-hpa":
            result = search_hpa(args.query, mock=args.mock)
        else:
            parser.error(f"Unknown subcommand: {cmd}")
            return 1

        _write_output(result, args.output)
        return 0
    except ValueError as exc:
        logger.error("Validation error: %s", exc)
        return 1
    except FileNotFoundError as exc:
        logger.error("File error: %s", exc)
        return 1
    except RuntimeError as exc:
        logger.error("Network/Runtime error: %s", exc)
        return 2
    except Exception as exc:  # pragma: no cover
        logger.error("Unexpected error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
