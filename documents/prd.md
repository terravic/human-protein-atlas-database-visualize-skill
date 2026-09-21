# Product Requirement Document: Human Protein Atlas Database Visualize Skill

## 1. User Stories & Scope

### 1.1 Target Audience
The `human-protein-atlas-database-visualize` skill serves three primary user segments across life sciences, translational research, and computational biology:
1. **Translational Scientists and Cell Biologists (Non-Technical End Users)**: Researchers interacting through conversational agent harnesses who require rapid, integrated spatial and tissue-level visual profiles of human proteins without writing Python code or parsing XML/JSON feeds.
2. **Bioinformaticians and Computational Biologists (Technical Users)**: Engineers running command-line pipelines to batch-profile gene sets, assess RNA-to-protein concordance across organ systems, and extract structured JSON summaries for downstream integration.
3. **Autonomous Scientific AI Agents**: Agentic workflows requiring deterministic, rate-limited API access, structured ontology mappings (Uberon and Gene Ontology), and self-contained HTML5 visualization artifacts.

### 1.2 User Stories
- **US-01 (End-to-End Protein Profiling)**: As a cell biologist, I want to provide a gene symbol (such as `TP53` or `ERBB2`) and receive a standalone interactive HTML dashboard (`dashboard.html`) showing subcellular compartment localization, organ-system immunohistochemistry (IHC) expression, RNA-to-protein concordance, and cancer pathology prognostic data.
- **US-02 (3D Physics & 2D Vector Subcellular Spatial Mapping)**: As a microscopist, I want to view both a 3D physics-driven cellular/network simulation (`#hpa-3d-physics-viewport`) and a 2D vector eukaryotic cell schematic highlighting main versus additional subcellular organelles alongside Gene Ontology (GO) Cellular Component identifiers and HPA antibody reliability levels.
- **US-03 (Anatomical Organ-System Grouping)**: As a physiologist, I want 44+ individual normal human tissues automatically grouped into 10 standardized physiological organ systems with numerical IHC staining scores (0.0 to 3.0) and Uberon ontology cross-references.
- **US-04 (RNA vs. Protein Concordance Analysis)**: As a systems biologist, I want to cross-tabulate consensus transcript abundance (nTPM) against IHC protein staining across tissues in a 2x2 quadrant matrix and 2D quantitative scatter plot (`#concordance-scatter-viewport`) to identify concordant expression, potential post-transcriptional repression, or high protein stability/secretion.
- **US-05 (Icon-Only Theme Control & Live Dataset Switching)**: As an interactive reviewer, I want an icon-only Light/Dark theme toggle button (`#theme-toggle-btn`) in the dashboard header alongside a pipeline provenance banner and dataset switcher (`TP53`, `ERBB2`, or custom JSON loader).
- **US-06 (Offline Deterministic Execution)**: As an agent evaluation engineer, I want a `--mock` execution flag that runs the entire query, analysis, and dashboard rendering pipeline using local curated fixtures without requiring network egress.

### 1.3 Scope Definition

| Capability | In Scope | Out of Scope |
| :--- | :--- | :--- |
| **Data Retrieval** | Rate-limited (2.0 QPS) queries to HPA JSON search API and XML gene records; Ensembl ID resolution; offline `--mock` replay. | Bulk downloading of multi-gigabyte raw microscopy TIFF images or full database dumps. |
| **Anatomical Analysis** | Grouping of 44+ HPA normal tissues into 10 organ systems with Uberon IDs and quantitative staining scores (0.0 to 3.0). | Automated histopathological image segmentation of raw tissue microarray slides. |
| **Subcellular & 3D Physics Mapping** | 3D volumetric cell/network spring-damper physics simulation and 2D vector SVG eukaryotic cell schematic mapping 35+ HPA subcellular terms to GO terms. | Raw confocal z-stack voxel reconstruction from raw microscopy files. |
| **Concordance & Pathology** | 2x2 quadrant classification and 2D scatter plot of RNA nTPM vs. IHC levels; summary of 17 major cancer types and prognostic status. | Patient-level survival curve Kaplan-Meier re-estimation from raw clinical trial tables. |
| **Compliance & Licensing** | Pre-flight license guard verification, CC BY-SA 4.0 attribution, Apache 2.0 code headers, and non-clinical research disclaimers. | Clinical diagnostic decision support or processing of patient-identifiable health data (PHI/PII). |

---

## 2. Technical Architecture

The skill is architected as a modular, layered pipeline compatible with standardized `SKILL.md` agent harnesses and standalone CLI environments.

