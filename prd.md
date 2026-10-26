# Product Requirement Document: Human Protein Atlas Database Visualize Skill

## 1. User Stories & Scope

### 1.1 Target Audience
The `human-protein-atlas-database-visualize` skill serves three primary user segments across life sciences, translational research, and computational biology:
1. **Translational Scientists and Cell Biologists (Non-Technical End Users)**: Researchers interacting through conversational interfaces who require integrated spatial and tissue-level visual profiles of human proteins without writing Python code or parsing XML/JSON feeds.
2. **Bioinformaticians and Computational Biologists (Technical Users)**: Engineers running command-line pipelines to batch-profile gene sets, assess RNA-to-protein concordance across organ systems, and extract structured JSON summaries for downstream integration.
3. **Automated Scientific Workflows**: Programmatic pipelines requiring deterministic, rate-limited API access, structured ontology mappings (Uberon and Gene Ontology), and self-contained HTML5 visualization outputs.

### 1.2 User Stories
- **US-01 (End-to-End Protein Profiling)**: As a cell biologist, I want to provide a gene symbol (such as `TP53` or `ERBB2`) and receive a standalone interactive HTML dashboard (`./dashboard.html`) showing subcellular compartment localization, organ-system immunohistochemistry (IHC) expression, RNA-to-protein concordance, and cancer pathology prognostic data.
- **US-02 (3D Structural Data Diagram & 2D Vector Subcellular Spatial Mapping)**: As a microscopist, I want to view a 3D structural and organ-network projection (`#hpa-3d-physics-viewport` with hardware WebGL detection and deterministic software projection fallback), an interactive bipartite relationship node map (`#hpa-relationship-node-map`), and a 2D vector eukaryotic cell schematic highlighting main versus additional subcellular organelles alongside Gene Ontology (GO) Cellular Component identifiers.
- **US-03 (Anatomical Organ-System Grouping & Concentration Heatmap)**: As a physiologist, I want 44+ individual normal human tissues automatically grouped into 10 standardized physiological organ systems with numerical IHC staining scores (`0.0` to `3.0`), Uberon ontology cross-references, and a concentration heatmap matrix transitioning across `Surface` -> `#0D9488` -> `#4F46E5` -> `#E11D48`.
- **US-04 (RNA vs. Protein Concordance Analysis)**: As a systems biologist, I want to cross-tabulate consensus transcript abundance (nTPM) against IHC protein staining across tissues in a 2x2 quadrant matrix and 2D quantitative scatter plot (`#concordance-scatter-viewport`) to identify concordant expression, potential post-transcriptional repression, or high protein stability/secretion.
- **US-05 (Three-Icon Theme Selector & Live Dataset Switching)**: As an interactive reviewer, I want a three-icon segmented theme selector (`#theme-btn-light`, `#theme-btn-dark`, `#theme-btn-system`) in the top navigation bar that tracks operating system appearance changes in real time alongside a pipeline provenance strip, live Server-Sent Events (SSE) update support, and dataset switching (`TP53`, `ERBB2`, or custom JSON loader).
- **US-06 (Offline Deterministic Execution)**: As a test engineer, I want a `--mock` execution flag that runs the entire query, analysis, and dashboard rendering pipeline using local curated fixtures without requiring network access.

### 1.3 Scope Definition

| Capability | In Scope | Out of Scope |
| :--- | :--- | :--- |
| **Data Retrieval** | Rate-limited (2.0 QPS) queries to HPA JSON search API and XML gene records; Ensembl ID resolution; offline `--mock` replay. | Bulk downloading of multi-gigabyte raw microscopy TIFF images or full database dumps. |
| **Anatomical Analysis** | Grouping of 44+ HPA normal tissues into 10 organ systems with Uberon IDs, quantitative staining scores (`0.0` to `3.0`), and concentration heatmap matrices. | Automated histopathological image segmentation of raw tissue microarray slides. |
| **Subcellular & 3D Structural Mapping** | 3D volumetric cell/network structural data diagram with software projection fallback, bipartite relationship node map, and 2D vector SVG eukaryotic cell schematic mapping 35+ HPA subcellular terms to GO terms. | Raw confocal z-stack voxel reconstruction from raw microscopy files. |
| **Concordance & Pathology** | 2x2 quadrant classification and 2D scatter plot of RNA nTPM vs. IHC levels; summary of 17 major cancer types and prognostic status. | Patient-level survival curve Kaplan-Meier re-estimation from raw clinical trial tables. |
| **Compliance & Licensing** | Pre-flight license guard verification, CC BY-SA 4.0 attribution, Apache 2.0 code headers, and non-clinical research disclaimers. | Clinical diagnostic decision support or processing of patient-identifiable health data. |

