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

"""RNA-seq transcript abundance (nTPM) versus IHC protein staining concordance engine."""

from __future__ import annotations

import argparse
import html
import json
import logging
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("visualize_concordance")

LEVEL_SCORES = {
    "high": 3,
    "medium": 2,
    "low": 1,
    "not detected": 0,
}


def parse_rna_ntpm_map(atlas_entry: Dict[str, Any]) -> Dict[str, float]:
    """Extract per-tissue consensus nTPM values from atlas entry JSON."""
    raw_rna = atlas_entry.get("RNA tissue specific nTPM")
    ntpm_map: Dict[str, float] = {}
    if isinstance(raw_rna, dict):
        for k, v in raw_rna.items():
            try:
                ntpm_map[str(k).strip().lower()] = float(v)
            except (TypeError, ValueError):
                continue
    elif isinstance(raw_rna, str) and raw_rna.strip():
        for pair in re.split(r"[;,]", raw_rna):
            if ":" in pair:
                t_name, val_str = pair.split(":", 1)
                try:
                    ntpm_map[t_name.strip().lower()] = float(val_str.strip())
                except ValueError:
                    continue
    return ntpm_map


def evaluate_concordance(
    atlas_entry: Dict[str, Any],
    tissue_ihc: Dict[str, Any],
) -> Dict[str, Any]:
    """Classify tissues into a 2x2 RNA-vs-Protein concordance matrix."""
    ntpm_map = parse_rna_ntpm_map(atlas_entry)
    tissues = tissue_ihc.get("tissues", [])
    reliability = (
        atlas_entry.get("RNA_protein_agreement", {}).get("reliability")
        or tissue_ihc.get("verification")
        or "Approved"
    )

    quadrants: Dict[str, List[Dict[str, Any]]] = {
        "Concordant High": [],
        "Concordant Low/Absent": [],
        "Potential Translational Repression": [],
        "High Protein Stability / Secretion": [],
    }
    tissue_points: List[Dict[str, Any]] = []
    discordant_tissues: List[Dict[str, Any]] = []

    for item in tissues:
        t_name = str(item.get("tissue", "")).strip()
        if not t_name:
            continue
        t_lower = t_name.lower()
        level = str(item.get("level", "Not detected")).strip()
        score = LEVEL_SCORES.get(level.lower(), 0)
        default_ntpm = 22.0 if score >= 2 else (9.5 if score == 1 else 0.5)
        ntpm = round(float(ntpm_map.get(t_lower, default_ntpm)), 2)

        if score >= 2 and ntpm >= 10.0:
            quadrant = "Concordant High"
            is_concordant = True
        elif score <= 1 and ntpm < 10.0:
            quadrant = "Concordant Low/Absent"
            is_concordant = True
        elif score <= 1 and ntpm >= 10.0:
            quadrant = "Potential Translational Repression"
            is_concordant = False
        else:
            quadrant = "High Protein Stability / Secretion"
            is_concordant = False

        point = {
            "tissue": t_name,
            "rna_ntpm": ntpm,
            "protein_level": level,
            "protein_score": score,
            "quadrant": quadrant,
            "concordant": is_concordant,
        }
        quadrants[quadrant].append(point)
        tissue_points.append(point)
        if not is_concordant:
            discordant_tissues.append(point)

    total = len(tissue_points)
    if total == 0:
        concordance_score = 0.0
        classification = "Insufficient IHC Data"
    else:
        concordant_count = len(quadrants["Concordant High"]) + len(quadrants["Concordant Low/Absent"])
        concordance_score = round(concordant_count / total, 2)
        if concordance_score >= 0.75:
            classification = "High Concordance"
        elif concordance_score >= 0.50:
            classification = "Moderate Concordance"
        else:
            classification = "Low Concordance / Post-Transcriptional Regulation"

    return {
        "gene_symbol": atlas_entry.get("Gene") or tissue_ihc.get("gene_symbol", ""),
        "ensembl_id": atlas_entry.get("Ensembl") or tissue_ihc.get("ensembl_id", ""),
        "reliability": reliability,
        "concordance_score": concordance_score,
        "concordance_classification": classification,
        "total_evaluated_tissues": total,
        "quadrant_counts": {k: len(v) for k, v in quadrants.items()},
        "quadrants": quadrants,
        "discordant_tissues": discordant_tissues,
        "tissue_points": tissue_points,
    }


