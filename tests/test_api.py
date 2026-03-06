import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

try:
    import motor.motor_asyncio  # noqa: F401
except Exception:
    motor_module = types.ModuleType("motor")
    motor_asyncio_module = types.ModuleType("motor.motor_asyncio")
    motor_asyncio_module.AsyncIOMotorClient = object
    motor_module.motor_asyncio = motor_asyncio_module
    sys.modules["motor"] = motor_module
    sys.modules["motor.motor_asyncio"] = motor_asyncio_module

from api.main import app
from api.services import condition_chat


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
        condition_chat._sessions.clear()
        self.client = TestClient(app)

    # Endpoint under test: GET /
    def test_root_serves_frontend_html(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers.get("content-type", ""))
        self.assertIn("Condition Chat Demo", response.text)

    # Endpoint under test: GET /api/v1/chat/conditions
    def test_chat_conditions_returns_seven_options(self):
        response = self.client.get("/api/v1/chat/conditions")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["conditions"]), 7)
        keys = {item["key"] for item in body["conditions"]}
        self.assertIn("teams_personalized", keys)
        self.assertIn("control", keys)

    # Endpoint under test: POST /api/v1/chat/initialize
    def test_initialize_personalized_requires_argument(self):
        payload = {
            "participant_id": "participant-123",
            "condition_key": "teams_personalized",
            "user_answer": 2,
        }

        response = self.client.post("/api/v1/chat/initialize", json=payload)

        self.assertEqual(response.status_code, 422)
        self.assertIn("argument is required", response.json()["detail"])

    # Endpoint under test: POST /api/v1/chat/initialize
    def test_initialize_control_creates_greeting_message(self):
        payload = {
            "participant_id": "participant-123",
            "condition_key": "control",
        }

        response = self.client.post("/api/v1/chat/initialize", json=payload)

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["condition_key"], "control")
        self.assertGreaterEqual(len(body["messages"]), 1)
        self.assertIn("quick and easy dishes", body["messages"][0]["content"])

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

    # Endpoint under test: POST /api/v1/chat/send
    @patch("api.services.condition_chat.generate_chat_reply", new_callable=AsyncMock)
    def test_send_message_returns_reply(self, mock_generate_chat_reply):
        mock_generate_chat_reply.return_value = "assistant reply"

        init_payload = {
            "participant_id": "participant-123",
            "condition_key": "teams_non_personalized",
            "user_answer": 1,
        }
        self.client.post("/api/v1/chat/initialize", json=init_payload)

        response = self.client.post(
            "/api/v1/chat/send",
            json={
                "participant_id": "participant-123",
                "condition_key": "teams_non_personalized",
                "message": "hello",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["reply"], "assistant reply")
        self.assertGreaterEqual(len(body["messages"]), 3)

    # Endpoint under test: POST /api/v1/chat/reset/{participant_id}/{condition_key}
    @patch("api.services.condition_chat.generate_chat_reply", new_callable=AsyncMock)
    def test_reset_clears_only_given_condition(self, mock_generate_chat_reply):
        mock_generate_chat_reply.return_value = "assistant reply"

        self.client.post(
            "/api/v1/chat/initialize",
            json={
                "participant_id": "participant-123",
                "condition_key": "teams_non_personalized",
                "user_answer": 2,
            },
        )
        self.client.post(
            "/api/v1/chat/initialize",
            json={
                "participant_id": "participant-123",
                "condition_key": "control",
            },
        )

        self.client.post(
            "/api/v1/chat/send",
            json={
                "participant_id": "participant-123",
                "condition_key": "teams_non_personalized",
                "message": "message 1",
            },
        )

        reset_response = self.client.post(
            "/api/v1/chat/reset/participant-123/teams_non_personalized"
        )
        self.assertEqual(reset_response.status_code, 200)
        self.assertEqual(len(reset_response.json()["messages"]), 1)

        control_history = self.client.get(
            "/api/v1/chat/history/participant-123/control"
        )
        self.assertEqual(control_history.status_code, 200)
        self.assertEqual(control_history.json()["condition_key"], "control")
        self.assertGreaterEqual(len(control_history.json()["messages"]), 1)


if __name__ == "__main__":
    unittest.main()