---

## 2. Visual & Technical Design Specifications

### 2.1 Typography & Hierarchy Rules
- **Sans-Serif UI Font**: `'DM Sans'`, `'Geist Sans'`, `system-ui`, `sans-serif` for navigation controls, filter buttons, labels, and descriptions. Avoid generic defaults such as `Inter` or `Roboto`.
- **Serif Display Font**: `'Instrument Serif'`, `Georgia`, `serif` for primary gene headers and analytical section titles (`h1`, `h2`, `.serif-display`).
- **Tabular Monospace Font**: `'IBM Plex Mono'`, `'Geist Mono'`, `monospace` with `font-variant-numeric: tabular-nums` for Ensembl IDs, UniProt accessions, Gene Ontology terms, Uberon IDs, p-values, and nTPM measurements.
- **Section Headings & Control Surfaces**: Text-first section headers with concise, domain-accurate titles ("Interactive Relationship Node Map" and "Structural Data Diagram"). Restrict icons to functional interactive controls such as the theme mode selector.

### 2.2 Surface Architecture & Theme Tokens
- **Container Layout**: Single-level bento-style grid organization using flat, solid surface tokens, `1px solid` structural borders (`6px` to `8px` border-radius), and thin horizontal row dividers. Avoid nested card-in-card containers or multi-stop color gradients.
- **Status Indicators**: High-signal state reporting. Highlight warning, error, or critical states explicitly; render nominal items using standard monospaced or muted tokens.
- **Background Surfaces**: Uncluttered viewport backgrounds for node maps and workspaces. Reserve gridlines strictly for quantitative chart axes and coordinate plots (`#E7E5E4` in light mode, `#292A30` in dark mode).
- **Light Mode Tokens**:
  - Background: `#FAFAF9` (Warm off-white)
  - Cards & Surfaces: `#FFFFFF`
  - Borders & Quantitative Axis Gridlines: `#E7E5E4` (`1px solid`, `6px` to `8px` border-radius)
  - Text Primary: `#1C1917`
  - Text Secondary: `#787774`
- **Dark Mode Tokens**:
  - Background: `#0D0E11` (Deep charcoal)
  - Cards & Surfaces: `#16171D`
  - Borders & Quantitative Axis Gridlines: `#292A30` (`1px solid`, `6px` to `8px` border-radius)
  - Text Primary: `#ECE8E2`
  - Text Secondary: `#9A9895`
- **Three-Icon Theme Selector**:
  - `#theme-btn-light` (Sun SVG icon, `title="Light Theme"`, `aria-label="Light Theme"`, `data-theme-mode="light"`).
  - `#theme-btn-dark` (Crescent moon SVG icon, `title="Dark Theme"`, `aria-label="Dark Theme"`, `data-theme-mode="dark"`).
  - `#theme-btn-system` (Simple computer monitor SVG icon, `title="System Theme"`, `aria-label="System Theme"`, `data-theme-mode="system"`).
  - Each button contains only its SVG icon, highlights the active mode via the `active` class and `aria-pressed="true"`, and persists mode selection in `localStorage`.
- **Cross-Platform System Theme Detection**:
  - Browser/Webview Layer: When `system` mode is selected, resolve the active theme via `window.matchMedia('(prefers-color-scheme: dark)')` and register a `'change'` event listener so operating system appearance changes update the interface in real time.
  - Host OS Layer (Backend Fallback): Query native OS appearance preference via platform commands (`defaults read -g AppleInterfaceStyle` on macOS, registry check on Windows, or `GTK_THEME` / `gsettings` / `kdeglobals` on Linux) and embed `system_theme` in the data bundle as a fallback for headless or restricted webviews.

