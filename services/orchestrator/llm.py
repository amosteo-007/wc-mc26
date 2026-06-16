"""Premium-model chat helper with cross-model parameter compatibility.

The orchestrator's premium calls (planner, QC, synthesis, world-spec) all use
JSON mode. gpt-5-family models (gpt-5, gpt-5-nano, o1, o3, …) reject
`max_tokens` (require `max_completion_tokens`), only accept the default
temperature, and — being reasoning models — burn completion budget on internal
reasoning before emitting text, so a tight cap returns an empty string. This
helper picks model-appropriate params, gives gpt-5 generous headroom plus
`reasoning_effort: "minimal"` for latency, and retries once on a param error.

Failures raise (the caller logs/falls back) rather than being masked here.
"""
import logging

logger = logging.getLogger("orchestrator.llm")


def _is_gpt5_family(model: str) -> bool:
    m = (model or "").lower()
    return m.startswith("gpt-5") or m.startswith("o1") or m.startswith("o3")


def chat_json(client, model: str, messages, max_tokens: int = 600,
              temperature: float = 0.3):
    """Call chat.completions in JSON mode with model-appropriate params.

    Returns the raw message content string (caller parses JSON), or raises on a
    genuine API failure so the caller's except can fall back.
    """
    common = {"model": model, "messages": messages,
              "response_format": {"type": "json_object"}}

    if _is_gpt5_family(model):
        budget = max(max_tokens, 2000)  # reasoning tokens + JSON output
        # "low" is the lowest reasoning_effort supported across the gpt-5 family
        # (gpt-5-nano also accepts "minimal", but gpt-5.x-mini does not).
        params = {**common, "max_completion_tokens": budget,
                  "extra_body": {"reasoning_effort": "low"}}
    else:
        params = {**common, "max_tokens": max_tokens, "temperature": temperature}

    try:
        resp = client.chat.completions.create(**params)
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "reasoning_effort" in msg:
            # Model doesn't accept the chosen effort — drop it and retry as-is.
            params.pop("extra_body", None)
            logger.warning("premium LLM dropping reasoning_effort for model=%s (%s)", model, exc)
            resp = client.chat.completions.create(**params)
        elif "max_tokens" in msg or "max_completion_tokens" in msg or "temperature" in msg:
            if _is_gpt5_family(model):
                alt = {**common, "max_tokens": max_tokens, "temperature": temperature}
            else:
                alt = {**common, "max_completion_tokens": max(max_tokens, 2000)}
            logger.warning("premium LLM param retry for model=%s (%s)", model, exc)
            resp = client.chat.completions.create(**alt)
        else:
            raise

    return resp.choices[0].message.content
