"""
retry_helper.py
~~~~~~~~~~~~~~~
Shared retry + exponential back-off utility for all LangGraph nodes.

Usage
-----
    from utilities.retry_helper import (
        llm_call_with_retry,
        NodeExecutionError,
        make_error_event,
        MAX_RETRY_COUNT,
    )

    async def my_node(state):
        async def call():
            return await llm.ainvoke(messages)

        try:
            result = await llm_call_with_retry("my_node", call)
        except NodeExecutionError as e:
            # push e to node_errors, set needs_user_input, etc.
            ...
"""

import asyncio
import datetime
import logging
from enum import Enum
from typing import Any, Callable, Coroutine, TypeVar

logger = logging.getLogger(__name__)

#  Constants 

MAX_RETRY_COUNT = 3          # additional attempts after the first failure
PRE_CALL_DELAY_SECONDS = 5   # sleep before every LLM call (free-API rate guard)
BACKOFF_BASE_SECONDS = 2     # base for exponential back-off
BACKOFF_CAP_SECONDS = 60     # upper bound for any single back-off sleep


#  Error Classification 

class ErrorType(str, Enum):
    TIMEOUT    = "timeout"
    RATE_LIMIT = "rate_limit"
    OTHER      = "other"


def classify_error(e: Exception) -> ErrorType:
    """Map any exception to one of the known :class:`ErrorType` values."""
    msg = str(e).lower()
    if (
        isinstance(e, (asyncio.TimeoutError, TimeoutError))
        or "timeout" in msg
        or "timed out" in msg
    ):
        return ErrorType.TIMEOUT
    if (
        "429" in msg
        or "rate limit" in msg
        or "rate_limit" in msg
        or "too many requests" in msg
    ):
        return ErrorType.RATE_LIMIT
    return ErrorType.OTHER


# Typed Exception

class NodeExecutionError(Exception):
    """
    Raised by :func:`llm_call_with_retry` when all retry attempts are
    exhausted.

    Attributes
    ----------
    node_name  : str        — the node that failed
    cause      : Exception  — the underlying exception from the last attempt
    error_type : ErrorType  — classified error category
    """

    def __init__(self, node_name: str, cause: Exception, error_type: ErrorType) -> None:
        self.node_name = node_name
        self.cause = cause
        self.error_type = error_type
        super().__init__(
            f"[{node_name}] {error_type.value} error after exhausting "
            f"{MAX_RETRY_COUNT + 1} attempts: {cause}"
        )


# Error Event Builder

def make_error_event(
    node_name: str,
    cause: Exception,
    error_type: ErrorType,
    attempt: int,
) -> dict:
    """
    Build a structured error-event dict for appending to
    ``AgentState.node_errors``.

    Returns
    -------
    dict with keys: node, error_type, message, attempt, timestamp
    """
    return {
        "node":       node_name,
        "error_type": error_type.value if error_type else "unknown",
        "message":    str(cause),
        "attempt":    attempt + 1,
        "timestamp":  datetime.datetime.utcnow().isoformat(),
    }


# Core Retry Helper 

T = TypeVar("T")


async def llm_call_with_retry(
    node_name: str,
    call: Callable[[], Coroutine[Any, Any, T]],
    max_retries: int = MAX_RETRY_COUNT,
    on_retry: Callable[[Exception, ErrorType, int], None] | None = None,
    pre_call_delay_seconds: float = PRE_CALL_DELAY_SECONDS,
) -> T:
    """
    Execute an async callable with retry and exponential back-off.

    Parameters
    ----------
    node_name : str
        Human-readable name used in logs and error events.
    call : async callable
        Zero-argument coroutine that performs the LLM or tool call.
    max_retries : int
        Number of *additional* attempts after the first failure.
        Total attempts = ``max_retries + 1``.  Default: :data:`MAX_RETRY_COUNT`.
    on_retry : optional callable(error, error_type, attempt)
        Called *before* the back-off sleep after each failure so the caller
        can enrich its prompt / context for the next attempt.
    pre_call_delay_seconds : float
        Seconds to sleep before every attempt.  Use the default
        (:data:`PRE_CALL_DELAY_SECONDS`) for LLM calls and ``0`` for tool
        calls that do not need rate-limit headroom.

    Back-off rules
    --------------
    * **TIMEOUT / RATE_LIMIT**: exponential — ``BACKOFF_BASE * 2^attempt``
      seconds, capped at :data:`BACKOFF_CAP_SECONDS`.
    * **Other errors**: flat 2 s delay.

    Raises
    ------
    NodeExecutionError
        When all ``max_retries + 1`` attempts fail.
    """
    last_error: Exception = RuntimeError("No attempts were made")
    last_error_type: ErrorType = ErrorType.OTHER

    for attempt in range(max_retries + 1):
        try:
            # Pre-call delay (rate-limit guard for free APIs)
            if pre_call_delay_seconds > 0:
                logger.info(
                    "[%s] Waiting %.1fs before call (attempt %s/%s)",
                    node_name,
                    pre_call_delay_seconds,
                    attempt + 1,
                    max_retries + 1,
                )
                await asyncio.sleep(pre_call_delay_seconds)

            logger.info(
                "[%s] Making call (attempt %s/%s)",
                node_name,
                attempt + 1,
                max_retries + 1,
            )
            result = await call()
            logger.info("[%s] Call succeeded on attempt %s", node_name, attempt + 1)
            return result

        except Exception as e:
            error_type = classify_error(e)
            last_error = e
            last_error_type = error_type

            logger.error(
                "[%s] Call failed (attempt %s/%s) [%s]: %s",
                node_name,
                attempt + 1,
                max_retries + 1,
                error_type.value,
                e,
                exc_info=True,
            )

            if attempt == max_retries:
                logger.error(
                    "[%s] All %s attempt(s) exhausted — giving up.",
                    node_name,
                    max_retries + 1,
                )
                break

            # Notify caller so it can update its prompt / context
            if on_retry is not None:
                try:
                    on_retry(e, error_type, attempt)
                except Exception as cb_err:
                    logger.warning(
                        "[%s] on_retry callback raised: %s", node_name, cb_err
                    )

            # Back-off before next attempt
            if error_type in (ErrorType.TIMEOUT, ErrorType.RATE_LIMIT):
                backoff = min(
                    BACKOFF_BASE_SECONDS * (2 ** attempt),
                    BACKOFF_CAP_SECONDS,
                )
                logger.warning(
                    "[%s] %s detected — exponential back-off: sleeping %ss",
                    node_name,
                    error_type.value,
                    backoff,
                )
                await asyncio.sleep(backoff)
            else:
                logger.warning(
                    "[%s] Non-transient error — retrying after 2s", node_name
                )
                await asyncio.sleep(2)

    raise NodeExecutionError(node_name, last_error, last_error_type)
