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

"""Anatomical IHC tissue expression grouping, numerical scoring, and heatmap rendering engine."""

from __future__ import annotations

import argparse
import html
import json
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("visualize_tissue_ihc")

SKILL_DIR = Path(__file__).resolve().parent.parent
MAPPING_PATH = SKILL_DIR / "references" / "tissue_organ_mapping.json"

LEVEL_TO_SCORE: Dict[str, int] = {
    "high": 3,
    "medium": 2,
    "low": 1,
    "not detected": 0,
}

# Heatmap concentration color transition:
# Surface Background (Not detected) -> Vibrant Teal (#0D9488) -> Vivid Indigo (#4F46E5) -> Deep Rose (#E11D48)
BADGE_COLORS: Dict[str, str] = {
    "High": "#E11D48",
    "Medium": "#4F46E5",
    "Low": "#0D9488",
    "Not detected": "#787774",
}

CANONICAL_ORGAN_SYSTEMS: List[str] = [
    "Central Nervous System",
    "Cardiovascular",
    "Digestive",
    "Endocrine",
    "Immune / Lymphoid",
    "Musculoskeletal",
    "Reproductive",
    "Respiratory",
    "Urinary",
    "Integumentary",
]


def load_tissue_mapping() -> Dict[str, Dict[str, str]]:
    """Load standardized tissue-to-organ-system ontology from references/."""
    if not MAPPING_PATH.exists():
        raise FileNotFoundError(f"Tissue organ mapping file not found: {MAPPING_PATH}")
    return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))