### 2.3 Semantic Data Visualization Palette
All charts, heatmaps, subcellular maps, and network/molecular graphs use the 5-color semantic palette:
- **Vibrant Teal (`#0D9488`)**: Primary data series, baseline metrics, structural bonds, main subcellular organelles, low IHC detection (`Score 1.0`), nominal nodes.
- **Energetic Amber (`#D97706`)**: Secondary data series, warning thresholds, intermediate intensity, high protein stability / secretion quadrant.
- **Vivid Indigo (`#4F46E5`)**: Comparison series, distinct molecular groups, specialized network nodes, additional subcellular organelles, medium IHC detection (`Score 2.0`), organ hubs.
- **Functional Emerald (`#059669`)**: Passing metrics, positive outcomes, validated states, favorable prognostic status.
- **Deep Rose (`#E11D48`)**: High IHC staining intensity (`Score 3.0`), critical alerts, negative trends, threshold violations, translational repression alerts, unfavorable prognostic status.

#### Visualization Guidelines
- **Matrices & Heatmaps**: Transition smoothly from the surface background tone through **Vibrant Teal** (`#0D9488`) and **Vivid Indigo** (`#4F46E5`) to **Deep Rose** (`#E11D48`) so concentration gradients are legible in both light and dark themes.
- **Network & Molecular Graphs**: Color nodes by category or validation state using the semantic palette above, with semi-transparent edge strokes derived from the connected node state.
- **Chart Backgrounds & Gridlines**: Keep chart plot backgrounds transparent so they inherit the active light or dark surface color, and use subtle axis gridlines (`#E7E5E4` in light mode, `#292A30` in dark mode).
- **Tables**: Render numerical and tabular data in a monospaced font (`IBM Plex Mono` or `Geist Mono`) with `font-variant-numeric: tabular-nums` and thin horizontal row dividers.

### 2.4 Runtime Environment & Viewport State Preservation
- **Self-Contained Execution**: Dashboards run inside standard browsers as well as sandboxed or embedded webviews using standard HTML5, CSS custom properties, and JavaScript.
- **Dynamic State Updates**: UI components support incremental state updates and live data refresh without resetting user viewport state, scroll position, or active chart/camera interactions.
- **Standalone Output (`dashboard.html`)**: Build workflows emit a self-contained `./dashboard.html` file at the project root directory that can be opened directly from disk or served over HTTP with Server-Sent Events (SSE).
- **Empirical Data Rendering**: Views render actual computed datasets, provenance records, and validation records from the active workspace without placeholder text.

### 2.5 Verification Checklist & Acceptance Criteria
1. **Self-Contained Output**: Build workflow produces a self-contained `./dashboard.html` file that renders both offline from disk and via live SSE streaming.
2. **Three-Icon Theme Selector**: Presents three side-by-side textless SVG icon buttons (Sun for Light, Crescent Moon for Dark, Computer Monitor for System) with real-time OS theme tracking and `localStorage` persistence.
3. **Exact Token Compliance**: Both Light Mode and Dark Mode apply the exact surface, border, and text hex tokens specified in Section 2.2.
4. **Semantic Visualization Palette**: All 2D charts, 3D structural views, and SVG node maps apply the semantic data visualization palette from Section 2.3 and re-render cleanly when switching themes.
5. **Empirical Data Display**: Renders computed workspace data, pipeline provenance records, and mandatory Uhlen (2015) and Thul (2017) citations without placeholder text.

---

## 3. Technical Pipeline Architecture

