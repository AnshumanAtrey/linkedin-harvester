"""Contract for harvester.inputs: parse any input shape, never raise.

These lock the fix for the run-level failures that mis-shaped input used to cause
(a list with a non-string item, a wrapped dict, a delimited string in the bulk
field, minConfidencePct sent as a string). Pure stdlib, no Apify SDK needed:

    python -m unittest discover -s tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harvester.inputs import collect_emails, confidence_gate  # noqa: E402


class CollectEmails(unittest.TestCase):
    def test_single_and_bulk(self):
        self.assertEqual(collect_emails({"email": "Jane@Stripe.com"}), ["jane@stripe.com"])
        self.assertEqual(collect_emails({"emails": ["a@x.io", "b@y.io"]}), ["a@x.io", "b@y.io"])

    def test_dedup_across_fields_case_insensitive(self):
        self.assertEqual(
            collect_emails({"email": "a@x.io", "emails": ["A@X.io", "b@y.io"]}),
            ["a@x.io", "b@y.io"],
        )

    def test_delimited_string_in_bulk_field(self):
        # The common paste mistake: a list typed as one string. Used to become ['@'].
        self.assertEqual(
            collect_emails({"emails": "a@b.com, c@d.com\n e@f.com; g@h.com"}),
            ["a@b.com", "c@d.com", "e@f.com", "g@h.com"],
        )

    def test_name_wrapped_address(self):
        self.assertEqual(collect_emails({"email": "Jane Doe <jane@x.io>"}), ["jane@x.io"])

    def test_junk_items_do_not_crash(self):
        # Each of these used to raise AttributeError/TypeError and FAIL the run.
        self.assertEqual(collect_emails({"emails": ["ok@x.io", 123, None, ""]}), ["ok@x.io"])
        self.assertEqual(collect_emails({"emails": [{"email": "w@x.io"}]}), ["w@x.io"])
        self.assertEqual(collect_emails({"email": ["list@x.io"]}), ["list@x.io"])

    def test_empty_and_unfindable(self):
        self.assertEqual(collect_emails({}), [])
        self.assertEqual(collect_emails({"email": ""}), [])
        self.assertEqual(collect_emails({"emails": ["notanemail", "also bad"]}), [])


class ConfidenceGate(unittest.TestCase):
    def test_int_and_default(self):
        self.assertEqual(confidence_gate(90), 0.9)
        self.assertEqual(confidence_gate(None), 0.8)

    def test_string_does_not_crash(self):
        # Used to raise TypeError: str / float and FAIL the run.
        self.assertEqual(confidence_gate("90"), 0.9)
        self.assertEqual(confidence_gate("not a number"), 0.8)

    def test_clamped(self):
        self.assertEqual(confidence_gate(999), 1.0)
        self.assertEqual(confidence_gate(-5), 0.0)


if __name__ == "__main__":
    unittest.main()
