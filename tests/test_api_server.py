"""HTTP-level tests for the FastAPI assurance server (app/server.py)."""

import os
import unittest

from fastapi.testclient import TestClient

from app.server import BASE_DIR, app

SAMPLE_MODEL = "demo_assets/sample_model.pt"


class TestServerHealthAndMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_reports_online(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "online")

    def test_coverage_matrix_lists_capabilities_and_limitations(self):
        body = self.client.get("/api/coverage").json()
        self.assertEqual(body["total_capabilities"], len(body["capabilities"]))
        self.assertGreater(len(body["limitations"]), 0)

    def test_root_serves_html(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/html", res.headers["content-type"])


class TestModelEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_hash_demo_model(self):
        res = self.client.post("/api/model/hash", json={"model_path": SAMPLE_MODEL})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()["sha256_digest"]), 64)

    def test_hash_rejects_path_outside_project(self):
        outside = os.path.abspath(os.path.join(BASE_DIR, os.pardir, "outside.pt"))
        for path in ("../requirements.txt", outside):
            with self.subTest(path=path):
                res = self.client.post("/api/model/hash", json={"model_path": path})
                self.assertEqual(res.status_code, 400)

    def test_whitebox_rejects_traversal(self):
        res = self.client.post(
            "/api/model/whitebox",
            json={"model_path": SAMPLE_MODEL, "reference_model_path": "../../etc/passwd"},
        )
        self.assertEqual(res.status_code, 400)

    def test_missing_model_is_404(self):
        res = self.client.post("/api/model/hash", json={"model_path": "demo_assets/does_not_exist.pt"})
        self.assertEqual(res.status_code, 404)

    def test_run_assurance_rejects_dataset_outside_project(self):
        res = self.client.post("/api/run_assurance", json={"dataset_path": "../secrets/annotations.json"})
        self.assertEqual(res.status_code, 400)


class TestProvenanceEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.demo = cls.client.get("/api/inference/demo_records").json()

    def test_clean_record_verifies(self):
        res = self.client.post("/api/verify_inference_record", json=self.demo["clean_record"])
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["verification_passed"])

    def test_tampered_records_fail_verification(self):
        for name in ("tampered_predictions", "tampered_model_digest"):
            with self.subTest(scenario=name):
                record = self.demo["tampered_scenarios"][name]
                res = self.client.post("/api/verify_inference_record", json=record)
                self.assertEqual(res.status_code, 200)
                self.assertFalse(res.json()["verification_passed"])

    def test_clean_chain_passes_and_sequence_violation_fails(self):
        clean = self.client.post("/api/inference/verify_chain", json=self.demo["clean_chain"]).json()
        self.assertTrue(clean["chain_valid"])

        broken_chain = [self.demo["clean_chain"][0], self.demo["tampered_scenarios"]["sequence_violation"]]
        broken = self.client.post("/api/inference/verify_chain", json=broken_chain).json()
        self.assertFalse(broken["chain_valid"])


class TestAuditTrailEndpoint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_generated_chain_verifies_and_tampering_is_detected(self):
        body = self.client.post("/api/audit/verify").json()
        self.assertTrue(body["is_valid"])

        events = body["events"]
        events[2]["event_summary"] = "tampered summary"
        tampered = self.client.post("/api/audit/verify", json=events).json()
        self.assertFalse(tampered["is_valid"])
        self.assertEqual(tampered["verification_status"], "TAMPER_DETECTED")


if __name__ == "__main__":
    unittest.main()
