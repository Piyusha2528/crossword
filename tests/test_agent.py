import unittest
from src.agent import SupportAgent, OrderTool

class AgentTests(unittest.TestCase):
    def test_order_normalization_and_privacy(self):
        result = OrderTool().lookup(" ord 1007 ", "status")
        self.assertEqual(result["order"]["order_id"], "ORD-1007")
        self.assertNotIn("'customer':", str(result)); self.assertNotIn("'internal':", str(result))

    def test_session_followup_keeps_shipping_subject(self):
        agent = SupportAgent(); agent.respond("Do you ship internationally?", "one")
        self.assertIn("business days", agent.respond("What about Canada?", "one").answer)

    def test_sessions_do_not_mix(self):
        agent = SupportAgent(); agent.respond("Do you ship internationally?", "one")
        self.assertTrue(agent.respond("What about it?", "two").handoff)

    def test_cancelled_hides_stale_eta(self):
        answer = SupportAgent().respond("When will ORD-1004 arrive?").answer
        self.assertNotIn("August 16", answer); self.assertIn("cancelled", answer)

    def test_current_standard_qualifier_overrides_previous_trailplus_context(self):
        agent = SupportAgent()
        agent.respond("My TrailPlus membership was active. What is my return window?", "returns")
        result = agent.respond("For a normal user, what is the return window?", "returns")
        self.assertIn("30 calendar days", result.answer)
        self.assertNotIn("45 calendar days", result.answer)
        self.assertEqual(result.sources, ["01-returns-policy-current.md — Standard return window"])

if __name__ == "__main__":
    unittest.main()
