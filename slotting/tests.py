"""
Smoke tests for the Django UI. Run with:

    python manage.py test

These don't replace real browser testing, but they do exercise every
view's actual code path (including disk reads/writes for the CRUD
flow) without needing a running server.
"""

import csv

from django.test import TestCase

from app.config import ALL_TABLES, ALL_ANALYSES, ALL_REPORTS, ORDERS_CONFIG


class EveryPageLoadsTests(TestCase):
    """Every table/analysis/report page should return 200, both blank and submitted."""

    def test_home(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_table_pages(self):
        for cfg in ALL_TABLES:
            with self.subTest(table=cfg.key):
                self.assertEqual(self.client.get(f"/table/{cfg.key}/").status_code, 200)
                self.assertEqual(self.client.get(f"/table/{cfg.key}/?q=a").status_code, 200)
                self.assertEqual(self.client.get(f"/table/{cfg.key}/add/").status_code, 200)

    def test_analysis_and_report_pages(self):
        for cfg in ALL_ANALYSES + [r for r in ALL_REPORTS if r.key != "warehouse_map"]:
            with self.subTest(analysis=cfg.key):
                self.assertEqual(self.client.get(f"/run/{cfg.key}/").status_code, 200)
                resp = self.client.get(f"/run/{cfg.key}/?start=2025-01-01&end=2026-12-31")
                self.assertEqual(resp.status_code, 200)
                export = self.client.get(f"/run/{cfg.key}/export/?start=2025-01-01&end=2026-12-31")
                if cfg.result_columns or True:  # all current configs export fine
                    self.assertEqual(export.status_code, 200)

    def test_warehouse_map(self):
        self.assertEqual(self.client.get("/warehouse-map/").status_code, 200)
        resp = self.client.get("/warehouse-map/?start=2025-01-01&end=2026-12-31&metric=units")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"plotly", resp.content.lower())
        self.assertEqual(
            self.client.get("/warehouse-map/export/?start=2025-01-01&end=2026-12-31").status_code, 200
        )


class AnalysisContentTests(TestCase):
    """Spot-check that real numbers come through, not just 200s."""

    def test_velocity_summary(self):
        resp = self.client.get("/run/velocity/?start=2025-01-01&end=2026-12-31")
        self.assertIn(b"active SKUs analyzed", resp.content)

    def test_abc_export_row_count(self):
        resp = self.client.get("/run/abc_ranking/export/?start=2025-01-01&end=2026-12-31")
        rows = resp.content.decode().strip().split("\n")
        self.assertGreater(len(rows), 1)  # header + at least one data row

    def test_option_defaults_apply_when_omitted(self):
        """Regression test: clicking a date-preset link only sets start/end,
        not opt_* params - option defaults must still apply rather than
        crashing on None (see _resolve_options in views.py)."""
        resp = self.client.get("/run/abc_ranking/?start=2025-01-01&end=2026-12-31")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(b"Internal Server Error", resp.content)


class CrudFlowTests(TestCase):
    """Full add -> edit -> delete round trip through real views, with real
    disk reads/writes via DataManager (restores the file afterward)."""

    TEST_ID = "CUST-999999"

    def tearDown(self):
        # Best-effort cleanup in case an assertion fails mid-test
        with open("data/customers.csv", newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        if any(r["customer_id"] == self.TEST_ID for r in rows):
            self.client.post(f"/table/customers/delete/?key={self.TEST_ID}", {"key": self.TEST_ID})

    def test_add_edit_delete_round_trip(self):
        resp = self.client.post("/table/customers/add/", {
            "customer_id": self.TEST_ID,
            "customer_name": "Django Test Customer",
            "customer_type": "Retail",
            "customer_status": "Active",
            "email": "test@example.com",
        }, follow=True)
        self.assertContains(resp, "Record added")

        with open("data/customers.csv", newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        added = [r for r in rows if r["customer_id"] == self.TEST_ID]
        self.assertEqual(len(added), 1)

        resp = self.client.post(f"/table/customers/edit/?key={self.TEST_ID}", {
            **added[0], "customer_name": "Django Test Customer EDITED",
        }, follow=True)
        self.assertContains(resp, "Record updated")

        with open("data/customers.csv", newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        edited = [r for r in rows if r["customer_id"] == self.TEST_ID]
        self.assertEqual(edited[0]["customer_name"], "Django Test Customer EDITED")

        resp = self.client.post(f"/table/customers/delete/?key={self.TEST_ID}",
                                {"key": self.TEST_ID}, follow=True)
        self.assertContains(resp, "Record deleted")

        with open("data/customers.csv", newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        remaining = [r for r in rows if r["customer_id"] == self.TEST_ID]
        self.assertEqual(len(remaining), 0)
