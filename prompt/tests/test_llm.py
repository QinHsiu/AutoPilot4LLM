import json
import urllib.error

import pytest

from prompt.config import Config
from prompt.llm import LlmError, OpenAiCompatibleClient

CONFIG = Config(base_url="http://example.invalid/v1", model="demo", timeout_s=3)


class Response:
    def __init__(self, body: bytes):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


def test_complete_posts_three_fields_and_retries_once():
    calls = []

    def opener(request, timeout):
        calls.append((request, timeout))
        if len(calls) == 1:
            raise urllib.error.URLError("down")
        return Response(json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode())

    client = OpenAiCompatibleClient(CONFIG, "secret", opener)
    assert client.complete([{"role": "user", "content": "hi"}], 0) == "ok"
    request, timeout = calls[1]
    assert timeout == 3
    assert request.full_url == "http://example.invalid/v1/chat/completions"
    assert request.get_header("Authorization") == "Bearer secret"
    assert json.loads(request.data.decode()) == {
        "model": "demo",
        "messages": [{"role": "user", "content": "hi"}],
        "temperature": 0,
    }


def test_second_failure_and_non_string_content_raise():
    def opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 400, "bad", {}, None)

    client = OpenAiCompatibleClient(CONFIG, "secret", opener)
    with pytest.raises(LlmError):
        client.complete([{"role": "user", "content": "hi"}], 0)

    def bad_body(request, timeout):
        return Response(json.dumps({"choices": [{"message": {"content": ["x"]}}]}).encode())

    with pytest.raises(LlmError, match="missing content"):
        OpenAiCompatibleClient(CONFIG, "secret", bad_body).complete([], 0)
