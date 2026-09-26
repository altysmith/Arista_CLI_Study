import unittest

from arista_sim.labs import get_lab
from arista_sim.post_lab_review import post_lab_review


class PostLabReviewTests(unittest.TestCase):
    def test_ticket_review_identifies_specific_fault_and_safe_path(self):
        review = post_lab_review(get_lab("campus-trunk-ticket"))
        self.assertIn("VLAN 20", review["root_cause"])
        self.assertIn("management VLAN 99", review["avoid"])
        self.assertGreaterEqual(len(review["path"]), 4)

    def test_build_lab_has_honest_non_ticket_review(self):
        review = post_lab_review(get_lab("access-vlan-basics"))
        self.assertIn("build-and-verify", review["symptom"])
        self.assertIn("VLAN 20", review["root_cause"])
