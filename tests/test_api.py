import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from api.main import app


def _valid_survey_payload():
    return {
        "participant_id": "participant-123",
        "prolific_id": "prolific-abc",
        "qualtrics_response_id": "R_123456",
        "topic_condition": "teams",
        "topic_usage": "daily",
        "topic_behavior": "often",
        "pre_block_id": "PERS_TEAMS",
        "pre_topic": "teams",
        "pre_personalization": "personalized",
        "pre_is_control": False,
        "block_responses": {
            "opinion": 4,
            "opinion_reason": "I have mixed feelings about Teams.",
            "statements": [
                {"statement_id": f"stmt{i}", "response": 3} for i in range(1, 8)
            ],
            "feeling_strength": 5,
            "topic_importance": 4,
        },
        "demographics": {
            "age": 30,
            "gender": "male",
            "education": "bachelor",
            "kids_in_school": "no",
            "political_belief": "moderate",
        },
        "survey_comment": "No additional comments.",
        "ip_address": "127.0.0.1",
        "user_agent": "pytest-client",
    }


class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    # Endpoint under test: GET /
    def test_root_returns_api_metadata(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["message"], "Persuasive AI Study API")
        self.assertEqual(body["version"], "1.0.0")
        self.assertIn("survey1", body["endpoints"])
        self.assertIn("health", body["endpoints"])

    # Endpoint under test: GET /health
    @patch("api.main.get_database")
    def test_health_check_success(self, mock_get_database):
        mock_client = Mock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_get_database.return_value = (mock_client, Mock(), Mock())

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["database"], "connected")
        self.assertIn("timestamp", body)
        mock_client.admin.command.assert_awaited_once_with("ping")

    # Endpoint under test: GET /health
    @patch("api.main.get_database")
    def test_health_check_database_failure_returns_503(self, mock_get_database):
        mock_client = Mock()
        mock_client.admin.command = AsyncMock(side_effect=Exception("db down"))
        mock_get_database.return_value = (mock_client, Mock(), Mock())

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Database connection failed", response.json()["detail"])

    # Endpoint under test: POST /api/v1/survey1
    @patch("api.main.get_database")
    def test_submit_survey1_success(self, mock_get_database):
        mock_collection = Mock()
        mock_collection.insert_one = AsyncMock(
            return_value=type("Result", (), {"inserted_id": "abc123"})()
        )
        mock_get_database.return_value = (Mock(), Mock(), mock_collection)

        response = self.client.post("/api/v1/survey1", json=_valid_survey_payload())

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["participant_id"], "participant-123")
        self.assertEqual(body["survey_id"], "abc123")
        mock_collection.insert_one.assert_awaited_once()

    # Endpoint under test: POST /api/v1/survey1
    def test_submit_survey1_validation_error_for_missing_required_field(self):
        payload = _valid_survey_payload()
        payload.pop("participant_id")

        response = self.client.post("/api/v1/survey1", json=payload)

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
