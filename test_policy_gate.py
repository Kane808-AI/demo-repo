import json
import unittest

from policy_gate import Action, Claim, Evidence, Status, Tier, audit_line, decide, verify


class DecideTest(unittest.TestCase):
    def test_read_only_is_automatic(self):
        d = decide(Action("read_pnl", read_only=True))
        self.assertEqual(d.tier, Tier.AUTOMATIC)
        self.assertEqual(d.matched_rule, "auto.read")

    def test_outbound_needs_approval(self):
        self.assertEqual(
            decide(Action("draft_email", outbound=True)).tier,
            Tier.APPROVAL_REQUIRED,
        )

    def test_money_is_forbidden(self):
        self.assertEqual(decide(Action("wire_funds", moves_money=True)).tier, Tier.FORBIDDEN)

    def test_protected_is_forbidden(self):
        self.assertEqual(
            decide(Action("file_motion", touches_protected=True)).tier,
            Tier.FORBIDDEN,
        )

    def test_system_of_record_is_forbidden(self):
        self.assertEqual(
            decide(Action("edit_case", mutates_system_of_record=True)).tier,
            Tier.FORBIDDEN,
        )

    def test_non_read_write_notifies(self):
        self.assertEqual(
            decide(Action("write_note")).tier,
            Tier.NOTIFY_AND_PROCEED,
        )

    def test_fails_closed_on_unknown(self):
        d = decide(Action("mystery"))
        self.assertNotEqual(d.tier, Tier.AUTOMATIC)
        self.assertNotEqual(d.tier, Tier.FORBIDDEN)


class VerifyTest(unittest.TestCase):
    def test_no_evidence_stays_claimed(self):
        self.assertEqual(verify(Claim("did the thing")), Status.CLAIMED)

    def test_independent_fresh_observed_verifies(self):
        ev = Evidence(source="readback", observed=True)
        self.assertEqual(verify(Claim("did the thing", ev)), Status.VERIFIED)

    def test_not_observed_disproves(self):
        ev = Evidence(source="readback", observed=False)
        self.assertEqual(verify(Claim("did the thing", ev)), Status.DISPROVED)

    def test_not_independent_inconclusive(self):
        ev = Evidence(source="self-report", observed=True, independent=False)
        self.assertEqual(verify(Claim("did the thing", ev)), Status.INCONCLUSIVE)

    def test_stale_inconclusive(self):
        ev = Evidence(source="readback", observed=True, fresh=False)
        self.assertEqual(verify(Claim("did the thing", ev)), Status.INCONCLUSIVE)


class AuditTest(unittest.TestCase):
    def test_audit_line_is_json(self):
        a = Action("read_pnl", read_only=True, scope="finance")
        line = audit_line(a, decide(a))
        parsed = json.loads(line)
        self.assertEqual(parsed["action"], "read_pnl")
        self.assertEqual(parsed["tier"], "automatic")


if __name__ == "__main__":
    unittest.main()
