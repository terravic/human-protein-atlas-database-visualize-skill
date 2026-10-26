---
name: human-protein-atlas-database-visualize
description: >
  Retrieve, analyze, and visualize semi-quantitative protein expression, spatial
  subcellular localization, and RNA-to-protein concordance from the Human Protein
  Atlas (HPA). Generates interactive standalone HTML5 dashboards featuring
  3D structural data diagrams, interactive relationship node maps,
  vector-rendered eukaryotic organelle maps, anatomical organ-system IHC heatmaps,
  and cancer pathology profiles. Use when the user asks to analyze, visualize, or
  profile protein abundance, cellular location, or immunohistochemistry across
  human tissues.
---

# Human Protein Atlas Database Visualize

## Overview
This skill provides programmatic queries, spatial subcellular localization mapping, anatomical IHC scoring, and interactive standalone HTML5 dashboards using data from the Human Protein Atlas (HPA). It combines semi-quantitative IHC protein abundance across 44+ normal human tissues with confocal microscopy-based subcellular organelle localization, RNA-protein concordance metrics, 3D structural data diagrams, bipartite relationship node maps, and 2D vector visualizations.

## Prerequisites
1. **Python Environment**: Python >= 3.10 with `polite-http` (or standard library fallback).
2. **License Guard**: Verify that `.licenses/human_protein_atlas_database_visualize_LICENSE.txt` exists in the workspace root. If absent, display the licensing notice and create the file with an ISO 8601 UTC timestamp before querying.

## Core Rules
- **Execute Utility Scripts**: Invoke the provided Python scripts in `scripts/`. Do not execute un-rate-limited HTTP requests directly against `proteinatlas.org`.
- **Rate Limiting Compliance**: Enforce 2.0 QPS request pacing to respect Human Protein Atlas API infrastructure.
- **Process Data Before Rendering UI**: Run the data retrieval and enrichment pipeline (`scripts/run_pipeline.py` or modular scripts) on the requested gene or protein first so that `dashboard.html` displays the computed data.
- **Standalone Dashboard Output**: Keep `./dashboard.html` updated in the project root directory and target output directory (`-o`) so it can be opened directly from disk or served over HTTP with Server-Sent Events (SSE).
- **Three-Icon Theme Selector**: Maintain the segmented three-icon theme selector (`#theme-btn-light`, `#theme-btn-dark`, `#theme-btn-system`) in the top navigation bar with automatic OS appearance tracking.
- **Attribution**: State in output that Human Protein Atlas Database Visualize was used, citing Uhlen et al. (Science 2015) and Thul et al. (Science 2017).

## Workflows

### 1. Unified End-to-End Pipeline
Run full protein profiling, subcellular mapping, and dashboard compilation:
```bash
python3 scripts/run_pipeline.py --gene TP53 -o ./output/TP53/
```

Profile by Ensembl ID with tissue filtering:
```bash
python3 scripts/run_pipeline.py --ensembl_id ENSG00000141736 --tissues "cerebral cortex,liver,heart muscle" -o ./output/ERBB2_tissues/
```

Deterministic offline mock mode (for testing without network access):
```bash
python3 scripts/run_pipeline.py --gene TP53 -o ./output/mock_tp53/ --mock
```

When `scripts/run_pipeline.py` completes, it writes the compiled `dashboard.html` to both the specified output directory and `./dashboard.html` at the project root.

### 2. Modular Subcommands
Query raw endpoints directly using `scripts/hpa_cli.py`:
```bash
# Resolve gene symbol to Ensembl ID
python3 scripts/hpa_cli.py resolve-ensembl-id TP53 --output ./output/tp53_id.json

# Fetch tissue protein expression (IHC)
python3 scripts/hpa_cli.py get-tissue-expression ENSG00000141510 --output ./output/tp53_tissue.json

# Fetch subcellular location
python3 scripts/hpa_cli.py get-subcellular-location ENSG00000141510 --output ./output/tp53_subcellular.json

# Fetch full atlas entry
python3 scripts/hpa_cli.py get-atlas-entry ENSG00000141510 --output ./output/tp53_entry.json

# Search HPA by criteria
python3 scripts/hpa_cli.py search-hpa --query "tissue_category_rna:Brain;Tissue enriched" --output ./output/brain_enriched.json
```

### 3. Specialized Visualization & Analytical Modules
Invoke individual enrichment and visualization scripts directly when custom intermediate outputs are needed:
```bash
# Enrich subcellular locations with GO terms and generate interactive SVG cell schematic
python3 scripts/visualize_subcellular.py \
    --input_json ./output/mock_tp53/subcellular_raw.json \
    --output_json ./output/mock_tp53/subcellular_enriched.json \
    --output_html ./output/mock_tp53/subcellular_map.html

# Group 44+ normal tissues into 10 anatomical systems and compute IHC staining scores (0.0-3.0)
python3 scripts/visualize_tissue_ihc.py \
    --input_json ./output/mock_tp53/tissue_ihc.json \
    --output_json ./output/mock_tp53/tissue_ihc_enriched.json \
    --output_html ./output/mock_tp53/tissue_ihc_atlas.html

# Evaluate 2x2 RNA consensus (nTPM) vs. IHC protein concordance
python3 scripts/visualize_concordance.py \
    --atlas_entry_json ./output/mock_tp53/atlas_entry.json \
    --tissue_ihc_json ./output/mock_tp53/tissue_ihc.json \
    --output_json ./output/mock_tp53/concordance_summary.json \
    --output_html ./output/mock_tp53/concordance_matrix.html

# Compile standalone HTML5 interactive dashboard
python3 scripts/generate_dashboard.py \
    --gene_symbol TP53 \
    --atlas_entry ./output/mock_tp53/atlas_entry.json \
    --subcellular_json ./output/mock_tp53/subcellular_enriched.json \
    --tissue_json ./output/mock_tp53/tissue_ihc_enriched.json \
    --concordance_json ./output/mock_tp53/concordance_summary.json \
    --output ./output/mock_tp53/dashboard.html
```
