from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class OpenApiContractTests(unittest.TestCase):
    def test_main_contract_is_parseable_and_exposes_core_paths(self):
        contract = yaml.safe_load(
            (ROOT / "contracts" / "openapi.yaml").read_text(encoding="utf-8")
        )
        paths = contract["paths"]
        schemas = contract["components"]["schemas"]

        for path in (
            "/tasks",
            "/analysis-records",
            "/action-plans",
            "/modules",
            "/ai/invoke",
            "/mood-checkins",
        ):
            self.assertIn(path, paths)

        self.assertIn("CreateAnalysisRecordRequest", schemas)
        self.assertIn("ModuleUpsertRequest", schemas)
        self.assertIn("CreateMoodCheckinRequest", schemas)
        self.assertIn("CreateActionPlanRequest", schemas)
        self.assertIn("UpdateActionPlanItemRequest", schemas)


if __name__ == "__main__":
    unittest.main()
