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

"""Subcellular organelle localization enrichment and interactive SVG cell map generator."""

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
logger = logging.getLogger("visualize_subcellular")

SKILL_DIR = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = SKILL_DIR / "references" / "subcellular_ontology.json"


def load_subcellular_ontology() -> Dict[str, Dict[str, str]]:
    """Load the subcellular compartment ontology mapping from references/."""
    if not ONTOLOGY_PATH.exists():
        raise FileNotFoundError(f"Subcellular ontology file missing at {ONTOLOGY_PATH}")
    return json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))


def enrich_subcellular_data(
    raw_data: Dict[str, Any],
    ontology: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Match detected main and additional subcellular locations against GO and SVG ontology."""
    ont = ontology or load_subcellular_ontology()
    ont_case_map = {k.lower(): (k, v) for k, v in ont.items()}

    main_locs = raw_data.get("main_locations") or raw_data.get("Subcellular main location") or []
    add_locs = raw_data.get("additional_locations") or raw_data.get("Subcellular additional location") or []
    all_locs = raw_data.get("locations_all") or raw_data.get("Subcellular location") or []

    if isinstance(main_locs, str):
        main_locs = [s.strip() for s in main_locs.split(",") if s.strip()]
    if isinstance(add_locs, str):
        add_locs = [s.strip() for s in add_locs.split(",") if s.strip()]
    if isinstance(all_locs, str):
        all_locs = [s.strip() for s in all_locs.split(",") if s.strip()]

    if not all_locs:
        all_locs = list(dict.fromkeys(list(main_locs) + list(add_locs)))

    annotations: List[Dict[str, Any]] = []
    active_ids: List[str] = []
    main_set = {m.lower() for m in main_locs}

    for loc in all_locs:
        loc_key = loc.strip().lower()
        loc_type = "Main" if loc_key in main_set else "Additional"
        semantic_color = "#0D9488" if loc_type == "Main" else "#4F46E5"
        if loc_key in ont_case_map:
            canonical_name, meta = ont_case_map[loc_key]
            svg_id = meta.get("svg_element_id", "cell-organelle-generic")
            if svg_id not in active_ids:
                active_ids.append(svg_id)
            annotations.append({
                "name": canonical_name,
                "localization_type": loc_type,
                "go_id": meta.get("go_id", "GO:0005575"),
                "category": meta.get("category", "Cellular Component"),
                "svg_element_id": svg_id,
                "color": semantic_color,
                "description": meta.get("description", "Eukaryotic subcellular compartment."),
            })
        else:
            svg_id = f"cell-organelle-{loc_key.replace(' ', '-')}"
            if svg_id not in active_ids:
                active_ids.append(svg_id)
            annotations.append({
                "name": loc,
                "localization_type": loc_type,
                "go_id": "GO:0005575",
                "category": "Other / Unclassified",
                "svg_element_id": svg_id,
                "color": semantic_color,
                "description": "Subcellular compartment annotated by the Human Protein Atlas.",
            })

    return {
        "ensembl_id": raw_data.get("ensembl_id") or raw_data.get("Ensembl", ""),
        "gene_symbol": raw_data.get("gene_symbol") or raw_data.get("Gene", ""),
        "reliability": raw_data.get("reliability") or raw_data.get("RNA_protein_agreement", {}).get("reliability", "Approved"),
        "main_locations": list(main_locs),
        "additional_locations": list(add_locs),
        "locations_all": list(all_locs),
        "active_organelle_ids": active_ids,
        "annotations": annotations,
    }


def render_subcellular_svg(
    enriched: Dict[str, Any],
    ontology: Optional[Dict[str, Dict[str, str]]] = None,
) -> str:
    """Render an interactive SVG schematic of a generalized human eukaryotic cell."""
    ont = ontology or load_subcellular_ontology()
    active_by_svg_id: Dict[str, Dict[str, Any]] = {}
    for ann in enriched.get("annotations", []):
        active_by_svg_id[ann["svg_element_id"]] = ann

    def style_attrs(svg_id: str, default_name: str) -> str:
        meta = next((v for k, v in ont.items() if v.get("svg_element_id") == svg_id), None)
        go_id = meta["go_id"] if meta else "GO:0005575"
        desc = meta["description"] if meta else "Eukaryotic cellular organelle."
        color = meta["color"] if meta else "#0D9488"

        if svg_id in active_by_svg_id:
            ann = active_by_svg_id[svg_id]
            loc_type = ann["localization_type"]
            if loc_type == "Main":
                fill_color = "#0D9488"
                cls = "organelle-node organelle-active-main"
                stroke_attr = f'fill="{fill_color}" fill-opacity="0.72" stroke="{fill_color}" stroke-width="2.5"'
            else:
                fill_color = "#4F46E5"
                cls = "organelle-node organelle-active-additional"
                stroke_attr = (
                    f'fill="{fill_color}" fill-opacity="0.48" stroke="{fill_color}" '
                    'stroke-width="2" stroke-dasharray="6,4"'
                )
        else:
            loc_type = "Not Detected"
            cls = "organelle-node organelle-inactive"
            stroke_attr = 'fill="var(--organelle-inactive-fill, #FAFAF9)" fill-opacity="0.45" stroke="var(--organelle-inactive-stroke, #787774)" stroke-width="1.25"'

        safe_name = html.escape(default_name, quote=True)
        safe_desc = html.escape(desc, quote=True)
        return (
            f'id="{svg_id}" class="{cls}" {stroke_attr} '
            f'data-name="{safe_name}" data-go="{go_id}" '
            f'data-type="{loc_type}" data-color="{color}" data-description="{safe_desc}"'
        )

    svg = f"""<div class="subcellular-schematic-wrapper relative w-full">
  <svg viewBox="0 0 820 520" class="w-full h-auto select-none" role="img" aria-label="Interactive Human Eukaryotic Cell Organelle Schematic">
    <!-- Extracellular / Secreted Zone -->
    <g {style_attrs("cell-organelle-secreted", "Secreted")}>
      <rect x="16" y="16" width="135" height="44" rx="6" />
      <text x="83" y="42" text-anchor="middle" font-size="11" fill="currentColor" class="pointer-events-none font-medium">Secreted Space</text>
    </g>

    <!-- Plasma Membrane (Outer Bilayer Boundary) -->
    <path d="M 160,95 C 260,35 580,35 670,100 C 755,160 760,355 665,425 C 565,495 255,495 155,420 C 70,355 65,155 160,95 Z"
          {style_attrs("cell-organelle-plasma-membrane", "Plasma membrane")} />

    <!-- Cell Junctions (Lateral Membrane Plaques) -->
    <g {style_attrs("cell-organelle-cell-junctions", "Cell junctions")}>
      <rect x="102" y="215" width="14" height="36" rx="4" />
      <rect x="102" y="265" width="14" height="36" rx="4" />
      <rect x="712" y="225" width="14" height="36" rx="4" />
      <rect x="712" y="275" width="14" height="36" rx="4" />
    </g>

    <!-- Cytosol (Interior Cytoplasmic Matrix) -->
    <path d="M 176,110 C 268,54 568,54 652,115 C 730,170 735,345 648,408 C 555,474 265,474 172,404 C 92,344 88,165 176,110 Z"
          {style_attrs("cell-organelle-cytosol", "Cytosol")} />

    <!-- Actin Filaments & Cytoskeleton Tracks -->
    <g {style_attrs("cell-organelle-actin", "Actin filaments")}>
      <path d="M 185,155 Q 250,130 320,145" fill="none" stroke-width="3" />
      <path d="M 195,380 Q 280,410 370,395" fill="none" stroke-width="3" />
    </g>

    <!-- Microtubules -->
    <g {style_attrs("cell-organelle-microtubules", "Microtubules")}>
      <line x1="485" y1="195" x2="620" y2="140" stroke-width="2.5" />
      <line x1="485" y1="195" x2="645" y2="235" stroke-width="2.5" />
      <line x1="485" y1="195" x2="595" y2="335" stroke-width="2.5" />
    </g>

    <!-- Endoplasmic Reticulum (Perinuclear Cisternae Network) -->
    <path d="M 225,195 C 200,225 200,295 228,325 C 245,342 268,335 262,315 C 242,290 242,230 264,205 Z"
          {style_attrs("cell-organelle-er", "Endoplasmic reticulum")} />

    <!-- Nuclear Membrane -->
    <ellipse cx="355" cy="260" rx="108" ry="92"
             {style_attrs("cell-organelle-nuclear-membrane", "Nuclear membrane")} />

    <!-- Nucleoplasm -->
    <ellipse cx="355" cy="260" rx="98" ry="82"
             {style_attrs("cell-organelle-nucleoplasm", "Nucleoplasm")} />

    <!-- Nucleoli -->
    <circle cx="332" cy="248" r="26"
            {style_attrs("cell-organelle-nucleoli", "Nucleoli")} />

    <!-- Nuclear Speckles & Nuclear Bodies -->
    <g {style_attrs("cell-organelle-speckles", "Nuclear speckles")}>
      <circle cx="388" cy="230" r="9" />
      <circle cx="408" cy="252" r="7" />
      <circle cx="382" cy="285" r="8" />
    </g>
    <g {style_attrs("cell-organelle-nuclear-bodies", "Nuclear bodies")}>
      <circle cx="315" cy="295" r="7" />
      <circle cx="352" cy="308" r="6" />
    </g>

    <!-- Centrosome (MTOC) -->
    <g {style_attrs("cell-organelle-centrosome", "Centrosome")}>
      <rect x="472" y="182" width="18" height="10" rx="3" transform="rotate(25 481 187)" />
      <rect x="476" y="188" width="18" height="10" rx="3" transform="rotate(-65 485 193)" />
    </g>

    <!-- Golgi Apparatus -->
    <g {style_attrs("cell-organelle-golgi", "Golgi apparatus")}>
      <path d="M 505,255 Q 548,242 585,260 Q 548,272 505,255 Z" />
      <path d="M 500,274 Q 548,260 592,280 Q 548,292 500,274 Z" />
      <path d="M 508,293 Q 548,282 584,298 Q 548,308 508,293 Z" />
    </g>

    <!-- Mitochondria -->
    <g {style_attrs("cell-organelle-mitochondria", "Mitochondria")}>
      <ellipse cx="555" cy="165" rx="36" ry="18" transform="rotate(-18 555 165)" />
      <ellipse cx="545" cy="365" rx="38" ry="18" transform="rotate(15 545 365)" />
    </g>

    <!-- Vesicles -->
    <g {style_attrs("cell-organelle-vesicles", "Vesicles")}>
      <circle cx="625" cy="285" r="11" />
      <circle cx="652" cy="262" r="9" />
      <circle cx="638" cy="318" r="10" />
    </g>

    <!-- Lysosomes & Peroxisomes -->
    <g {style_attrs("cell-organelle-lysosomes", "Lysosomes")}>
      <circle cx="245" cy="365" r="14" />
    </g>
    <g {style_attrs("cell-organelle-peroxisomes", "Peroxisomes")}>
      <circle cx="285" cy="152" r="12" />
    </g>

    <!-- Diagram Labels -->
    <g font-family="var(--font-sans, 'DM Sans', sans-serif)" font-size="11" fill="var(--text-secondary, #787774)" class="pointer-events-none font-semibold">
      <text x="355" y="160" text-anchor="middle">Nucleus / Nucleoplasm</text>
      <text x="332" y="252" text-anchor="middle" font-size="10">Nucleoli</text>
      <text x="548" y="238" text-anchor="middle">Golgi</text>
      <text x="555" y="138" text-anchor="middle">Mitochondria</text>
      <text x="640" y="345" text-anchor="middle">Vesicles</text>
      <text x="202" y="262" text-anchor="end">ER</text>
      <text x="415" y="452" text-anchor="middle">Plasma Membrane &amp; Cytosol</text>
    </g>
  </svg>
</div>"""
    return svg


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="visualize_subcellular.py",
        description="Enrich HPA subcellular localization JSON and render interactive SVG cell schematic.",
    )
    parser.add_argument("--input_json", "-i", type=str, required=True, help="Path to subcellular or atlas entry JSON.")
    parser.add_argument("--output_html", type=str, required=True, help="Output path for generated HTML/SVG snippet.")
    parser.add_argument("--output_json", type=str, required=True, help="Output path for enriched subcellular JSON.")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        in_path = Path(args.input_json)
        if not in_path.exists():
            raise FileNotFoundError(f"Input JSON file not found: {in_path}")

        raw_data = json.loads(in_path.read_text(encoding="utf-8"))
        ontology = load_subcellular_ontology()
        enriched = enrich_subcellular_data(raw_data, ontology=ontology)
        svg_html = render_subcellular_svg(enriched, ontology=ontology)

        out_json_path = Path(args.output_json)
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        out_json_path.write_text(json.dumps(enriched, indent=2) + "\n", encoding="utf-8")

        out_html_path = Path(args.output_html)
        out_html_path.parent.mkdir(parents=True, exist_ok=True)
        out_html_path.write_text(svg_html + "\n", encoding="utf-8")

        logger.info("Saved enriched subcellular JSON to %s and SVG to %s", out_json_path, out_html_path)
        return 0
    except Exception as exc:
        logger.error("Subcellular visualization failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
