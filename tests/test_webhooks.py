import json
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ToolCallWebhookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_vapi_tool_call_returns_result_with_call_id(self) -> None:
        response = self.client.post(
            "/voice/webhook/tool-call",
            json={
                "message": {
                    "type": "tool-calls",
                    "toolCallList": [
                        {
                            "id": "call-123",
                            "type": "function",
                            "function": {
                                "name": "validate_field",
                                "arguments": {
                                    "field_name": "phone_number",
                                    "field_value": "555-123-4567",
                                },
                            },
                        }
                    ],
                }
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()["results"][0]
        self.assertEqual(result["name"], "validate_field")
        self.assertEqual(result["toolCallId"], "call-123")
        self.assertEqual(
            json.loads(result["result"]),
            {"valid": True, "normalized_value": "5551234567"},
        )

    def test_vapi_tool_call_supports_json_string_arguments(self) -> None:
        response = self.client.post(
            "/voice/webhook/tool-call",
            json={
                "message": {
                    "type": "tool-calls",
                    "toolCallList": [
                        {
                            "id": "call-456",
                            "type": "function",
                            "function": {
                                "name": "validate_field",
                                "arguments": '{"field_name":"phone_number","field_value":"5551234567"}',
                            },
                        }
                    ],
                }
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.json()["results"][0]["result"]),
            {"valid": True, "normalized_value": "5551234567"},
        )

    def test_vapi_tool_call_returns_result_for_each_call(self) -> None:
        response = self.client.post(
            "/voice/webhook/tool-call",
            json={
                "message": {
                    "type": "tool-calls",
                    "toolCallList": [
                        {
                            "id": "call-1",
                            "type": "function",
                            "function": {
                                "name": "validate_field",
                                "arguments": {
                                    "field_name": "phone_number",
                                    "field_value": "5551234567",
                                },
                            },
                        },
                        {
                            "id": "call-2",
                            "type": "function",
                            "function": {
                                "name": "validate_field",
                                "arguments": {
                                    "field_name": "zip_code",
                                    "field_value": "10001",
                                },
                            },
                        },
                    ],
                }
            },
        )

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual([result["toolCallId"] for result in results], ["call-1", "call-2"])
        self.assertEqual(
            json.loads(results[0]["result"]),
            {"valid": True, "normalized_value": "5551234567"},
        )
        self.assertTrue(json.loads(results[1]["result"])["valid"])

    def test_legacy_local_tool_call_format_remains_supported(self) -> None:
        response = self.client.post(
            "/voice/webhook/tool-call",
            json={
                "tool_name": "validate_field",
                "field_name": "phone_number",
                "field_value": "5551234567",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"valid": True, "normalized_value": "5551234567"},
        )

    def test_missing_vapi_tool_call_id_is_rejected(self) -> None:
        response = self.client.post(
            "/voice/webhook/tool-call",
            json={
                "message": {
                    "type": "tool-calls",
                    "toolCallList": [
                        {
                            "type": "function",
                            "function": {
                                "name": "validate_field",
                                "arguments": {
                                    "field_name": "phone_number",
                                    "field_value": "5551234567",
                                },
                            },
                        }
                    ],
                }
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("must include an id", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