```text
+-----------------------------------------------------------------------------------+
|                           AGENT HARNESS / CLI USER                                |
|          (Invokes SKILL.md workflows or runs scripts/run_pipeline.py)             |
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
|   Renders standalone HTML5 dashboard (dashboard.html) with 3D physics viewport,   |
|   2D vector cell map, 2D scatter plot, and icon-only Light/Dark theme toggle      |
|   Appends mandatory Uhlén (2015) & Thul (2017) citations and research disclaimer  |
+-----------------------------------------------------------------------------------+
```

---

## 3. Functional Requirements

### 3.1 Data Inputs
1. **Primary Gene Identifiers**:
   - Standard HGNC Gene Symbol (string, case-insensitive, e.g., `TP53`, `ERBB2`, `INS`).
   - Ensembl Gene Identifier (string matching regex `^ENSG\d{11}$`, e.g., `ENSG00000141510`).
2. **Optional Filter Parameters**:
   - `--tissues`: Comma-separated list of target tissue names (case-insensitive, e.g., `"cerebral cortex,liver,heart muscle"`).
   - `--query`: Structured HPA search query string for `search-hpa` subcommand.
   - `--mock`: Boolean flag activating deterministic offline fixture execution.
3. **Reference Ontologies**:
   - `references/tissue_organ_mapping.json`: Maps 49 HPA normal tissues to 10 physiological organ systems, hex color palettes, and Uberon ontology IDs.
   - `references/subcellular_ontology.json`: Maps 35 HPA subcellular locations to cellular categories, GO Cellular Component IDs, and SVG element identifiers.

### 3.2 Processing Stages
1. **Stage 1: License Guard Validation**:
   - Check workspace root for `.licenses/human_protein_atlas_database_visualize_LICENSE.txt` (or `.licenses/human_protein_atlas_database_LICENSE.txt`).
   - If absent, output the HPA CC BY-SA 4.0 licensing notification to standard output and write `.licenses/human_protein_atlas_database_visualize_LICENSE.txt` with an ISO 8601 UTC timestamp.
2. **Stage 2: Symbol Resolution & Data Retrieval (`scripts/hpa_cli.py`)**:
   - Resolve gene symbol to canonical Ensembl ID via `search_download.php` or offline fixture table.
   - Retrieve multi-column metadata (`get-atlas-entry`), XML-parsed normal tissue IHC scores (`get-tissue-expression`), and confocal subcellular localization arrays (`get-subcellular-location`).
3. **Stage 3: Subcellular Spatial Mapping (`scripts/visualize_subcellular.py`)**:
   - Match `main_locations` and `additional_locations` against `references/subcellular_ontology.json`.
   - Generate vector SVG eukaryotic cell diagram with distinct visual styling for main compartments (solid vibrant fill + highlight ring), additional compartments (dashed/accent fill), and inactive compartments (muted neutral gray).
4. **Stage 4: Anatomical Organ-System Grouping (`scripts/visualize_tissue_ihc.py`)**:
   - Convert qualitative staining levels into numerical values: `High` = 3.0, `Medium` = 2.0, `Low` = 1.0, `Not detected` = 0.0.
   - Group all tissues into 10 anatomical systems (`Central Nervous System`, `Cardiovascular`, `Digestive`, `Endocrine`, `Immune / Lymphoid`, `Musculoskeletal`, `Reproductive`, `Respiratory`, `Urinary`, `Integumentary`) and compute mean organ system expression scores.
5. **Stage 5: RNA-to-Protein Concordance Scoring (`scripts/visualize_concordance.py`)**:
   - Compare tissue-level RNA consensus abundance (nTPM) with IHC staining scores across profiled tissues.
   - Classify each tissue into one of four quadrants: `Concordant High`, `Concordant Low/Absent`, `Potential Translational Repression`, or `High Protein Stability / Secretion`.
   - Compute overall concordance score (0.0 to 1.0) and classification label.
6. **Stage 6: Dashboard Compilation & Agent Harness Artifact Emission (`scripts/generate_dashboard.py`)**:
   - Validate combined data payload against `references/dashboard_schema.md`.
   - Embed JSON payload inside `<script id="hpa-dashboard-data" type="application/json">` alongside reference profiles (`TP53`, `ERBB2`) and a live JSON file uploader.
   - Output standalone `dashboard.html` (>15 KB) featuring an icon-only Light/Dark mode toggle button (`#theme-toggle-btn` containing only SVG Sun/Moon icons), an Input-to-Processed Pipeline Provenance Banner, a hybrid 3D Physics Viewport (`#hpa-3d-physics-viewport` supporting 3D Cell Organelle Volume and 3D Organ-System Force Network modes) + 2D Vector Cell Map + 2D Concordance Scatter Plot (`#concordance-scatter-viewport`), interactive tabs, searchable data explorer, CSV/JSON export controls, and mandatory academic citations.
   - Write `dashboard.html` both to the local project root (`./dashboard.html`) and as a user-facing artifact (`ArtifactMetadata: { UserFacing: true, Summary: "Interactive Evaluation Dashboard", RequestFeedback: false }`) for immediate rendering inside the agent harness preview pane.

