from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import serpapi

from toppertrail.serp.base import (
    SerpError,
    SerpResult,
    canonical_params,
    params_hash,
    redact,
    scrub,
    trim,
)
from toppertrail.serp.budget import Budget, append_spend

_RETRY_STATUS = {429, 500, 502, 503, -1}
_NO_RESULTS = "hasn't returned any results"


class LiveSerpClient:
    def __init__(self, api_key: str, budget: Budget, spend_log: Path | None = None, sdk=None,
                 sleep: Callable[[float], None] = time.sleep, max_retries: int = 3,
                 timeout: int = 60) -> None:
        if not api_key:
            raise SerpError("SERPAPI_API_KEY is not set")
        self._key = api_key
        self._sdk = sdk or serpapi.Client(api_key=api_key, timeout=timeout)
        self.budget = budget
        self.spend_log = spend_log
        self._sleep = sleep
        self.max_retries = max_retries

    @staticmethod
    def _wait(err: Exception, attempt: int) -> float:
        try:
            return min(float(err.response.headers.get("Retry-After")), 30.0)
        except (AttributeError, TypeError, ValueError):
            return min(2.0**attempt, 30.0)

    def _result(self, engine: str, params: dict, data: dict) -> SerpResult:
        clean = trim(engine, scrub(data, self._key))
        return SerpResult(engine, canonical_params(engine, params), clean, "live")

    def search(self, engine: str, params: dict) -> SerpResult:
        query = {"engine": engine, **params}
        for attempt in range(self.max_retries + 1):
            self.budget.ensure_available()
            try:
                raw = self._sdk.search(dict(query))
            except serpapi.TimeoutError:
                if attempt < self.max_retries:
                    self._sleep(self._wait(Exception(), attempt))
                    continue
                raise SerpError(f"SerpApi {engine} timed out") from None
            except serpapi.HTTPError as err:
                status = getattr(err, "status_code", None)
                message = getattr(err, "error", None)
                if message and _NO_RESULTS in message.lower():
                    return self._result(engine, params, {"error": message})
                if status in _RETRY_STATUS and attempt < self.max_retries:
                    self._sleep(self._wait(err, attempt))
                    continue
                detail = redact(str(message or err), self._key)
                raise SerpError(
                    f"SerpApi {engine} failed (HTTP {status}): {detail}", status=status
                ) from None
            data = raw.as_dict() if hasattr(raw, "as_dict") else dict(raw)
            result = self._result(engine, params, data)
            if not result.data.get("error"):
                self.budget.charge()
                if self.spend_log is not None:
                    append_spend(
                        self.spend_log, engine, params_hash(engine, params), result.search_id
                    )
            return result
        raise SerpError(f"SerpApi {engine} failed after retries")


def account_searches_left(api_key: str, sdk=None) -> int:
    client = sdk or serpapi.Client(api_key=api_key)
    try:
        data = client.account()
    except serpapi.HTTPError as err:
        raise SerpError(redact(f"account check failed: {err}", api_key)) from None
    data = data.as_dict() if hasattr(data, "as_dict") else dict(data)
    return int(data.get("total_searches_left", data.get("plan_searches_left", 0)))