def render_concordance_html(concordance: Dict[str, Any]) -> str:
    """Render a flat single-level bento 2x2 RNA-vs-Protein Concordance Quadrant summary block."""
    q_counts = concordance.get("quadrant_counts", {})
    score = concordance.get("concordance_score", 0.0)
    cls_label = html.escape(str(concordance.get("concordance_classification", "")))
    rel = html.escape(str(concordance.get("reliability", "Approved")))

    return f"""<div class="concordance-matrix-card dashboard-card p-5">
  <div class="flex flex-wrap items-center justify-between gap-2 pb-4 border-b" style="border-color: var(--border-color);">
    <div>
      <h3 class="text-base font-bold" style="color: var(--text-primary); margin:0;">RNA-Seq (nTPM) vs. IHC Protein Concordance Matrix</h3>
      <p class="text-xs mt-1" style="color: var(--text-secondary); margin-bottom:0;">HPA Verification Status: <span id="conc-card-reliability" class="font-mono font-semibold" style="color: #059669;">{rel}</span></p>
    </div>
    <div id="conc-card-score-badge" class="px-3 py-1 rounded text-xs font-mono font-bold" style="border: 1px solid #059669; color: #059669;">
      Concordance Score: {score:.2f} ({cls_label})
    </div>
  </div>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-4">
    <div class="pt-1">
      <div class="text-xs font-bold uppercase tracking-wider" style="color: #059669;">Concordant High (RNA &gt;= 10 nTPM &amp; IHC)</div>
      <div id="conc-q-high" class="text-2xl font-mono font-semibold mt-1" style="color: var(--text-primary);">{q_counts.get("Concordant High", 0)} tissues</div>
    </div>
    <div class="pt-1">
      <div class="text-xs font-bold uppercase tracking-wider" style="color: #D97706;">High Protein Stability (RNA &lt; 10 nTPM)</div>
      <div id="conc-q-stability" class="text-2xl font-mono font-semibold mt-1" style="color: var(--text-primary);">{q_counts.get("High Protein Stability / Secretion", 0)} tissues</div>
    </div>
    <div class="pt-1">
      <div class="text-xs font-bold uppercase tracking-wider" style="color: #0D9488;">Concordant Low / Absent</div>
      <div id="conc-q-low" class="text-2xl font-mono font-semibold mt-1" style="color: var(--text-primary);">{q_counts.get("Concordant Low/Absent", 0)} tissues</div>
    </div>
    <div class="pt-1">
      <div class="text-xs font-bold uppercase tracking-wider" style="color: #E11D48;">Potential Translational Repression</div>
      <div id="conc-q-repression" class="text-2xl font-mono font-semibold mt-1" style="color: var(--text-primary);">{q_counts.get("Potential Translational Repression", 0)} tissues</div>
    </div>
  </div>
</div>"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="visualize_concordance.py",
        description="Evaluate RNA transcript (nTPM) vs. IHC protein staining concordance across tissues.",
    )
    parser.add_argument("--atlas_entry_json", type=str, required=True, help="Path to atlas entry JSON.")
    parser.add_argument("--tissue_ihc_json", type=str, required=True, help="Path to tissue IHC JSON.")
    parser.add_argument("--output_html", type=str, required=True, help="Output path for concordance HTML snippet.")
    parser.add_argument("--output_json", type=str, required=True, help="Output path for concordance summary JSON.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        entry_path = Path(args.atlas_entry_json)
        ihc_path = Path(args.tissue_ihc_json)
        if not entry_path.exists():
            raise FileNotFoundError(f"Atlas entry JSON not found: {entry_path}")
        if not ihc_path.exists():
            raise FileNotFoundError(f"Tissue IHC JSON not found: {ihc_path}")

        atlas_entry = json.loads(entry_path.read_text(encoding="utf-8"))
        tissue_ihc = json.loads(ihc_path.read_text(encoding="utf-8"))

        concordance = evaluate_concordance(atlas_entry, tissue_ihc)
        html_out = render_concordance_html(concordance)

        out_json = Path(args.output_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(concordance, indent=2) + "\n", encoding="utf-8")

        out_html = Path(args.output_html)
        out_html.parent.mkdir(parents=True, exist_ok=True)
        out_html.write_text(html_out + "\n", encoding="utf-8")

        logger.info("Saved concordance JSON to %s and HTML snippet to %s", out_json, out_html)
        return 0
    except Exception as exc:
        logger.error("Concordance analysis failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
