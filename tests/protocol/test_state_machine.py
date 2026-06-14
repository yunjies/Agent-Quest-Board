import unittest

from agent_delegation_board import StateTransitionError, transition


class StateMachineTest(unittest.TestCase):
    def test_approved_is_only_path_to_closed(self):
        self.assertEqual(transition("approved", "closed"), "closed")
        with self.assertRaises(StateTransitionError):
            transition("failed", "closed")
        with self.assertRaises(StateTransitionError):
            transition("rejected", "closed")

    def test_rejected_routes_to_revision_requested(self):
        self.assertEqual(transition("reviewing", "rejected"), "rejected")
        self.assertEqual(transition("rejected", "revision_requested"), "revision_requested")

    def test_illegal_transition_rejected(self):
        with self.assertRaises(StateTransitionError):
            transition("published", "closed")


if __name__ == "__main__":
    unittest.main()
