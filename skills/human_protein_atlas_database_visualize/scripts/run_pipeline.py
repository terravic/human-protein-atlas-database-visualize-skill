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

"""Unified end-to-end pipeline orchestrator for Human Protein Atlas Database Visualize."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
import sys
from typing import List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_dashboard as gd  # noqa: E402
import hpa_cli  # noqa: E402
import visualize_concordance as vc  # noqa: E402
import visualize_subcellular as vs  # noqa: E402
import visualize_tissue_ihc as vt  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_pipeline")


def run_pipeline(
    gene: Optional[str] = None,
    ensembl_id: Optional[str] = None,
    tissues: Optional[List[str]] = None,
    output_dir: str = "./output",
    mock: bool = False,
) -> Path:
    """Execute the complete HPA query, enrichment, concordance, and dashboard pipeline."""
    # Step 1: Verify mandatory workspace license guard
    workspace_root = hpa_cli.resolve_workspace_root()
    license_path = hpa_cli.verify_license_guard()
    try:
        rel_license_path = license_path.resolve().relative_to(workspace_root.resolve())
    except ValueError:
        rel_license_path = Path(license_path.name)
    logger.info("Verified HPA license guard at %s", rel_license_path)

    if not gene and not ensembl_id:
        raise ValueError("Either --gene (-g) or --ensembl_id (-e) must be specified.")

    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Step 2: Resolve gene symbol to Ensembl ID
    if gene:
        resolved = hpa_cli.resolve_ensembl_id(gene, mock=mock)
        target_ensembl = resolved["ensembl_id"]
        target_gene = resolved.get("gene_symbol", gene.upper())
        (out_dir / "resolved_id.json").write_text(json.dumps(resolved, indent=2) + "\n", encoding="utf-8")
    else:
        target_ensembl = str(ensembl_id).strip().upper()
        if not target_ensembl.startswith("ENSG"):
            raise ValueError(f"Invalid Ensembl ID '{target_ensembl}'. Must begin with 'ENSG'.")
        target_gene = target_ensembl

    # Step 3: Fetch full atlas entry
    atlas_entry = hpa_cli.get_atlas_entry(target_ensembl, mock=mock)
    if atlas_entry.get("Gene"):
        target_gene = str(atlas_entry["Gene"])
    atlas_entry_path = out_dir / "atlas_entry.json"
    atlas_entry_path.write_text(json.dumps(atlas_entry, indent=2) + "\n", encoding="utf-8")

    # Step 4: Fetch tissue IHC expression
    tissue_ihc = hpa_cli.get_tissue_expression(target_ensembl, tissues=tissues, mock=mock)
    tissue_ihc_path = out_dir / "tissue_ihc.json"
    tissue_ihc_path.write_text(json.dumps(tissue_ihc, indent=2) + "\n", encoding="utf-8")

    # Step 5: Fetch subcellular localization
    subcellular_raw = hpa_cli.get_subcellular_location(target_ensembl, mock=mock)
    subcellular_raw_path = out_dir / "subcellular_raw.json"
    subcellular_raw_path.write_text(json.dumps(subcellular_raw, indent=2) + "\n", encoding="utf-8")

    # Step 6: Enrich subcellular localization and generate SVG cell model
    subcellular_enriched = vs.enrich_subcellular_data(subcellular_raw)
    subcellular_svg = vs.render_subcellular_svg(subcellular_enriched)
    subcell_json_path = out_dir / "subcellular_enriched.json"
    subcell_html_path = out_dir / "subcellular_map.html"
    subcell_json_path.write_text(json.dumps(subcellular_enriched, indent=2) + "\n", encoding="utf-8")
    subcell_html_path.write_text(subcellular_svg + "\n", encoding="utf-8")

    # Step 7: Group tissue IHC into 10 anatomical systems and compute stain scores
    tissue_enriched = vt.analyze_tissue_ihc(tissue_ihc)
    tissue_html = vt.render_tissue_ihc_html(tissue_enriched)
    tissue_enriched_path = out_dir / "tissue_ihc_enriched.json"
    tissue_html_path = out_dir / "tissue_ihc_atlas.html"
    tissue_enriched_path.write_text(json.dumps(tissue_enriched, indent=2) + "\n", encoding="utf-8")
    tissue_html_path.write_text(tissue_html + "\n", encoding="utf-8")

    # Step 8: Calculate RNA vs. Protein concordance matrix
    concordance = vc.evaluate_concordance(atlas_entry, tissue_ihc)
    concordance_html = vc.render_concordance_html(concordance)
    concordance_json_path = out_dir / "concordance_summary.json"
    concordance_html_path = out_dir / "concordance_matrix.html"
    concordance_json_path.write_text(json.dumps(concordance, indent=2) + "\n", encoding="utf-8")
    concordance_html_path.write_text(concordance_html + "\n", encoding="utf-8")

    # Step 9: Compile standalone HTML5 interactive dashboard
    dashboard_payload = gd.build_dashboard_payload(
        gene_symbol=target_gene,
        atlas_entry=atlas_entry,
        subcellular_data=subcellular_enriched,
        tissue_data=tissue_enriched,
        concordance_data=concordance,
    )
    dashboard_html = gd.render_dashboard_html(dashboard_payload)
    dashboard_path = out_dir / "dashboard.html"
    dashboard_path.write_text(dashboard_html, encoding="utf-8")

    # Also update the workspace root and nested skill dashboard.html for direct local viewing
    try:
        ws_root = hpa_cli.resolve_workspace_root()
        for candidate in [
            ws_root / "dashboard.html",
            ws_root / "skills" / "human_protein_atlas_database_visualize" / "dashboard.html",
        ]:
            if candidate.parent.exists() and candidate.resolve() != dashboard_path.resolve():
                candidate.write_text(dashboard_html, encoding="utf-8")
    except OSError:
        pass

    # Step 10: Print terminal summary with citations and scientific disclaimer
    top_systems = [
        f"{m['organ_system']} ({m['organ_score']:.2f})"
        for m in tissue_enriched.get("ranked_organ_systems", [])[:3]
    ]
    main_locs = ", ".join(subcellular_enriched.get("main_locations", [])) or "None"

    try:
        rel_dashboard_path = dashboard_path.resolve().relative_to(workspace_root.resolve())
    except ValueError:
        rel_dashboard_path = Path(dashboard_path.name)

    summary_lines = [
        "=" * 78,
        "HUMAN PROTEIN ATLAS DATABASE VISUALIZE - PIPELINE SUMMARY",
        "=" * 78,
        f"Gene Symbol              : {target_gene}",
        f"Ensembl Gene ID          : {target_ensembl}",
        f"UniProt Accession        : {dashboard_payload.get('uniprot_id', 'N/A')}",
        f"Main Subcellular Locs    : {main_locs}",
        f"Normal Tissues Profiled  : {tissue_enriched.get('total_tissues_profiled', 0)}",
        f"Top Expressing Systems   : {', '.join(top_systems) if top_systems else 'None'}",
        f"RNA-Protein Concordance  : {concordance.get('concordance_score', 0.0):.2f} ({concordance.get('concordance_classification', '')})",
        f"Dashboard Artifact Path  : {rel_dashboard_path}",
        "-" * 78,
        "Citations (CC BY-SA 4.0):",
        "  1. Uhlen, M. et al. Tissue-based map of the human proteome. Science 347, 1260419 (2015). doi:10.1126/science.1260419.",
        "  2. Thul, P. J. et al. A subcellular map of the human proteome. Science 356, eaal3321 (2017). doi:10.1126/science.aal3321.",
        "Disclaimer:",
        "  HPA expression levels, antibody staining, and subcellular localizations are experimental research data derived from cell lines and human tissue microarrays. They are intended for scientific research and must not be used as clinical diagnostic or medical guidance.",
        "=" * 78,
    ]
    print("\n".join(summary_lines))
    return dashboard_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_pipeline.py",
        description="Unified end-to-end HPA query, spatial mapping, and dashboard generation pipeline.",
    )
    parser.add_argument("-g", "--gene", type=str, default=None, help="HGNC gene symbol (e.g., TP53, ERBB2).")
    parser.add_argument("-e", "--ensembl_id", type=str, default=None, help="Ensembl gene ID (e.g., ENSG00000141510).")
    parser.add_argument("-t", "--tissues", type=str, default=None, help="Comma-separated tissue filter list.")
    parser.add_argument("-o", "--output_dir", type=str, required=True, help="Output directory for JSON and dashboard.html.")
    parser.add_argument("--mock", action="store_true", help="Run deterministic offline pipeline using sample_data/ fixtures.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        tissue_list = [t.strip() for t in args.tissues.split(",") if t.strip()] if args.tissues else None
        run_pipeline(
            gene=args.gene,
            ensembl_id=args.ensembl_id,
            tissues=tissue_list,
            output_dir=args.output_dir,
            mock=args.mock,
        )
        return 0
    except Exception as exc:
        logger.error("Pipeline execution failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
