"""Truth-separation and content checks for deterministic CEO reports."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from company_os.policy import ApprovalClass
from company_os.reporting import _cell, format_money, generate_ceo_report, write_ceo_report
from company_os.scoring import score_from_evidence
from company_os.storage import CompanyStore


class CEOReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_directory.cleanup)
        self.root = Path(self.temp_directory.name)
        (self.root / "PAUSE_AUTONOMY").write_text("paused\n", encoding="utf-8")
        self.store = CompanyStore(self.root / "state" / "company.db")
        self.store.initialize()
        self.addCleanup(self.store.close)

    def test_empty_report_states_unknowns_without_inventing_activity(self) -> None:
        report = generate_ceo_report(self.store, repo_root=self.root)

        self.assertIn("# K.O. Enterprises CEO Report", report)
        self.assertIn("Operating state: **PAUSED**", report)
        self.assertIn("Audit chain: **valid**", report)
        self.assertIn("No opportunities recorded", report)
        self.assertIn("No approvals are pending", report)
        self.assertIn("none are recorded, not that risk is absent", report)
        self.assertIn("USD 0.00", report)
        self.assertIn("missing records are never inferred", report)

    def test_populated_report_separates_actuals_from_forecasts(self) -> None:
        opportunity = self.store.create_opportunity(
            "Operator reconciliation",
            buyer="SaaS operators",
            entry_wedge="Read-only error report",
        )
        self.store.add_evidence(
            opportunity["id"],
            criterion="need_severity",
            claim="A directly observed workflow failure.",
            source_uri="https://evidence.test/failure",
            strength="strong",
            rating=0.8,
            confidence=0.9,
            observed_at="2026-08-24",
            expires_at="2099-01-01",
        )
        self.store.add_evidence(
            opportunity["id"],
            criterion="reachable_beachhead",
            claim="A permission-based channel is available.",
            source_uri="https://evidence.test/channel",
            strength="moderate",
            rating=0.6,
            confidence=0.8,
            observed_at="2026-08-24",
            expires_at="2099-01-01",
        )
        evidence = self.store.list_evidence(opportunity["id"])
        self.store.save_score(
            opportunity["id"],
            score_from_evidence(evidence),
            inputs={"evidence_ids": [row["id"] for row in evidence]},
        )
        self.store.create_experiment(
            opportunity["id"],
            name="Five-interview problem test",
            hypothesis="Qualified operators report the same costly failure.",
            method="Permission-based interviews only.",
            success_metric="Three specific matching workflows.",
            kill_metric="Fewer than two matching workflows.",
            planned_cost_cents=0,
        )
        self.store.request_approval(
            action="spend_money",
            rationale="Only if a later paid test is justified.",
            risk="Evidence may not justify the expense.",
            estimated_cost_cents=2000,
            reversibility="reversible",
            approval_class=ApprovalClass.CEO_APPROVAL_REQUIRED,
            expires_at="2099-01-01",
        )
        self.store.record_risk(
            category="evidence",
            title="Small sample",
            description="Early evidence may not generalize.",
            likelihood=3,
            impact=3,
            mitigation="Predefine a counter-thesis.",
        )
        self.store.record_decision(
            title="Do not build yet",
            decision="validate",
            rationale="Behavioral evidence is still limited.",
            decided_by="company_os",
            opportunity=opportunity["id"],
        )
        self.store.record_revenue(
            amount_cents=1000,
            description="Verified sale",
            status="cleared",
            external_reference="sale:verified",
        )
        self.store.record_revenue(
            amount_cents=5000,
            description="Scenario only",
            entry_type="projection",
            status="projected",
        )
        self.store.record_cost(
            amount_cents=300,
            description="Actual cost",
            status="paid",
            source_reference="receipt:actual",
        )
        self.store.record_cost(
            amount_cents=400, description="Potential cost", status="estimated"
        )

        report = generate_ceo_report(self.store, repo_root=self.root)

        self.assertIn(
            "transaction-status assertions and projections are deliberately separated",
            report,
        )
        self.assertIn("does not independently authenticate", report)
        self.assertIn("All-time ledger totals", report)
        self.assertIn("USD 10.00", report)
        self.assertIn("USD 50.00", report)
        self.assertIn("USD 3.00", report)
        self.assertIn("USD 4.00", report)
        self.assertIn("USD 7.00", report)
        self.assertIn("Operator reconciliation", report)
        self.assertIn("Advancement-ready", report)
        self.assertIn("score below 65 advancement threshold", report)
        self.assertIn("none is advancement-ready", report)
        self.assertNotIn(
            "Define one zero-spend validation experiment",
            report,
        )
        self.assertIn("Five-interview problem test", report)
        self.assertIn("Only if a later paid test is justified", report)
        self.assertIn("Evidence may not justify the expense", report)
        self.assertIn("reversibility: reversible", report)
        self.assertIn("expires: 2099-01-01T00:00:00Z", report)
        self.assertIn("not executable authority", report)
        self.assertIn("Small sample", report)
        self.assertIn("Do not build yet", report)

    def test_write_report_creates_parent_and_exact_generated_content(self) -> None:
        destination = self.root / "reports" / "generated" / "ceo.md"
        returned = write_ceo_report(
            self.store,
            destination,
            title="Phase 0 Check",
            repo_root=self.root,
        )
        self.assertEqual(destination, returned)
        self.assertTrue(destination.is_file())
        self.assertIn("# Phase 0 Check", destination.read_text(encoding="utf-8"))

    def test_money_format_handles_sign_and_currency(self) -> None:
        self.assertEqual("USD 12,345.67", format_money(1_234_567))
        self.assertEqual("-EUR 1.05", format_money(-105, "EUR"))

    def test_markdown_cells_escape_untrusted_html_and_table_delimiters(self) -> None:
        self.assertEqual(
            "&lt;script&gt;alert(1)&lt;/script&gt; \\| next",
            _cell("<script>alert(1)</script> |\nnext"),
        )
        self.assertEqual(
            "\\[link\\](https://untrusted.test)",
            _cell("[link](https://untrusted.test)"),
        )


if __name__ == "__main__":
    unittest.main()
