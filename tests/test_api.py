import json
import sys
import types
import unittest
from datetime import UTC, datetime
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

try:
    import beanie  # noqa: F401
except Exception:
    from pydantic import BaseModel

    beanie_module = types.ModuleType("beanie")

    class _Document(BaseModel):
        id: str | None = None

        @classmethod
        async def find_one(cls, *args, **kwargs):
            return None

        async def insert(self):
            return self

        async def save(self):
            return self

    async def _init_beanie(*args, **kwargs):
        return None

    def _indexed(tp, **kwargs):
        return tp

    beanie_module.Document = _Document
    beanie_module.init_beanie = _init_beanie
    beanie_module.Indexed = _indexed
    sys.modules["beanie"] = beanie_module

from api import main


class _FakeMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
        self.created_at = datetime.utcnow()

    def model_dump(self):
        return {
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }


class _FakeChatDoc:
    def __init__(self, prolific_id: str, condition_key: str = "control"):
        self.prolific_id = prolific_id
        self.condition_key = condition_key
        self.condition_label = "Control"
        self.topic = "quick and easy dishes"
        self.statement = "quick and easy dishes"
        self.system_prompt = "prompt"
        self.messages = [_FakeMessage("assistant", "Hello")]
        self.inflight_until = None
        self.inflight_request_id = None
        self.last_client_message_id = None
        self.last_user_message = None
        self.last_assistant_message = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    async def insert(self):
        return self

    async def save(self):
        return self

    def to_service(self):
        return types.SimpleNamespace(
            prolific_id=self.prolific_id,
            condition_key=self.condition_key,
            condition_label=self.condition_label,
            topic=self.topic,
            statement=self.statement,
            system_prompt=self.system_prompt,
            messages=[m.model_dump() for m in self.messages],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class _FakeSurveyDoc:
    def __init__(self, prolific_id: str):
        self.prolific_id = prolific_id
        self.participant_id = "participant-123"
        self.pre_block = types.SimpleNamespace(
            topic="teams",
            personalization="non_personalized",
            is_control=False,
            responses=types.SimpleNamespace(
                opinion=2,
                opinion_reason="reason",
            ),
        )
        self.id = "abc123"

    def model_dump(self, **_):
        return {"prolific_id": self.prolific_id, "participant_id": self.participant_id}

    async def insert(self):
        return self


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
        self.client = TestClient(main.app)

    @patch("api.main.get_database")
    def test_health_check_success(self, mock_get_database):
        mock_client = Mock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_get_database.return_value = (mock_client, Mock())

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["database"], "connected")

    @patch("api.main.Survey1Document.get_motor_collection", create=True)
    @patch("api.main.Survey1Document.from_request")
    def test_submit_survey1_success(self, mock_from_request, mock_get_collection):
        doc = _FakeSurveyDoc("prolific-abc")
        mock_from_request.return_value = doc

        mock_collection = Mock()
        mock_collection.find_one_and_update = AsyncMock(return_value={
            "participant_id": "participant-123",
            "prolific_id": "prolific-abc",
            "_id": "abc123",
            "created_at": datetime.now(UTC),
        })
        mock_get_collection.return_value = mock_collection

        response = self.client.post("/api/v1/survey1", json=_valid_survey_payload())

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["participant_id"], "participant-123")

    @patch("api.main.ChatSessionDocument.from_service")
    @patch("api.main.ChatSessionDocument.find_one", new_callable=AsyncMock)
    @patch("api.main.Survey1Document.find_one", new_callable=AsyncMock)
    def test_start_chat_reuses_existing_single_session(
        self, mock_survey_find_one, mock_chat_find_one, mock_from_service
    ):
        created_doc = _FakeChatDoc("prolific-abc", "teams_non_personalized")
        created_doc.insert = AsyncMock(return_value=created_doc)
        mock_from_service.return_value = created_doc

        mock_survey_find_one.return_value = _FakeSurveyDoc("prolific-abc")
        mock_chat_find_one.side_effect = [None, created_doc]

        first = self.client.get("/api/v1/chat/start?prolific_id=prolific-abc")
        second = self.client.get("/api/v1/chat/start?prolific_id=prolific-abc")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["prolific_id"], "prolific-abc")
        self.assertEqual(second.json()["prolific_id"], "prolific-abc")

    @patch("api.main._release_inflight", new_callable=AsyncMock)
    @patch("api.main._acquire_inflight", new_callable=AsyncMock)
    @patch("api.main.append_and_generate", new_callable=AsyncMock)
    @patch("api.main.ChatSessionDocument.find_one", new_callable=AsyncMock)
    def test_send_message_returns_reply_and_updates_session(
        self,
        mock_find_one,
        mock_append_and_generate,
        mock_acquire_inflight,
        _mock_release_inflight,
    ):
        doc = _FakeChatDoc("prolific-abc", "teams_non_personalized")
        doc.save = AsyncMock(return_value=doc)
        mock_find_one.side_effect = [doc, doc]
        mock_acquire_inflight.return_value = True

        updated = types.SimpleNamespace(
            prolific_id="prolific-abc",
            condition_key="teams_non_personalized",
            condition_label="MS Teams (Non-personalized)",
            topic="MS Teams",
            statement="MS Teams is the most effective collaboration app on the market",
            system_prompt="prompt",
            messages=[
                {"role": "assistant", "content": "Hello", "created_at": datetime.utcnow()},
                {"role": "user", "content": "hello", "created_at": datetime.utcnow()},
                {"role": "assistant", "content": "assistant reply", "created_at": datetime.utcnow()},
            ],
            updated_at=datetime.utcnow(),
        )
        mock_append_and_generate.return_value = updated
        response = self.client.post(
            "/api/v1/chat/send",
            json={
                "prolific_id": "prolific-abc",
                "message": "hello",
                "client_message_id": "msg-1",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["reply"], "assistant reply")
        self.assertEqual(body["user_message"]["role"], "user")
        self.assertEqual(body["assistant_message"]["role"], "assistant")

    @patch("api.main.ChatSessionDocument.from_service")
    @patch("api.main.ChatSessionDocument.find_one", new_callable=AsyncMock)
    def test_reset_clears_messages(self, mock_find_one, mock_from_service):
        doc = _FakeChatDoc("prolific-abc", "control")
        doc.save = AsyncMock(return_value=doc)
        mock_find_one.return_value = doc
        mock_from_service.return_value = doc

        response = self.client.post("/api/v1/chat/reset/prolific-abc")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["prolific_id"], "prolific-abc")
        self.assertEqual(len(body["messages"]), 1)

    @patch("api.main._release_inflight", new_callable=AsyncMock)
    @patch("api.main._acquire_inflight", new_callable=AsyncMock)
    @patch("api.main.append_and_generate", new_callable=AsyncMock)
    @patch("api.main.ChatSessionDocument.find_one", new_callable=AsyncMock)
    def test_send_message_with_same_client_message_id_is_idempotent(
        self,
        mock_find_one,
        mock_append_and_generate,
        mock_acquire_inflight,
        _mock_release_inflight,
    ):
        doc = _FakeChatDoc("prolific-abc", "control")
        doc.last_client_message_id = "msg-1"
        doc.last_user_message = _FakeMessage("user", "hello")
        doc.last_assistant_message = _FakeMessage("assistant", "assistant reply")
        mock_find_one.return_value = doc
        mock_acquire_inflight.return_value = True

        response = self.client.post(
            "/api/v1/chat/send",
            json={
                "prolific_id": "prolific-abc",
                "message": "hello",
                "client_message_id": "msg-1",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["assistant_message"]["content"], "assistant reply")
        mock_append_and_generate.assert_not_awaited()


class TestSSEStream(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def _parse_sse(self, content: bytes) -> list[dict]:
        events = []
        for part in content.decode().split("\n\n"):
            line = part.strip()
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
        return events

    def _make_doc(self, prolific_id="prolific-stream"):
        doc = _FakeChatDoc(prolific_id)
        doc.save = AsyncMock()
        return doc

    @staticmethod
    def _async_gen(*tokens):
        """Returns an async generator function that yields the given tokens."""
        async def _gen(*args, **kwargs):
            for t in tokens:
                yield t
        return _gen

    @patch("api.main._release_inflight", new_callable=AsyncMock)
    @patch("api.main._acquire_inflight", new_callable=AsyncMock)
    @patch("api.main.ChatSessionDocument.find_one", new_callable=AsyncMock)
    def test_chunks_joined_equals_assistant_message_content(
        self, mock_find, mock_acquire, mock_release
    ):
        """Streamed chunks joined must equal assistant_message.content in the done event.

        Concatenating every chunk token must produce the exact same string that
        the done event reports as assistant_message.content — i.e., what the
        client received over the wire matches what is written to the database.
        """
        doc = self._make_doc()
        mock_find.return_value = doc
        mock_acquire.return_value = True

        tokens = ["Hello", ", ", "world", "!"]
        with patch("api.services.llm.stream_chat_reply", self._async_gen(*tokens)):
            resp = self.client.post(
                "/api/v1/chat/stream",
                json={"prolific_id": "prolific-stream", "message": "hi", "client_message_id": "msg-1"},
            )

        self.assertEqual(resp.status_code, 200)
        events = self._parse_sse(resp.content)

        chunks = [e["chunk"] for e in events if "chunk" in e]
        done_events = [e for e in events if e.get("done")]

        self.assertTrue(chunks, "Expected at least one chunk event")
        self.assertEqual(len(done_events), 1)
        self.assertEqual("".join(chunks), "Hello, world!")
        self.assertEqual("".join(chunks), done_events[0]["assistant_message"]["content"])

    @patch("api.main._release_inflight", new_callable=AsyncMock)
    @patch("api.main._acquire_inflight", new_callable=AsyncMock)
    @patch("api.main.ChatSessionDocument.find_one", new_callable=AsyncMock)
    def test_db_persistence_after_stream(self, mock_find, mock_acquire, mock_release):
        """Both user and assistant messages must be persisted to the DB after the stream completes.

        Asserts that after the stream completes:
          - doc.save() was called exactly twice (once to persist the user message
            before streaming begins, once to persist the assistant message after
            the stream finishes)
          - doc.last_assistant_message is populated with the full joined content
          - the assistant ChatMessage is appended to doc.messages as the last
            entry, with role "assistant" and the correct content
        """
        doc = self._make_doc()
        mock_find.return_value = doc
        mock_acquire.return_value = True

        tokens = ["Hello", " there"]
        with patch("api.services.llm.stream_chat_reply", self._async_gen(*tokens)):
            resp = self.client.post(
                "/api/v1/chat/stream",
                json={"prolific_id": "prolific-stream", "message": "hi", "client_message_id": "msg-2"},
            )

        self.assertEqual(resp.status_code, 200)
        # save() called twice: once for user msg, once for assistant msg
        self.assertEqual(doc.save.await_count, 2)
        # last_assistant_message populated with joined content
        self.assertIsNotNone(doc.last_assistant_message)
        self.assertEqual(doc.last_assistant_message.content, "Hello there")
        # messages list: 1 initial greeting + user + assistant = 3
        self.assertEqual(len(doc.messages), 3)
        self.assertEqual(doc.messages[-1].content, "Hello there")
        self.assertEqual(doc.messages[-1].role, "assistant")

    @patch("api.main._release_inflight", new_callable=AsyncMock)
    @patch("api.main._acquire_inflight", new_callable=AsyncMock)
    @patch("api.main.ChatSessionDocument.find_one", new_callable=AsyncMock)
    def test_lock_released_after_successful_stream(
        self, mock_find, mock_acquire, mock_release
    ):
        """Inflight lock must be released exactly once after a successful stream.

        Asserts that _release_inflight is awaited exactly once with the correct
        prolific_id and client_message_id after a stream completes successfully,
        confirming the lock is not left held after a normal response.
        """
        doc = self._make_doc()
        mock_find.return_value = doc
        mock_acquire.return_value = True

        with patch("api.services.llm.stream_chat_reply", self._async_gen("response")):
            resp = self.client.post(
                "/api/v1/chat/stream",
                json={"prolific_id": "prolific-stream", "message": "hi", "client_message_id": "msg-3"},
            )

        self.assertEqual(resp.status_code, 200)
        mock_release.assert_awaited_once_with("prolific-stream", "msg-3")

    @patch("api.main._release_inflight", new_callable=AsyncMock)
    @patch("api.main._acquire_inflight", new_callable=AsyncMock)
    @patch("api.main.ChatSessionDocument.find_one", new_callable=AsyncMock)
    def test_lock_released_after_llm_error(self, mock_find, mock_acquire, mock_release):
        """Inflight lock must be released and an error event emitted when the LLM raises.

        Asserts that when stream_chat_reply raises mid-stream, the SSE response
        contains an error event with the exception message, and _release_inflight
        is still awaited exactly once — confirming the finally block in _generate
        runs even on failure and does not leave the lock permanently held.
        """
        doc = self._make_doc()
        mock_find.return_value = doc
        mock_acquire.return_value = True

        async def _error_gen(*args, **kwargs):
            raise RuntimeError("LLM connection failed")
            yield  # makes this an async generator function

        with patch("api.services.llm.stream_chat_reply", _error_gen):
            resp = self.client.post(
                "/api/v1/chat/stream",
                json={"prolific_id": "prolific-stream", "message": "hi", "client_message_id": "msg-4"},
            )

        self.assertEqual(resp.status_code, 200)
        events = self._parse_sse(resp.content)
        error_events = [e for e in events if "error" in e]
        self.assertTrue(error_events, "Expected an error event in the stream")
        self.assertIn("LLM connection failed", error_events[0]["error"])
        mock_release.assert_awaited_once_with("prolific-stream", "msg-4")

    @patch("api.main._release_inflight", new_callable=AsyncMock)
    @patch("api.main._acquire_inflight", new_callable=AsyncMock)
    @patch("api.main.ChatSessionDocument.find_one", new_callable=AsyncMock)
    def test_sse_event_shape(self, mock_find, mock_acquire, mock_release):
        """SSE response must follow the expected event structure and field contract.

        Asserts the structural contract of the SSE stream:
          - Content-Type header is text/event-stream
          - Every chunk event carries a non-empty string value
          - There is exactly one done event
          - The done event is the final event in the stream (no chunks after it)
          - The done event contains user_message and assistant_message with the
            correct roles, a content field, and a created_at timestamp
        """
        doc = self._make_doc()
        mock_find.return_value = doc
        mock_acquire.return_value = True

        tokens = ["token1", " token2", " token3"]
        with patch("api.services.llm.stream_chat_reply", self._async_gen(*tokens)):
            resp = self.client.post(
                "/api/v1/chat/stream",
                json={"prolific_id": "prolific-stream", "message": "hi", "client_message_id": "msg-5"},
            )

        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/event-stream", resp.headers.get("content-type", ""))

        events = self._parse_sse(resp.content)

        # All chunk events carry non-empty strings
        chunk_events = [e for e in events if "chunk" in e]
        self.assertTrue(chunk_events, "Expected chunk events")
        for ev in chunk_events:
            self.assertIsInstance(ev["chunk"], str)
            self.assertGreater(len(ev["chunk"]), 0)

        # Exactly one done event
        done_events = [e for e in events if e.get("done")]
        self.assertEqual(len(done_events), 1)

        # done is the last event
        self.assertEqual(events[-1], done_events[0])

        # done event has required fields with correct roles
        done = done_events[0]
        self.assertIn("user_message", done)
        self.assertIn("assistant_message", done)
        self.assertEqual(done["user_message"]["role"], "user")
        self.assertEqual(done["assistant_message"]["role"], "assistant")
        self.assertIn("content", done["assistant_message"])
        self.assertIn("created_at", done["assistant_message"])

        # no chunk events appear after done
        done_idx = events.index(done)
        trailing_chunks = [e for e in events[done_idx + 1:] if "chunk" in e]
        self.assertEqual(trailing_chunks, [])


if __name__ == "__main__":
    unittest.main()
