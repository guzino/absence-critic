# Copyright 2026 Guzino (https://github.com/guzino)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request

from absencecritic.prompts import (
    CRITIC_SYSTEM,
    DRAFT_SYSTEM,
    REVISE_SYSTEM,
    critic_user_message,
    revise_user_message,
)

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_NO_RETRY_STATUS = frozenset({400, 401, 403})


class LLMError(RuntimeError):
    """Adapter-level live-provider failure. Ports and WaldLoop stay unchanged."""

    def __init__(
        self, message: str, *, status: int | None = None, body: str = ""
    ) -> None:
        clipped = body[:500]
        extra = f" status={status}" if status is not None else ""
        if clipped:
            extra += f" body={clipped}"
        super().__init__(message + extra)
        self.status = status
        self.body = clipped


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    return float(raw)


def _retry_after_seconds(exc: urllib.error.HTTPError, attempt: int) -> float:
    header = ""
    if exc.headers:
        header = str(exc.headers.get("Retry-After") or "")
    if header.strip().isdigit():
        return min(float(header), 30.0)
    return min(0.5 * (2**attempt), 8.0)


class OpenAICompat:
    """Chat Completions transport for GeneratorPort and CriticPort."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        *,
        timeout: float | None = None,
        retries: int | None = None,
        urlopen=None,
        sleeper=None,
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = (
            base_url
            or os.environ.get("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.model = model or os.environ.get("ABSENCECRITIC_MODEL") or "gpt-4o-mini"
        self.timeout = (
            timeout
            if timeout is not None
            else _env_float("ABSENCECRITIC_HTTP_TIMEOUT", 120.0)
        )
        self.retries = (
            retries
            if retries is not None
            else max(0, _env_int("ABSENCECRITIC_HTTP_RETRIES", 3))
        )
        self._urlopen = urlopen or urllib.request.urlopen
        self._sleep = sleeper or time.sleep
        if not self.api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Tests and eval default to --provider fixture."
            )

    def generate(self, *, query: str) -> str:
        return self._chat(DRAFT_SYSTEM, query, temperature=0.4, json_object=False)

    def critique(self, *, query: str, draft: str, store_hits: str) -> str:
        return self._chat(
            CRITIC_SYSTEM,
            critic_user_message(query, draft, store_hits),
            temperature=0.2,
            json_object=True,
        )

    def revise(self, *, query: str, draft: str, critique_json: str) -> str:
        return self._chat(
            REVISE_SYSTEM,
            revise_user_message(query, draft, critique_json),
            temperature=0.4,
            json_object=False,
        )

    def _chat(
        self, system: str, user: str, *, temperature: float, json_object: bool
    ) -> str:
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if json_object:
            payload["response_format"] = {"type": "json_object"}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        last_error: LLMError | None = None
        attempts = self.retries + 1
        for attempt in range(attempts):
            try:
                with self._urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise LLMError(
                        "OpenAI-compatible response was not JSON", body=raw
                    ) from exc
                try:
                    content = body["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise LLMError(
                        "OpenAI-compatible response missing choices[0].message.content",
                        body=raw,
                    ) from exc
                if not isinstance(content, str):
                    raise LLMError(
                        "OpenAI-compatible response content is not a string",
                        body=raw,
                    )
                return content
            except LLMError:
                raise
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                last_error = LLMError(
                    "OpenAI-compatible request failed",
                    status=exc.code,
                    body=detail,
                )
                if exc.code in _NO_RETRY_STATUS or exc.code not in _RETRY_STATUS:
                    raise last_error from exc
                if attempt + 1 >= attempts:
                    raise last_error from exc
                self._sleep(_retry_after_seconds(exc, attempt))
            except (
                urllib.error.URLError,
                TimeoutError,
                socket.timeout,
                ConnectionError,
                OSError,
            ) as exc:
                last_error = LLMError(
                    "OpenAI-compatible request failed",
                    body=str(exc),
                )
                if attempt + 1 >= attempts:
                    raise last_error from exc
                self._sleep(min(0.5 * (2**attempt), 8.0))
        assert last_error is not None
        raise last_error
