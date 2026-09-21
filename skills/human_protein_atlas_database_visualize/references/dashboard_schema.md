# HPA Dashboard JSON Data Island Schema

The standalone interactive HTML5 dashboard (`dashboard.html`) embeds a structured JSON payload inside `<script id="hpa-dashboard-data" type="application/json">`. This schema allows the dashboard to render completely offline via `file:///` without requiring an active web server or live API requests.

```json
{
  "gene_symbol": "TP53",
  "ensembl_id": "ENSG00000141510",
  "uniprot_id": "P04637",
  "gene_description": "tumor protein p53",
  "gene_synonyms": ["p53", "LFS1"],
  "validation_status": "Approved",
  "rna_protein_agreement": {
    "reliability": "Approved",
    "description": "Consistency between RNA-seq and antibody staining"
  },
  "subcellular_summary": {
    "main_locations": ["Nucleoplasm"],
    "additional_locations": ["Cytosol"],
    "locations_all": ["Nucleoplasm", "Cytosol"],
    "active_organelle_ids": ["cell-organelle-nucleoplasm", "cell-organelle-cytosol"]
  },
  "tissue_ihc_summary": {
    "total_tissues_profiled": 44,
    "high_expression_count": 12,
    "medium_expression_count": 18,
    "low_expression_count": 8,
    "not_detected_count": 6,
    "organ_systems": {
      "Central Nervous System": [
        {"tissue": "cerebral cortex", "organ": "brain", "level": "Medium", "score": 2},
        {"tissue": "cerebellum", "organ": "brain", "level": "High", "score": 3}
      ]
    }
  },
  "concordance_summary": {
    "concordance_score": 0.82,
    "concordance_classification": "High Concordance",
    "discordant_tissues": []
  },
  "pathology_summary": {
    "prognostic_status": "Unfavorable",
    "cancer_types_summary": "High expression associated with poor prognosis in head and neck cancer"
  }
}
```
