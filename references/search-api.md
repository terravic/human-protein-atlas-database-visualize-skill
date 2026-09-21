# Human Protein Atlas Search and Download API Reference

## 1. JSON Search API (`search_download.php`)

Endpoint: `https://www.proteinatlas.org/api/search_download.php`

### Query Parameters
- `search`: Search query string (e.g., `TP53`, `ENSG00000141510`, or field queries such as `tissue_category_rna:Brain;Tissue enriched`).
- `format`: Output format (`json` or `tsv`).
- `columns`: Comma-separated list of column codes to return.
- `compress`: Whether to gzip response (`no` or `yes`).

### Supported Column Codes
| Code | Field Name | Description |
| :--- | :--- | :--- |
| `g` | `Gene` | Official HGNC gene symbol |
| `eg` | `Ensembl` | Ensembl gene identifier (`ENSG...`) |
| `gs` | `Gene synonym` | Known alias and synonym symbols |
| `gd` | `Gene description` | Full descriptive name of the gene/protein |
| `up` | `Uniprot` | Primary UniProtKB accession |
| `scl` | `Subcellular location` | All experimentally detected subcellular locations |
| `scml` | `Subcellular main location` | Primary subcellular compartments |
| `scal` | `Subcellular additional location` | Secondary subcellular compartments |
| `pc` | `Protein class` | Functional classification categories |
| `ccdp` | `Cancer prognostics` | Summary of prognostic survival associations across cancer types |
| `ectissue` | `Enhanced_tissues` | Tissues with enhanced expression |
| `rnats` | `RNA tissue specificity` | Specificity category across tissues (`Tissue enriched`, `Low tissue specificity`, etc.) |
| `rnatd` | `RNA tissue distribution` | Distribution category across tissues (`Detected in all`, `Detected in many`, etc.) |
| `rnatss` | `RNA tissue specific nTPM` | Consensus normalized transcripts per million (nTPM) per tissue |

## 2. Gene Entry XML API

Endpoint: `https://www.proteinatlas.org/{ensembl_id}.xml`

### Key XML Elements
- `<tissueExpression technology="IHC">`: Contains `<data>` elements for each normal tissue, with `<tissue>` name and `<level type="expression">` (`High`, `Medium`, `Low`, `Not detected`).
- `<verification type="validation">`: Contains HPA antibody validation and RNA-to-protein reliability scores (`Enhanced`, `Supported`, `Approved`, `Uncertain`).
- `<subcellularExpression>`: Contains confocal immunofluorescence (ICC-IF) organelle localization entries and reliability status.

## 3. Rate Limiting & Access Policy
All requests to `proteinatlas.org` must be rate-limited to at most 2.0 queries per second (QPS) and comply with the Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) license.