```text
+-----------------------------------------------------------------------------------+
|                              CLI / SKILL INVOCATION                               |
|             (Invokes SKILL.md workflows or runs scripts/run_pipeline.py)          |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                     PRE-FLIGHT LICENSE & COMPLIANCE GUARD                         |
|   Checks .licenses/human_protein_atlas_database_visualize_LICENSE.txt             |
|   Creates notice file with ISO 8601 UTC timestamp if absent                       |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                  ORCHESTRATION LAYER (scripts/run_pipeline.py)                    |
|   Coordinates gene symbol resolution, data retrieval, enrichment, and rendering   |
+-------------------+-------------------------------------------+-------------------+
                    |                                           |
        (Live Mode: 2.0 QPS HTTP)                    (Offline Mode: --mock)
                    v                                           v
+---------------------------------------+   +---------------------------------------+
|     HPA API CLIENT (hpa_cli.py)       |   |     OFFLINE MOCK FIXTURE ENGINE       |
| - resolve-ensembl-id                  |   | - sample_data/tp53_entry.json         |
| - get-atlas-entry                     |   | - sample_data/tp53_tissue_ihc.json    |
| - get-tissue-expression               |   | - sample_data/tp53_subcellular.json   |
| - get-subcellular-location            |   | - sample_data/erbb2_*.json            |
| - search-hpa                          |   +-------------------+-------------------+
+-------------------+-------------------+                       |
                    |                                           |
                    +---------------------+---------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                         ANALYTICAL & VISUALIZATION ENGINES                        |
|                                                                                   |
|  +------------------------------+  Uses -> references/subcellular_ontology.json   |
|  | visualize_subcellular.py     |  Outputs: Enriched JSON + Vector Cell SVG       |
|  +------------------------------+                                                 |
|                                                                                   |
|  +------------------------------+  Uses -> references/tissue_organ_mapping.json   |
|  | visualize_tissue_ihc.py      |  Outputs: 10 Organ Systems + Scores (0.0-3.0)   |
|  +------------------------------+                                                 |
|                                                                                   |
|  +------------------------------+  Cross-tabulates RNA nTPM vs IHC Staining       |
|  | visualize_concordance.py     |  Outputs: 2x2 Quadrant Matrix + Reliability     |
|  +------------------------------+                                                 |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|               DASHBOARD COMPILER (scripts/generate_dashboard.py)                  |
|   Embeds <script id="hpa-dashboard-data" type="application/json">                 |
|   Renders standalone HTML5 dashboard (./dashboard.html) with Structural Data      |
|   Diagram, Interactive Relationship Node Map, 2D vector cell schematic,           |
|   Anatomical IHC Heatmap Matrix, 2D scatter plot, and 3-icon theme selector       |
|   Appends mandatory Uhlen (2015) & Thul (2017) citations and research disclaimer  |
+-----------------------------------------------------------------------------------+
```

---

## 4. Functional Requirements

### 4.1 Data Inputs
1. **Primary Gene Identifiers**:
   - Standard HGNC Gene Symbol (string, case-insensitive, e.g., `TP53`, `ERBB2`, `INS`).
   - Ensembl Gene Identifier (string matching regex `^ENSG\d{11}$`, e.g., `ENSG00000141510`).
2. **Optional Filter Parameters**:
   - `--tissues`: Comma-separated list of target tissue names (case-insensitive, e.g., `"cerebral cortex,liver,heart muscle"`).
   - `--query`: Structured HPA search query string for `search-hpa` subcommand.
   - `--mock`: Boolean flag activating deterministic offline fixture execution.
3. **Reference Ontologies**:
   - `references/tissue_organ_mapping.json`: Maps 49 HPA normal tissues to 10 physiological organ systems, semantic hex colors, and Uberon ontology IDs.
   - `references/subcellular_ontology.json`: Maps 35 HPA subcellular locations to cellular categories, GO Cellular Component IDs, semantic hex colors, and SVG element identifiers.

### 4.2 Processing Stages
1. **Stage 1: License Guard Validation**:
   - Check project root for `.licenses/human_protein_atlas_database_visualize_LICENSE.txt` (or `.licenses/human_protein_atlas_database_LICENSE.txt`).
   - If absent, output the HPA CC BY-SA 4.0 licensing notification to standard output and write `.licenses/human_protein_atlas_database_visualize_LICENSE.txt` with an ISO 8601 UTC timestamp.
2. **Stage 2: Symbol Resolution & Data Retrieval (`scripts/hpa_cli.py`)**:
   - Resolve gene symbol to canonical Ensembl ID via `search_download.php` or offline fixture table.
   - Retrieve multi-column metadata (`get-atlas-entry`), XML-parsed normal tissue IHC scores (`get-tissue-expression`), and confocal subcellular localization arrays (`get-subcellular-location`).
3. **Stage 3: Subcellular Spatial Mapping (`scripts/visualize_subcellular.py`)**:
   - Match `main_locations` and `additional_locations` against `references/subcellular_ontology.json`.
   - Generate vector SVG eukaryotic cell diagram with distinct semantic styling for main compartments (`#0D9488`), additional compartments (`#4F46E5`), and inactive compartments.
4. **Stage 4: Anatomical Organ-System Grouping (`scripts/visualize_tissue_ihc.py`)**:
   - Convert qualitative staining levels into numerical values: `High` = 3.0, `Medium` = 2.0, `Low` = 1.0, `Not detected` = 0.0.
   - Group all tissues into 10 anatomical systems (`Central Nervous System`, `Cardiovascular`, `Digestive`, `Endocrine`, `Immune / Lymphoid`, `Musculoskeletal`, `Reproductive`, `Respiratory`, `Urinary`, `Integumentary`) and compute mean organ system expression scores.
