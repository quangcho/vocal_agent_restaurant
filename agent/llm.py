"""One place for every Claude call, so the model and settings are easy to change."""

import anthropic

MODEL = "claude-opus-5-5"


def create(client: anthropic.Anthropic, *, effort: str = "medium", **params):
    """Send one Messages request and return the response.

    Server-side fallbacks are on: if a request is declined by a safety
    classifier, the API retries it on a fallback model in the same call.
    """
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        output_config={"effort": effort},
        cache_control={"type": "ephemeral"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        **params,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Response cut off by max_tokens.")
    return response


def text_of(response) -> str:
    return "".join(b.text for b in response.content if b.type == "text").strip()