def analyze_tissue_ihc(
    raw_ihc: Dict[str, Any],
    mapping: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Group normal human tissues into 10 organ systems and compute quantitative IHC scores."""
    organ_map = mapping or load_tissue_mapping()
    organ_map_lower = {k.lower(): v for k, v in organ_map.items()}

    tissues_list = raw_ihc.get("tissues", [])
    organ_systems: Dict[str, List[Dict[str, Any]]] = {sys_name: [] for sys_name in CANONICAL_ORGAN_SYSTEMS}

    counts = {
        "High": 0,
        "Medium": 0,
        "Low": 0,
        "Not detected": 0,
    }

    for entry in tissues_list:
        tissue_name = str(entry.get("tissue", "")).strip()
        if not tissue_name:
            continue
        raw_level = str(entry.get("level", "Not detected")).strip()
        norm_key = raw_level.lower()
        score = LEVEL_TO_SCORE.get(norm_key, 0)
        canonical_level = (
            "High" if score == 3 else
            "Medium" if score == 2 else
            "Low" if score == 1 else
            "Not detected"
        )
        counts[canonical_level] += 1

        meta = organ_map_lower.get(tissue_name.lower(), {
            "organ_system": "Musculoskeletal",
            "organ": tissue_name.lower(),
            "color": "#0D9488",
            "uberon_id": "UBERON:0000479",
        })
        sys_name = meta.get("organ_system", "Musculoskeletal")
        if sys_name not in organ_systems:
            organ_systems[sys_name] = []

        organ_systems[sys_name].append({
            "tissue": tissue_name,
            "organ": meta.get("organ", tissue_name),
            "level": canonical_level,
            "score": score,
            "cell_type": entry.get("cell_type", "glandular cells"),
            "uberon_id": meta.get("uberon_id", "UBERON:0000479"),
            "color": meta.get("color", "#0D9488"),
            "badge_color": BADGE_COLORS[canonical_level],
        })

    organ_system_metrics: Dict[str, Dict[str, Any]] = {}
    non_empty_systems: Dict[str, List[Dict[str, Any]]] = {}
    for sys_name, items in organ_systems.items():
        if not items:
            continue
        items_sorted = sorted(items, key=lambda x: (-x["score"], x["tissue"]))
        non_empty_systems[sys_name] = items_sorted
        mean_score = round(sum(float(i["score"]) for i in items_sorted) / len(items_sorted), 2)
        max_score = max(i["score"] for i in items_sorted)
        if mean_score >= 2.2:
            sys_color = "#E11D48"
        elif mean_score >= 1.5:
            sys_color = "#4F46E5"
        elif mean_score >= 0.5:
            sys_color = "#0D9488"
        else:
            sys_color = "#787774"
        organ_system_metrics[sys_name] = {
            "organ_system": sys_name,
            "tissue_count": len(items_sorted),
            "organ_score": mean_score,
            "max_score": max_score,
            "system_color": sys_color,
        }

    ranked_systems = sorted(
        organ_system_metrics.values(),
        key=lambda m: (-m["organ_score"], -m["tissue_count"], m["organ_system"]),
    )

    return {
        "ensembl_id": raw_ihc.get("ensembl_id", ""),
        "gene_symbol": raw_ihc.get("gene_symbol", ""),
        "verification": raw_ihc.get("verification", "Approved"),
        "total_tissues_profiled": len(tissues_list),
        "high_expression_count": counts["High"],
        "medium_expression_count": counts["Medium"],
        "low_expression_count": counts["Low"],
        "not_detected_count": counts["Not detected"],
        "organ_systems": non_empty_systems,
        "organ_system_scores": {m["organ_system"]: m["organ_score"] for m in ranked_systems},
        "ranked_organ_systems": ranked_systems,
    }


def render_tissue_ihc_html(summary: Dict[str, Any]) -> str:
    """Render single-level bento cells and flat row dividers for anatomical IHC scores."""
    cards_html: List[str] = []
    organ_systems = summary.get("organ_systems", {})
    ranked_meta = summary.get("ranked_organ_systems", [])

    for sys_meta in ranked_meta:
        sys_name = sys_meta["organ_system"]
        organ_score = sys_meta["organ_score"]
        sys_color = sys_meta["system_color"]
        tissues = organ_systems.get(sys_name, [])
        pct = min(100, int(round((organ_score / 3.0) * 100)))

        rows: List[str] = []
        for t in tissues:
            badge_bg = t["badge_color"]
            t_name = html.escape(t["tissue"])
            u_id = html.escape(t["uberon_id"])
            c_type = html.escape(t["cell_type"])
            lvl = html.escape(t["level"])
            scr = t["score"]
            if scr == 0:
                badge_html = (
                    f'<span class="px-2 py-0.5 rounded font-mono text-xs" '
                    f'style="border: 1px solid var(--border-color); color: var(--text-secondary);">'
                    f'{lvl} ({scr})</span>'
                )
            else:
                badge_html = (
                    f'<span class="px-2 py-0.5 rounded font-mono font-semibold text-xs text-white" '
                    f'style="background-color:{badge_bg};">{lvl} ({scr})</span>'
                )
            rows.append(
                f'<div class="flex items-center justify-between py-2 border-b text-xs" style="border-color: var(--border-color);">'
                f'<div><span class="font-semibold capitalize">{t_name}</span> '
                f'<span class="font-mono" style="color: var(--text-secondary);">({u_id}, {c_type})</span></div>'
                f'{badge_html}</div>'
            )

        cards_html.append(
            f'<div class="organ-system-card dashboard-card p-4">'
            f'<div class="flex items-center justify-between mb-2">'
            f'<span class="font-bold text-sm" style="color:{sys_color}">{html.escape(sys_name)}</span>'
            f'<span class="text-xs font-mono" style="color: var(--text-secondary);">'
            f'Mean Score: {organ_score:.2f} / 3.00</span></div>'
            f'<div class="w-full h-2 rounded overflow-hidden mb-3" style="background-color: var(--bg-page); border: 1px solid var(--border-color);">'
            f'<div class="h-full" style="width:{pct}%;background-color:{sys_color}"></div></div>'
            f'<div>{"".join(rows)}</div>'
            f'</div>'
        )

    return (
        '<div class="anatomical-ihc-atlas grid grid-cols-1 md:grid-cols-2 gap-4">'
        + "".join(cards_html)
        + "</div>"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="visualize_tissue_ihc.py",
        description="Group normal tissue IHC staining into 10 anatomical systems and compute stain scores.",
    )
    parser.add_argument("--input_json", "-i", type=str, required=True, help="Path to tissue IHC JSON file.")
    parser.add_argument("--output_html", type=str, required=True, help="Output path for anatomical IHC HTML snippet.")
    parser.add_argument("--output_json", type=str, required=True, help="Output path for enriched organ-system JSON.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        in_path = Path(args.input_json)
        if not in_path.exists():
            raise FileNotFoundError(f"Input tissue IHC JSON file not found: {in_path}")

        raw_ihc = json.loads(in_path.read_text(encoding="utf-8"))
        summary = analyze_tissue_ihc(raw_ihc)
        html_snippet = render_tissue_ihc_html(summary)

        out_json_path = Path(args.output_json)
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        out_json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

        out_html_path = Path(args.output_html)
        out_html_path.parent.mkdir(parents=True, exist_ok=True)
        out_html_path.write_text(html_snippet + "\n", encoding="utf-8")

        logger.info("Saved anatomical IHC summary to %s and HTML snippet to %s", out_json_path, out_html_path)
        return 0
    except Exception as exc:
        logger.error("Tissue IHC visualization failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
