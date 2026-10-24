import json
import urllib.error
import urllib.request

from prompt.config import Config


class LlmError(Exception):
    pass


class OpenAiCompatibleClient:
    def __init__(self, config: Config, api_key: str, opener=None):
        self.config = config
        self.api_key = api_key
        self.opener = opener or urllib.request.urlopen

    def complete(self, messages: list[dict], temperature: float) -> str:
        last = LlmError("missing content")
        for _ in range(2):
            try:
                return self._once(messages, temperature)
            except LlmError as exc:
                last = exc
        raise last

    def _once(self, messages: list[dict], temperature: float) -> str:
        body = json.dumps(
            {"model": self.config.model, "messages": messages, "temperature": temperature},
            ensure_ascii=False,
        ).encode()
        request = urllib.request.Request(
            self.config.base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.config.timeout_s) as response:
                payload = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            raise LlmError(str(exc.code)) from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LlmError(str(exc)) from exc
        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmError("missing content") from exc
        if not isinstance(content, str):
            raise LlmError("missing content")
        return content