### 3.3 Validation Rules
- Ensembl IDs must start with `ENSG` or be resolved from a valid HGNC symbol.
- IHC staining scores must strictly fall within `{0, 1, 2, 3}` for individual tissues and `[0.0, 3.0]` for aggregate organ system scores.
- Generated HTML dashboards must contain valid JSON in `#hpa-dashboard-data`, active SVG organelle IDs, the icon-only Light/Dark theme toggle button, and required attribution text.

---

## 4. Non-Functional Requirements

### 4.1 Performance & Rate Limiting
- **API Pacing**: Live HTTP requests to `proteinatlas.org` must be rate-limited to a maximum of 2.0 queries per second (minimum 0.5 seconds interval between requests) with exponential backoff on HTTP 429/5xx responses.
- **Offline Latency**: Execution of `run_pipeline.py --mock` must complete end-to-end within 3.0 seconds on standard hardware.

### 4.2 Security, HCLS Safety & HIPAA Privacy Compliance
- **Zero PHI/PII**: All sample fixtures, test records, and reference datasets represent aggregate reference biology or synthetic reference fixtures. No Protected Health Information (PHI) or Personally Identifiable Information (PII) is accepted, stored, or processed.
- **Safe File Handling**: All file paths are resolved relative to the skill directory or explicit user-provided output paths without shell injection vulnerabilities.
- **Offline Self-Containment**: The generated `dashboard.html` embeds its full dataset and CSS stylesheet so users can open the file directly via `file:///` without exposing research queries to external servers.

### 4.3 Extensibility & Portability
- **Relative Path Resolution**: All scripts dynamically resolve `SKILL_DIR` and workspace paths via `pathlib.Path(__file__).resolve()`.
- **Graceful Dependency Fallback**: If `polite-http` is not installed in the active Python environment, `hpa_cli.py` transparently falls back to Python standard library `urllib.request` with built-in token-bucket rate limiting (2.0 QPS).

---

## 5. Error Handling & Edge Cases

| Failure Scenario / Edge Case | Detection Mechanism | System Behavior & Recovery Strategy | Exit Code |
| :--- | :--- | :--- | :--- |
| **Missing License File** | Pre-flight check before API call or pipeline run | Prints CC BY-SA 4.0 notice to stdout, creates `.licenses/human_protein_atlas_database_visualize_LICENSE.txt` with UTC timestamp, and proceeds. | `0` |
| **Unrecognized Gene Symbol** | Empty search response or missing mock fixture key | Logs descriptive error message identifying the unmapped symbol; raises clean validation error when input is empty or invalid. | `1` |
| **Malformed Ensembl ID** | Prefix validation (`not startswith('ENSG')`) | Rejects invalid identifier format with structured error message explaining expected `ENSG...` format. | `1` |
| **Network Timeout / HTTP 429 / 503** | HTTP client exception / status code check | Retries up to 3 times with exponential backoff; if network remains unreachable, logs actionable message advising `--mock` flag for offline usage. | `2` |
| **Missing or Empty Tissue Filter Match** | Tissue filter list matches zero tissues in dataset | Preserves valid JSON output structure with `total_tissues_profiled: 0` and empty `organ_systems` dictionary rather than crashing with ZeroDivisionError. | `0` |
| **Unmapped Subcellular Term or Tissue** | Term not present in ontology JSON dictionary | Assigns fallback default category (`Other / Unclassified`, neutral color `#64748B`, generic Uberon/GO placeholder) and logs a warning without halting execution. | `0` |
| **Corrupted Input JSON File** | `json.JSONDecodeError` or `FileNotFoundError` | Catches exception, logs exact file path and parse error details to stderr, and exits cleanly. | `1` |
| **Incomplete XML Record (Missing IHC Tag)** | XML element lookup returns `None` or empty list | Returns structured empty tissue array `[]` and marks concordance calculation as `"Insufficient IHC Data"` without raising `AttributeError`. | `0` |
