# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import io
import json
from urllib.error import HTTPError, URLError

import pytest

from absencecritic.adapters.llm.openai_compat import LLMError, OpenAICompat


def _ok_body(text: str = "hello") -> bytes:
    return json.dumps(
        {"choices": [{"message": {"content": text}}]}
    ).encode("utf-8")


class _Resp:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _http_error(code: int, body: bytes = b"nope", headers: dict | None = None) -> HTTPError:
    hdrs = headers or {}
    return HTTPError(
        "https://example.test/v1/chat/completions",
        code,
        "err",
        hdrs,
        io.BytesIO(body),
    )


def test_retries_429_then_succeeds():
    calls = {"n": 0}
    sleeps: list[float] = []

    def urlopen(req, timeout=None):
        del req, timeout
        calls["n"] += 1
        if calls["n"] == 1:
            raise _http_error(429, b"slow down", {"Retry-After": "0"})
        return _Resp(_ok_body("ok"))

    llm = OpenAICompat(
        api_key="k", retries=3, timeout=5, urlopen=urlopen, sleeper=sleeps.append
    )
    assert llm.generate(query="hi") == "ok"
    assert calls["n"] == 2
    assert sleeps == [0.0]


def test_repeated_500_raises_after_retries():
    calls = {"n": 0}

    def urlopen(req, timeout=None):
        del req, timeout
        calls["n"] += 1
        raise _http_error(500, b"down")

    llm = OpenAICompat(
        api_key="k", retries=2, timeout=5, urlopen=urlopen, sleeper=lambda _s: None
    )
    with pytest.raises(LLMError) as caught:
        llm.generate(query="hi")
    assert caught.value.status == 500
    assert "down" in caught.value.body
    assert calls["n"] == 3


def test_401_fails_immediately():
    calls = {"n": 0}

    def urlopen(req, timeout=None):
        del req, timeout
        calls["n"] += 1
        raise _http_error(401, b"nope")

    llm = OpenAICompat(
        api_key="k", retries=5, timeout=5, urlopen=urlopen, sleeper=lambda _s: None
    )
    with pytest.raises(LLMError) as caught:
        llm.generate(query="hi")
    assert caught.value.status == 401
    assert calls["n"] == 1


def test_malformed_body_is_adapter_error_not_keyerror():
    def urlopen(req, timeout=None):
        del req, timeout
        return _Resp(b'{"choices": []}')

    llm = OpenAICompat(api_key="k", retries=0, urlopen=urlopen, sleeper=lambda _s: None)
    with pytest.raises(LLMError) as caught:
        llm.generate(query="hi")
    assert caught.value.status is None
    assert "choices[0].message.content" in str(caught.value)


def test_connection_error_retries():
    calls = {"n": 0}

    def urlopen(req, timeout=None):
        del req, timeout
        calls["n"] += 1
        if calls["n"] < 3:
            raise URLError("reset")
        return _Resp(_ok_body("recovered"))

    llm = OpenAICompat(
        api_key="k", retries=3, urlopen=urlopen, sleeper=lambda _s: None
    )
    assert llm.generate(query="hi") == "recovered"
    assert calls["n"] == 3
