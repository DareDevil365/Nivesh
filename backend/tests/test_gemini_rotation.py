import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import httpx

from config import settings
from services.gemini_client import GeminiKeyRotator, _retry_after


class GeminiRotationTests(unittest.TestCase):
    def pool(self, keys="alpha,beta", projects=""):
        with (
            patch.object(settings, "GEMINI_API_KEYS", keys),
            patch.object(settings, "GEMINI_KEY_PROJECTS", projects),
        ):
            return GeminiKeyRotator()

    def test_deduplicate_and_rotate_without_exposing_credentials(self):
        pool = self.pool(" alpha, beta,alpha, ")
        self.assertEqual([pool.get_active_key() for _ in range(3)], ["alpha", "beta", "alpha"])
        self.assertEqual(pool.get_status()["total_keys"], 2)
        self.assertNotIn("alpha", str(pool.get_status()))
        self.assertNotIn("alpha", repr(pool.keys))

    def test_invalid_project_mapping_fails_without_disclosing_keys(self):
        for keys, projects in [("alpha,beta", "one"), ("alpha,alpha", "one,two")]:
            with self.assertRaises(ValueError) as error:
                self.pool(keys, projects)
            self.assertNotIn("alpha", str(error.exception))

    def test_429_pauses_entire_unlabelled_pool_and_recovers(self):
        pool = self.pool()
        with patch("services.gemini_client.time.monotonic", return_value=100):
            pool.report_error("alpha", 429, 120)
            pool.report_success("beta")
            self.assertIsNone(pool.get_active_key())
            self.assertEqual(pool.get_status()["active_keys"], 0)
        with patch("services.gemini_client.time.monotonic", return_value=221):
            self.assertIsNotNone(pool.get_active_key())
            self.assertEqual(pool.get_status()["active_keys"], 2)

    def test_auth_rejection_falls_back_but_does_not_switch_model(self):
        pool = self.pool()
        with patch(
            "services.gemini_client.httpx.post",
            side_effect=[httpx.Response(403), httpx.Response(200)],
        ) as post:
            response, key = pool.post("https://example.com/model", {"contents": []})
        self.assertEqual((response.status_code, key), (200, "beta"))
        self.assertEqual(pool.keys[0].status, "disabled")
        self.assertEqual(post.call_args_list[0].args, post.call_args_list[1].args)
        self.assertEqual(post.call_args.kwargs["headers"], {"x-goog-api-key": "beta"})

    def test_429_only_falls_back_to_another_project(self):
        pool = self.pool("alpha,beta,gamma", "one,one,two")
        with patch(
            "services.gemini_client.httpx.post",
            side_effect=[httpx.Response(429, headers={"Retry-After": "120"}), httpx.Response(200)],
        ) as post:
            response, key = pool.post("https://example.com/model", {})
        self.assertEqual((response.status_code, key), (200, "gamma"))
        self.assertEqual(post.call_count, 2)
        self.assertEqual([k.status for k in pool.keys], ["cooldown", "cooldown", "active"])

    def test_same_project_quota_and_global_errors_do_not_retry(self):
        for status in (429, 400, 404, 500, 503):
            pool = self.pool()
            with patch(
                "services.gemini_client.httpx.post", return_value=httpx.Response(status)
            ) as post:
                response, _ = pool.post("https://example.com/model", {})
            self.assertEqual(response.status_code, status)
            self.assertEqual(post.call_count, 1)

    def test_attempts_are_bounded_and_network_errors_are_not_replayed(self):
        pool = self.pool("a,b,c,d")
        with patch("services.gemini_client.httpx.post", return_value=httpx.Response(401)) as post:
            pool.post("https://example.com/model", {})
        self.assertEqual(post.call_count, 3)
        with patch(
            "services.gemini_client.httpx.post", side_effect=httpx.ReadTimeout("timeout")
        ) as post:
            with self.assertRaises(httpx.ReadTimeout):
                self.pool().post("https://example.com/model", {})
        self.assertEqual(post.call_count, 1)

    def test_thread_safe_counters(self):
        pool = self.pool()

        def success(_):
            pool.report_success(pool.get_active_key())

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(success, range(1000)))
        self.assertEqual(pool.get_status()["total_calls_today"], 1000)
        self.assertEqual([k.calls_today for k in pool.keys], [500, 500])

    def test_retry_after_parsing(self):
        self.assertEqual(_retry_after("120"), 120)
        with patch("services.gemini_client.time.time", return_value=0):
            self.assertEqual(_retry_after("Thu, 01 Jan 1970 00:02:00 GMT"), 120)
        for value in (None, "garbage", "nan", "inf", "-1"):
            self.assertIsNone(_retry_after(value))
