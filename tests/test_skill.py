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

"""Unit, smoke, and end-to-end system tests for human-protein-atlas-database-visualize."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
NESTED_SKILL_DIR = PROJECT_ROOT / "skills" / "human_protein_atlas_database_visualize"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import generate_dashboard as gd  # noqa: E402
import hpa_cli  # noqa: E402
import run_pipeline as rp  # noqa: E402
import visualize_concordance as vc  # noqa: E402
import visualize_subcellular as vs  # noqa: E402
import visualize_tissue_ihc as vt  # noqa: E402


class TestSkillComplianceAndSmoke(unittest.TestCase):
    """Smoke tests for repository layout, license headers, and pre-flight license guards."""

    def test_required_directory_and_file_structure(self) -> None:
        """Verify both root and skills/human_protein_atlas_database_visualize/ layouts exist."""
        required_root_files = [
            PROJECT_ROOT / "SKILL.md",
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "LICENSE",
            PROJECT_ROOT / "SKILL_LICENSES.md",
            PROJECT_ROOT / "requirements.txt",
            PROJECT_ROOT / "prd.md",
            PROJECT_ROOT / "documents" / "prd.md",
            PROJECT_ROOT / "assets" / "dashboard_schema.json",
            PROJECT_ROOT / "assets" / "skill_workflow_overview.png",
            PROJECT_ROOT / "references" / "citation.bib",
            PROJECT_ROOT / "references" / "dashboard_schema.md",
            PROJECT_ROOT / "references" / "search-api.md",
            PROJECT_ROOT / "references" / "subcellular_ontology.json",
            PROJECT_ROOT / "references" / "tissue_organ_mapping.json",
            PROJECT_ROOT / "sample_data" / "tp53_entry.json",
            PROJECT_ROOT / "sample_data" / "tp53_subcellular.json",
            PROJECT_ROOT / "sample_data" / "tp53_tissue_ihc.json",
            PROJECT_ROOT / "sample_data" / "erbb2_entry.json",
            PROJECT_ROOT / "sample_data" / "erbb2_subcellular.json",
            PROJECT_ROOT / "sample_data" / "erbb2_tissue_ihc.json",
        ]
        for path in required_root_files:
            self.assertTrue(path.exists(), f"Missing required root file: {path}")

        for rel in [
            "SKILL.md",
            "LICENSE",
            "references/tissue_organ_mapping.json",
            "references/subcellular_ontology.json",
            "scripts/hpa_cli.py",
            "scripts/run_pipeline.py",
            "scripts/generate_dashboard.py",
        ]:
            nested_path = NESTED_SKILL_DIR / rel
            self.assertTrue(nested_path.exists(), f"Missing required nested skill file: {nested_path}")

    def test_apache_headers_in_all_scripts(self) -> None:
        """Ensure every Python file in scripts/ begins with the Apache 2.0 license header."""
        for script_dir in [PROJECT_ROOT / "scripts", NESTED_SKILL_DIR / "scripts"]:
            for py_file in script_dir.glob("*.py"):
                content = py_file.read_text(encoding="utf-8")
                self.assertIn(
                    "Licensed under the Apache License, Version 2.0",
                    content[:250],
                    f"Missing Apache 2.0 header in {py_file}",
                )

    def test_skill_licenses_registration(self) -> None:
        """Verify SKILL_LICENSES.md registers human-protein-atlas-database-visualize."""
        content = (PROJECT_ROOT / "SKILL_LICENSES.md").read_text(encoding="utf-8")
        self.assertIn(
            "human-protein-atlas-database-visualize | https://www.proteinatlas.org/about/licence",
            content,
        )

    def test_license_guard_creation_and_timestamp(self) -> None:
        """Verify pre-flight license guard creates .licenses/human_protein_atlas_database_visualize_LICENSE.txt."""
        license_file = hpa_cli.verify_license_guard()
        self.assertTrue(license_file.exists())
        text = license_file.read_text(encoding="utf-8")
        self.assertIn("https://www.proteinatlas.org/about/licence", text)
        self.assertIn("CC BY-SA 4.0", text)
        self.assertRegex(text, r"Timestamp: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


class TestAnalyticalAndClientUnits(unittest.TestCase):
    """Unit tests for hpa_cli, visualize_subcellular, visualize_tissue_ihc, and visualize_concordance."""

    def test_hpa_cli_mock_subcommands(self) -> None:
        """Test all 5 subcommands in hpa_cli using deterministic --mock mode."""
        res_tp53 = hpa_cli.resolve_ensembl_id("TP53", mock=True)
        self.assertEqual(res_tp53["ensembl_id"], "ENSG00000141510")

        res_erbb2 = hpa_cli.resolve_ensembl_id("ERBB2", mock=True)
        self.assertEqual(res_erbb2["ensembl_id"], "ENSG00000141736")

        ihc_all = hpa_cli.get_tissue_expression("ENSG00000141510", mock=True)
        self.assertEqual(len(ihc_all["tissues"]), 44)

        ihc_filtered = hpa_cli.get_tissue_expression(
            "ENSG00000141510",
            tissues=["cerebral cortex", "liver"],
            mock=True,
        )
        self.assertEqual(len(ihc_filtered["tissues"]), 2)

        subcell = hpa_cli.get_subcellular_location("ENSG00000141510", mock=True)
        self.assertIn("Nucleoplasm", subcell["main_locations"])
        self.assertIn("Cytosol", subcell["additional_locations"])

        entry = hpa_cli.get_atlas_entry("ENSG00000141510", mock=True)
        self.assertEqual(entry["Gene"], "TP53")
        self.assertEqual(entry["Uniprot"], "P04637")

        search_res = hpa_cli.search_hpa("tissue_category_rna:Brain;Tissue enriched", mock=True)
        self.assertGreaterEqual(len(search_res), 1)

    def test_error_handling_edge_cases(self) -> None:
        """Verify defensive error handling on invalid Ensembl IDs and unrecognized symbols."""
        with self.assertRaises(ValueError):
            hpa_cli.resolve_ensembl_id("", mock=True)
        with self.assertRaises(ValueError):
            hpa_cli.resolve_ensembl_id("NONEXISTENT_GENE_XYZ", mock=True)
        with self.assertRaises(ValueError):
            hpa_cli.get_tissue_expression("INVALID_ID_123", mock=True)

    def test_subcellular_enrichment_and_svg(self) -> None:
        """Verify GO term enrichment and SVG active organelle highlighting."""
        subcell_raw = hpa_cli.get_subcellular_location("ENSG00000141510", mock=True)
        enriched = vs.enrich_subcellular_data(subcell_raw)
        self.assertIn("cell-organelle-nucleoplasm", enriched["active_organelle_ids"])
        self.assertIn("cell-organelle-cytosol", enriched["active_organelle_ids"])

        svg = vs.render_subcellular_svg(enriched)
        self.assertIn('id="cell-organelle-nucleoplasm"', svg)
        self.assertIn("GO:0005654", svg)
        self.assertIn("organelle-active-main", svg)

    def test_tissue_ihc_scoring_and_10_systems(self) -> None:
        """Verify 44 tissues group into 10 anatomical systems with accurate staining scores."""
        ihc_raw = hpa_cli.get_tissue_expression("ENSG00000141510", mock=True)
        summary = vt.analyze_tissue_ihc(ihc_raw)
        self.assertEqual(summary["total_tissues_profiled"], 44)
        self.assertEqual(summary["high_expression_count"], 12)
        self.assertEqual(summary["medium_expression_count"], 18)
        self.assertEqual(summary["low_expression_count"], 8)
        self.assertEqual(summary["not_detected_count"], 6)
        self.assertEqual(len(summary["organ_systems"]), 10)

        for sys_name, score in summary["organ_system_scores"].items():
            self.assertGreaterEqual(score, 0.0, f"Negative score for {sys_name}")
            self.assertLessEqual(score, 3.0, f"Score > 3.0 for {sys_name}")

    def test_concordance_quadrant_evaluation(self) -> None:
        """Verify RNA nTPM vs. IHC staining 2x2 concordance calculation."""
        entry = hpa_cli.get_atlas_entry("ENSG00000141510", mock=True)
        ihc = hpa_cli.get_tissue_expression("ENSG00000141510", mock=True)
        conc = vc.evaluate_concordance(entry, ihc)
        self.assertEqual(conc["concordance_score"], 0.82)
        self.assertEqual(conc["concordance_classification"], "High Concordance")
        self.assertEqual(conc["total_evaluated_tissues"], 44)


class TestEndToEndPipelineAndDashboard(unittest.TestCase):
    """End-to-end system tests validating CLI execution and dashboard.html output."""

    def test_pipeline_cli_execution_and_dashboard_verification(self) -> None:
        """Run skills/human_protein_atlas_database_visualize/scripts/run_pipeline.py end-to-end."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                sys.executable,
                str(NESTED_SKILL_DIR / "scripts" / "run_pipeline.py"),
                "--gene",
                "TP53",
                "--mock",
                "-o",
                tmpdir,
            ]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, f"Pipeline failed: {proc.stderr}")

            dashboard_file = Path(tmpdir) / "dashboard.html"
            self.assertTrue(dashboard_file.exists(), "dashboard.html was not generated")
            self.assertGreater(
                dashboard_file.stat().st_size,
                15 * 1024,
                "dashboard.html must be > 15 KB",
            )

            html_text = dashboard_file.read_text(encoding="utf-8")
            match = re.search(
                r'<script id="hpa-dashboard-data" type="application/json">\s*(.*?)\s*</script>',
                html_text,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(match, "Missing #hpa-dashboard-data JSON island")
            island_data = json.loads(match.group(1))
            self.assertEqual(island_data["gene_symbol"], "TP53")
            self.assertEqual(island_data["ensembl_id"], "ENSG00000141510")
            self.assertEqual(island_data["tissue_ihc_summary"]["total_tissues_profiled"], 44)

            self.assertIn("10.1126/science.1260419", html_text)
            self.assertIn("10.1126/science.aal3321", html_text)
            self.assertIn("must not be used as clinical diagnostic or medical guidance", html_text)

            for btn_id, expected_mode in [
                ("theme-btn-light", "light"),
                ("theme-btn-dark", "dark"),
                ("theme-btn-system", "system"),
            ]:
                btn_match = re.search(
                    rf'<button id="{btn_id}"[^>]*data-theme-mode="{expected_mode}"[^>]*>(.*?)</button>',
                    html_text,
                    flags=re.DOTALL,
                )
                self.assertIsNotNone(btn_match, f"Missing #{btn_id} in dashboard.html")
                btn_inner = btn_match.group(1)
                self.assertIn("<svg", btn_inner)
                stripped_non_svg = re.sub(r"<svg.*?</svg>", "", btn_inner, flags=re.DOTALL).strip()
                self.assertEqual(stripped_non_svg, "", f"#{btn_id} must contain only SVG icon")

            for required_token in [
                "#FAFAF9", "#FFFFFF", "#E7E5E4", "#1C1917", "#787774",
                "#0D0E11", "#16171D", "#292A30", "#ECE8E2", "#9A9895",
                "#0D9488", "#D97706", "#4F46E5", "#059669", "#E11D48",
                "DM Sans", "Instrument Serif", "IBM Plex Mono",
                "Structural Data Diagram", "Interactive Relationship Node Map",
            ]:
                self.assertIn(required_token, html_text, f"Missing required design token: {required_token}")

            self.assertIn('id="hpa-3d-physics-viewport"', html_text)
            self.assertIn('id="hpa-relationship-node-map"', html_text)
            self.assertIn('id="concordance-scatter-viewport"', html_text)
            self.assertIn("pipeline_provenance", island_data)
            self.assertIn("system_theme", island_data)

            root_dashboard = PROJECT_ROOT / "dashboard.html"
            self.assertTrue(root_dashboard.exists(), "Project root dashboard.html must exist for local testing")
            workflow_img = PROJECT_ROOT / "assets" / "skill_workflow_overview.png"
            self.assertTrue(workflow_img.exists(), "assets/skill_workflow_overview.png must exist")
            readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
            self.assertIn("Apache License, Version 2.0", readme_text)
            self.assertIn("LICENSE", readme_text)
            self.assertIn("assets/skill_workflow_overview.png", readme_text)


if __name__ == "__main__":
    unittest.main()
