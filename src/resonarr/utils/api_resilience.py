import json
import os
import time
from datetime import datetime, timezone

import requests


TRANSIENT_STATUS_CODES = {500, 502, 503, 504}
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 1.0
DEFAULT_TIMEOUT_SECONDS = 20


class ExternalApiError(RuntimeError):
    def __init__(
        self,
        source,
        operation,
        message,
        *,
        status_code=None,
        url=None,
        attempts=None,
        cause=None,
    ):
        super().__init__(message)
        self.source = source
        self.operation = operation
        self.status_code = status_code
        self.url = url
        self.attempts = attempts
        self.cause = cause


def _utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def append_api_error_event(
    *,
    source,
    operation,
    message,
    url=None,
    attempt=None,
    status_code=None,
    exception_type=None,
    context=None,
):
    os.makedirs("logs", exist_ok=True)
    event = {
        "ts": _utc_now_iso(),
        "source": source,
        "operation": operation,
        "message": message,
        "url": url,
        "attempt": attempt,
        "status_code": status_code,
        "exception_type": exception_type,
        "context": context or {},
    }

    with open("logs/api-error-events.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def request_with_retry(
    *,
    source,
    operation,
    request_func,
    url,
    params=None,
    headers=None,
    attempts=DEFAULT_RETRY_ATTEMPTS,
    retry_delay_seconds=DEFAULT_RETRY_DELAY_SECONDS,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    context=None,
):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            response = request_func(
                url,
                params=params,
                headers=headers,
                timeout=timeout_seconds,
            )

            status_code = response.status_code

            if status_code in TRANSIENT_STATUS_CODES:
                message = f"{source} {operation} returned transient status {status_code}"
                append_api_error_event(
                    source=source,
                    operation=operation,
                    message=message,
                    url=url,
                    attempt=attempt,
                    status_code=status_code,
                    exception_type="HTTPStatusRetry",
                    context=context,
                )

                if attempt < attempts:
                    time.sleep(retry_delay_seconds)
                    continue

                raise ExternalApiError(
                    source,
                    operation,
                    message,
                    status_code=status_code,
                    url=url,
                    attempts=attempt,
                )

            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as exc:
            last_error = exc
            status_code = getattr(getattr(exc, "response", None), "status_code", None)

            append_api_error_event(
                source=source,
                operation=operation,
                message=str(exc),
                url=url,
                attempt=attempt,
                status_code=status_code,
                exception_type=type(exc).__name__,
                context=context,
            )

            if attempt < attempts:
                time.sleep(retry_delay_seconds)
                continue

            raise ExternalApiError(
                source,
                operation,
                f"{source} {operation} failed after {attempt} attempts: {exc}",
                status_code=status_code,
                url=url,
                attempts=attempt,
                cause=exc,
            ) from exc

    raise ExternalApiError(
        source,
        operation,
        f"{source} {operation} failed after {attempts} attempts",
        url=url,
        attempts=attempts,
        cause=last_error,
    )


def request_json_with_retry(
    *,
    source,
    operation,
    request_func,
    url,
    params=None,
    headers=None,
    attempts=DEFAULT_RETRY_ATTEMPTS,
    retry_delay_seconds=DEFAULT_RETRY_DELAY_SECONDS,
    timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    context=None,
):
    response = request_with_retry(
        source=source,
        operation=operation,
        request_func=request_func,
        url=url,
        params=params,
        headers=headers,
        attempts=attempts,
        retry_delay_seconds=retry_delay_seconds,
        timeout_seconds=timeout_seconds,
        context=context,
    )
    return response.json()
