import math
import unittest

from fastapi.testclient import TestClient

from main import app


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.data = dict(
            revenue=1000,
            growth_pct=10,
            margin_pct=10,
            shares=10,
            dilution_pct=0,
            pe=15,
            current_price=150,
        )

    def test_known_example_and_no_network_dependency(self):
        response = self.client.post("/api/learn/scenario", json=self.data)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertAlmostEqual(data["revenue"], 1100)
        self.assertAlmostEqual(data["profit"], 110)
        self.assertAlmostEqual(data["eps"], 11)
        self.assertAlmostEqual(data["scenario_price"], 165)
        self.assertAlmostEqual(data["price_change_pct"], 10)

    def test_dilution_reduces_eps_without_changing_profit(self):
        result = self.client.post(
            "/api/learn/scenario", json={**self.data, "dilution_pct": 20}
        ).json()
        self.assertAlmostEqual(result["profit"], 110)
        self.assertAlmostEqual(result["shares"], 12)
        self.assertAlmostEqual(result["eps"], 110 / 12)

    def test_zero_revenue_and_losses_do_not_receive_pe_prices(self):
        for override in ({"growth_pct": -100}, {"margin_pct": 0}, {"margin_pct": -10}):
            with self.subTest(override=override):
                result = self.client.post(
                    "/api/learn/scenario", json={**self.data, **override}
                ).json()
                self.assertEqual(result["status"], "pe_not_applicable")
                self.assertIsNone(result["scenario_price"])
                self.assertIsNone(result["price_change_pct"])

    def test_growth_with_multiple_compression_can_lower_price(self):
        result = self.client.post("/api/learn/scenario", json={**self.data, "pe": 12}).json()
        self.assertAlmostEqual(result["price_change_pct"], -12)

    def test_bounds_reject_missing_nonfinite_and_wrong_fields(self):
        for key, value in (
            ("shares", 0),
            ("shares", 1e-300),
            ("current_price", 0),
            ("revenue", -1),
            ("growth_pct", -101),
            ("margin_pct", 101),
            ("dilution_pct", -1),
            ("pe", 0),
            ("pe", 201),
            ("revenue", "NaN"),
            ("shares", "Infinity"),
            ("unexpected", 1),
        ):
            with self.subTest(key=key, value=value):
                self.assertEqual(
                    self.client.post(
                        "/api/learn/scenario", json={**self.data, key: value}
                    ).status_code,
                    422,
                )
        self.assertEqual(self.client.post("/api/learn/scenario", json={}).status_code, 422)

    def test_extreme_valid_values_remain_finite(self):
        result = self.client.post(
            "/api/learn/scenario",
            json={
                **self.data,
                "revenue": 1e9,
                "growth_pct": 200,
                "margin_pct": 100,
                "shares": 0.000001,
                "current_price": 0.000001,
                "pe": 200,
            },
        ).json()
        for key in ("revenue", "profit", "shares", "eps", "scenario_price", "price_change_pct"):
            self.assertTrue(math.isfinite(result[key]), key)


if __name__ == "__main__":
    unittest.main()
