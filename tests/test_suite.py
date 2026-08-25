#!/usr/bin/env python3
"""
NetSage AI - Automated Test Suite
=================================
Validates dataset integrity, deterministic rule coverage, diagnostic accuracy,
and Responsible AI audit log compliance.
"""

import os
import sys
import csv
import json
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE_DIR = os.path.join(BASE_DIR, "engine")
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

from rule_checker import DeterministicRuleChecker, RuleFinding
from diagnose_runner import DiagnosticEngine, run_batch_evaluation


class TestNetSageDataset(unittest.TestCase):
    """Verifies cases.csv schema, completeness, and domain coverage."""

    def setUp(self):
        self.csv_path = os.path.join(DATA_DIR, "cases.csv")
        self.assertTrue(os.path.exists(self.csv_path), "cases.csv must exist in data/ directory")
        with open(self.csv_path, mode="r", encoding="utf-8") as f:
            self.cases = list(csv.DictReader(f))

    def test_case_count_and_uniqueness(self):
        """Must have at least 30 cases across lab scenarios."""
        self.assertGreaterEqual(len(self.cases), 30, f"Expected >= 30 cases, found {len(self.cases)}")
        case_ids = [c["case_id"] for c in self.cases]
        self.assertEqual(len(case_ids), len(set(case_ids)), "Case IDs must be strictly unique")

    def test_required_fields_present(self):
        """Each case must contain symptom, show outputs, expected fault, OSI layer, concept tag, severity."""
        required_fields = ["case_id", "title", "symptom", "topology_note", "show_outputs", "expected_fault", "osi_layer", "concept_tag", "severity", "suggested_fix"]
        for case in self.cases:
            if case.get("case_id", "").startswith("CUSTOM-"):
                continue
            for field in required_fields:
                self.assertIn(field, case, f"Case {case.get('case_id')} is missing field '{field}'")
                self.assertTrue(len(case[field].strip()) > 0, f"Field '{field}' in case {case.get('case_id')} cannot be empty")

    def test_domain_coverage(self):
        """Must cover VLAN, gateway, DHCP, DNS, routing, ACL, NAT, and wireless."""
        required_concepts = {"VLAN", "GATEWAY", "DHCP", "DNS", "ROUTING", "ACL", "NAT", "WIRELESS"}
        present_concepts = {c["concept_tag"].upper() for c in self.cases}
        for concept in required_concepts:
            self.assertIn(concept, present_concepts, f"Dataset must include cases for domain '{concept}'")


class TestDeterministicRuleChecker(unittest.TestCase):
    """Verifies that the Python rule checker catches deterministic configuration bugs."""

    def setUp(self):
        self.checker = DeterministicRuleChecker()

    def test_admin_down_detection(self):
        show_output = "GigabitEthernet0/0.10      192.168.10.1    YES manual administratively down down"
        findings = self.checker.check_interface_status(show_output)
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RULE-IF-01")

    def test_native_vlan_mismatch_detection(self):
        show_output = "%CDP-4-NATIVE_VLAN_MISMATCH: Native VLAN mismatch discovered on GigabitEthernet0/1 (1), with Switch-A GigabitEthernet0/1 (10)."
        findings = self.checker.check_native_vlan_mismatch(show_output)
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RULE-VLAN-01")

    def test_missing_default_route_detection(self):
        show_output = "Gateway of last resort is not set\nC 172.16.1.0/24 is directly connected"
        findings = self.checker.check_routing_and_default_route(show_output, "No internet access")
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RULE-ROUTE-01")

    def test_nat_inverted_interfaces_detection(self):
        show_output = "interface GigabitEthernet0/0\n ip nat outside\ninterface GigabitEthernet0/1\n ip nat inside"
        findings = self.checker.check_nat_configuration(show_output, "LAN hosts cannot reach internet")
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RULE-NAT-01")

    def test_duplex_collision_detection(self):
        show_output = "FastEthernet0/24 is up, line protocol is up\n Half-duplex, 100Mb/s\n 389211 late collision, 582914 input errors"
        findings = self.checker.check_duplex_and_collisions(show_output)
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "RULE-L1-02")


class TestResponsibleAiLog(unittest.TestCase):
    """Verifies Responsible AI documentation and log completeness."""

    def test_responsible_ai_log_count(self):
        """Must document at least 5 cases where AI was corrected by human."""
        csv_path = os.path.join(DATA_DIR, "responsible_ai_log.csv")
        self.assertTrue(os.path.exists(csv_path), "responsible_ai_log.csv must exist")
        with open(csv_path, mode="r", encoding="utf-8") as f:
            logs = list(csv.DictReader(f))
        self.assertGreaterEqual(len(logs), 5, f"Expected at least 5 Responsible AI cases, found {len(logs)}")
        for log in logs:
            self.assertIn(log["human_verdict"], ["Accepted", "Edited", "Rejected"], "Verdict must be Accepted, Edited, or Rejected")
            self.assertTrue(len(log["safety_rationale_and_learnings"]) > 10, "Safety rationale must be documented")


class TestDiagnosticEngineAndEvaluation(unittest.TestCase):
    """Verifies diagnostic engine execution and evaluation summary generation."""

    def test_batch_evaluation_execution(self):
        cases_csv = os.path.join(DATA_DIR, "cases.csv")
        out_json = os.path.join(DATA_DIR, "evaluation_summary.json")
        summary = run_batch_evaluation(cases_csv, out_json)
        
        self.assertIn("metrics", summary)
        self.assertGreaterEqual(summary["metrics"]["total_cases"], 30)
        self.assertGreaterEqual(summary["metrics"]["overall_agreement_rate_pct"], 85.0)
        self.assertGreaterEqual(summary["metrics"]["rule_coverage_rate_pct"], 90.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
