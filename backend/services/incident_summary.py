# Utility for parsing incident summary JSON responses from LLMs

from __future__ import annotations

import json
import re
from typing import Callable, List, Literal

from pydantic import BaseModel, Field, ValidationError

# ---------------------------------------------------------------------------
# 1. Schema definitions
# ---------------------------------------------------------------------------

class IncidentBucket(BaseModel):
    """A single incident category bucket."""

    category: str
    severity: Literal["High", "Medium", "Low"]
    count: int = Field(..., ge=0)
    examples: List[str] = Field(default_factory=list, max_items=5)

    model_config = dict(extra="forbid")


class IncidentSummary(BaseModel):
    """Root model for a list of incident buckets."""

    __root__: List[IncidentBucket]

    model_config = dict(extra="forbid")


# ---------------------------------------------------------------------------
# 2. Sanitising helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_json_fence(raw: str) -> str | None:
    """Strip common ```json fences and surrounding whitespace."""
    if not raw:
        return None
    stripped = re.sub(_FENCE_RE, "", raw).strip()
    return stripped or None


# ---------------------------------------------------------------------------
# 3. Validation wrapper
# ---------------------------------------------------------------------------


def _validate(obj) -> IncidentSummary | None:
    """Validate object against ``IncidentSummary`` schema."""
    try:
        return IncidentSummary.model_validate(obj)
    except ValidationError:
        return None


# ---------------------------------------------------------------------------
# 4. Parse + repair loop
# ---------------------------------------------------------------------------


def parse_incident_summary(
    raw: str,
    llm_call: Callable[[str], str],
    *,
    max_attempts: int = 2,
) -> IncidentSummary:
    """Parse and validate an incident summary from an LLM.

    Parameters
    ----------
    raw:
        The original text produced by the LLM. It may include markdown fences
        or other formatting around the JSON.
    llm_call:
        Callback used to request a repaired JSON payload from the LLM when
        validation fails.
    max_attempts:
        Maximum number of repair attempts before giving up.
    """
    attempt, text = 0, raw
    while attempt <= max_attempts:
        attempt += 1

        candidate = _strip_json_fence(text)
        if candidate:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                parsed = None
        else:
            parsed = None

        summary = _validate(parsed) if parsed is not None else None
        if summary:
            return summary

        if attempt > max_attempts:
            break

        text = llm_call(
            "You returned invalid JSON for the Incident Summary schema. "
            "Error detail: schema mismatch. "
            "Regenerate ONLY a valid JSON array that matches the schema. "
            "Do not wrap it in markdown."
        )

    raise ValueError("Unable to produce valid IncidentSummary after repair")


# ---------------------------------------------------------------------------
# 5. Example usage
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Integration helpers
# ---------------------------------------------------------------------------

def try_parse_incident_summary(
    text: str, llm_call: Callable[[str], str]
) -> list[dict] | None:
    """Parse an incident summary if present.

    Parameters
    ----------
    text : str
        Raw LLM output possibly containing an incident summary JSON array.
    llm_call : Callable[[str], str]
        Callback used for self-repair attempts on invalid JSON.

    Returns
    -------
    list[dict] | None
        Parsed summary as list of dictionaries or ``None`` if no valid
        summary could be extracted.
    """
    try:
        summary = parse_incident_summary(text, llm_call)
        return summary.model_dump()
    except Exception:
        return None

