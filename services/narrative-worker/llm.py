"""Cheap-model chat helper with cross-model parameter compatibility.

gpt-5-family models (gpt-5, gpt-5-nano, …) reject `max_tokens` (they require
`max_completion_tokens`) and only accept the default temperature. Older models
(gpt-4o, gpt-4o-mini) accept `max_tokens` and custom temperature. This helper
picks the right params per model and, on a parameter error, retries with the
alternate set — so a model swap can't silently knock every call into the
template fallback.

Failures are logged (not silently swallowed) so a misconfigured key/model is
visible instead of masquerading as "template mode".
"""
import logging

logger = logging.getLogger("narrative.llm")


def _is_gpt5_family(model: str) -> bool:
    m = (model or "").lower()
    return m.startswith("gpt-5") or m.startswith("o1") or m.startswith("o3")


def chat(client, model: str, messages, max_tokens: int = 256,
         temperature: float = 0.9, **extra):
    """Call chat.completions with model-appropriate params.

    Returns the message content string, or raises on a genuine API failure
    (auth, rate limit, network) so the caller's except can log it.
    """
    if _is_gpt5_family(model):
        # gpt-5 family: max_completion_tokens, default temperature only. These
        # are reasoning models that spend completion budget on internal
        # reasoning tokens *before* emitting any visible text, so a tight cap
        # (e.g. 120) can finish with reason=length and an empty string. Give
        # them generous headroom so real output survives the reasoning pass.
        budget = max(max_tokens, 2000)
        params = {"model": model, "messages": messages,
                  "max_completion_tokens": budget, **extra}
        # Short transfer posts don't need deep reasoning; low effort cuts
        # per-call latency massively (reasoning tokens dominate otherwise).
        # "low" is supported across the gpt-5 family; passed via extra_body so it
        # works on SDK versions predating the typed kwarg.
        eb = params.get("extra_body") or {}
        eb.setdefault("reasoning_effort", "low")
        params["extra_body"] = eb
    else:
        params = {"model": model, "messages": messages,
                  "max_tokens": max_tokens, "temperature": temperature, **extra}

    try:
        resp = client.chat.completions.create(**params)
    except Exception as exc:  # noqa: BLE001
        # If the param set was wrong for this model, retry once before giving up
        # — keeps us resilient to future model swaps.
        msg = str(exc).lower()
        if "reasoning_effort" in msg:
            params.pop("extra_body", None)
            logger.warning("LLM dropping reasoning_effort for model=%s (%s)", model, exc)
            resp = client.chat.completions.create(**params)
        elif "max_tokens" in msg or "max_completion_tokens" in msg or "temperature" in msg:
            alt = {"model": model, "messages": messages, **extra}
            if _is_gpt5_family(model):
                alt["max_completion_tokens"] = max(max_tokens, 2000)
            else:
                alt["max_tokens"] = max_tokens
                alt["temperature"] = temperature
            logger.warning("LLM param retry for model=%s (%s)", model, exc)
            resp = client.chat.completions.create(**alt)
        else:
            raise

    return resp.choices[0].message.content
