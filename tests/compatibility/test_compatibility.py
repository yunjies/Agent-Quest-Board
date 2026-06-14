import json
import unittest
from pathlib import Path

from agent_delegation_board import CompatibilityError, check_component_compatibility


ROOT = Path(__file__).resolve().parents[2]


def load_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class CompatibilityTest(unittest.TestCase):
    def test_principal_1_0_is_compatible(self):
        compatibility = load_json("protocol/compatibility.json")
        component = load_json("protocol/fixtures/component-principal-codex.example.json")
        self.assertTrue(check_component_compatibility(component, compatibility))

    def test_unsupported_protocol_rejected(self):
        compatibility = load_json("protocol/compatibility.json")
        component = load_json("protocol/fixtures/component-contractor.example.json")
        component["board_protocol_version"] = "0.9"
        with self.assertRaises(CompatibilityError):
            check_component_compatibility(component, compatibility)

    def test_missing_capability_rejected(self):
        compatibility = load_json("protocol/compatibility.json")
        component = load_json("protocol/fixtures/component-contractor.example.json")
        component["capabilities"] = ["claim_task"]
        with self.assertRaises(CompatibilityError):
            check_component_compatibility(component, compatibility)


if __name__ == "__main__":
    unittest.main()