5. **Stage 5: RNA-to-Protein Concordance Scoring (`scripts/visualize_concordance.py`)**:
   - Compare tissue-level RNA consensus abundance (nTPM) with IHC staining scores across profiled tissues.
   - Classify each tissue into one of four quadrants: `Concordant High`, `Concordant Low/Absent`, `Potential Translational Repression`, or `High Protein Stability / Secretion`.
   - Compute overall concordance score (`0.0` to `1.0`) and classification label.
6. **Stage 6: Dashboard Compilation (`scripts/generate_dashboard.py`)**:
   - Validate combined data payload against `references/dashboard_schema.md`.
   - Embed JSON payload inside `<script id="hpa-dashboard-data" type="application/json">` alongside reference profiles (`TP53`, `ERBB2`) and a live JSON file uploader.
   - Output standalone `./dashboard.html` (>15 KB) featuring the Three-Icon Theme Selector (`#theme-btn-light`, `#theme-btn-dark`, `#theme-btn-system`), the Provenance Strip, the `Structural Data Diagram` (`#hpa-3d-physics-viewport`), the `Interactive Relationship Node Map` (`#hpa-relationship-node-map`), the 2D Vector Cell Map, the `Anatomical IHC Concentration Heatmap Matrix`, the 2D Concordance Scatter Plot (`#concordance-scatter-viewport`), interactive tabs, searchable data explorer, CSV/JSON export controls, and mandatory academic citations.

---

## 5. Non-Functional Requirements

### 5.1 Performance & Rate Limiting
- **API Pacing**: Live HTTP requests to `proteinatlas.org` are rate-limited to a maximum of 2.0 queries per second (minimum 0.5 seconds interval between requests) with exponential backoff on HTTP 429/5xx responses.
- **Offline Execution Speed**: Execution of `scripts/run_pipeline.py --mock` completes end-to-end within 3.0 seconds on standard hardware.

### 5.2 Security & Data Privacy Compliance
- **Zero Personal Identifiers & Protected Health Information**: All sample fixtures, test records, and reference datasets represent aggregate reference biology. No Protected Health Information or Personally Identifiable Information is accepted, stored, or processed.
- **Safe File Handling**: All file paths are resolved relative to the project root directory or explicit user-provided output paths.
- **Self-Contained Execution**: The generated `./dashboard.html` embeds its full dataset and stylesheet so users can open the file directly from disk or serve it via HTTP with Server-Sent Events (SSE) without external dependencies.

---

## 6. Error Handling & Edge Cases

| Failure Scenario / Edge Case | Detection Mechanism | System Behavior & Recovery Strategy | Exit Code |
| :--- | :--- | :--- | :--- |
| **Missing License File** | Pre-flight check before API call or pipeline run | Prints CC BY-SA 4.0 notice to stdout, creates `.licenses/human_protein_atlas_database_visualize_LICENSE.txt` with UTC timestamp, and proceeds. | `0` |
| **Unrecognized Gene Symbol** | Empty search response or missing mock fixture key | Logs descriptive error message identifying the unmapped symbol; raises validation error when input is empty or invalid. | `1` |
| **Malformed Ensembl ID** | Prefix validation (`not startswith('ENSG')`) | Rejects invalid identifier format with structured error message explaining expected `ENSG...` format. | `1` |
| **Network Timeout / HTTP 429 / 503** | HTTP client exception / status code check | Retries up to 3 times with exponential backoff; if network remains unreachable, logs actionable message advising `--mock` flag for offline usage. | `2` |
| **Missing or Empty Tissue Filter Match** | Tissue filter list matches zero tissues in dataset | Preserves valid JSON output structure with `total_tissues_profiled: 0` and empty `organ_systems` dictionary rather than crashing with ZeroDivisionError. | `0` |
| **Unmapped Subcellular Term or Tissue** | Term not present in ontology JSON dictionary | Assigns fallback default category (`Other / Unclassified`, semantic color `#0D9488`, generic Uberon/GO placeholder) and logs a warning without halting execution. | `0` |
| **Corrupted Input JSON File** | `json.JSONDecodeError` or `FileNotFoundError` | Catches exception, logs relative file path and parse error details to stderr, and exits cleanly. | `1` |
| **Incomplete XML Record (Missing IHC Tag)** | XML element lookup returns `None` or empty list | Returns structured empty tissue array `[]` and marks concordance calculation as `"Insufficient IHC Data"` without raising `AttributeError`. | `0` |
