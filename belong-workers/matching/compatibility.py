import json
import logging
import os
import time
from typing import Any, Dict, Optional, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from config import settings
from matching.schemas import PairwiseCompatibilityOutput, DimensionDetail

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry helpers
# ---------------------------------------------------------------------------
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # seconds


def _retry_llm_invoke(fn, *args, **kwargs):
    """Simple exponential-backoff retry wrapper for LLM calls with empty-response detection."""
    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            res = fn(*args, **kwargs)
            # Check if an LLM message returned empty content
            if hasattr(res, "content") and not getattr(res, "content"):
                raise ValueError("LLM returned empty content string")
            return res
        except Exception as exc:
            last_exc = exc
            err_str = str(exc).lower()
            # Retry on rate-limit (429), connection issues, or empty-output errors
            if any(k in err_str for k in ("429", "rate limit", "empty", "output text", "too many requests")):
                delay = _RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    f"LLM call failed (attempt {attempt + 1}/{_MAX_RETRIES}): {exc}. "
                    f"Retrying in {delay:.1f}s…"
                )
                time.sleep(delay)
            else:
                raise  # Non-retriable error — fail fast
    assert last_exc is not None
    raise last_exc

class PairwiseState(TypedDict):
    user_a_profile: Dict[str, Any]
    user_b_profile: Dict[str, Any]
    prompt_text: Optional[str]
    parsed_output: Optional[PairwiseCompatibilityOutput]
    error: Optional[str]

def get_llm():
    """Factory function to instantiate configured LLM.

    Default model on Groq: llama-3.1-8b-instant — it is free-tier safe,
    supports json_mode, and produces structured output reliably.
    Override via LLM_MODEL env var.
    """
    provider = settings.LLM_PROVIDER.lower()
    if provider == "groq":
        api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=2048,
                groq_api_key=api_key,
            )
        except (ImportError, ModuleNotFoundError):
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=2048,
                api_key=api_key or "missing_key",
                base_url="https://api.groq.com/openai/v1",
            )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

# --- LangGraph Nodes ---

def _slim_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Strip signal metadata (id, confidence, evidence_type, question_id) from a profile
    before sending to the LLM. Keeps only label, summary, quote — cuts token count ~50%."""
    def slim_signals(signals: Any) -> Any:
        if not isinstance(signals, list):
            return signals
        result = []
        for s in signals:
            if isinstance(s, dict):
                result.append({
                    "id": s.get("id", ""),
                    "label": s.get("label", ""),
                    "summary": s.get("summary", ""),
                    "quote": s.get("quote", ""),
                })
            else:
                result.append(s)
        return result

    slimmed: Dict[str, Any] = {}
    for section_key in ("self", "wants", "constraints"):
        section = profile.get(section_key)
        if isinstance(section, dict):
            slimmed[section_key] = {k: slim_signals(v) for k, v in section.items()}
        elif section is not None:
            slimmed[section_key] = section

    # Include other_signals (unmapped/novel signals)
    other_sigs = profile.get("other_signals") or profile.get("novel_signals")
    if other_sigs:
        slimmed["other_signals"] = slim_signals(other_sigs)

    # Include original raw responses/dialogue
    raw_resp = profile.get("raw_responses") or profile.get("raw_dialogue")
    if raw_resp:
        slimmed["original_responses"] = raw_resp

    # Preserve top-level demographic fields (age, gender, relationship_goal)
    for key in ("age", "gender", "relationship_goal"):
        if key in profile:
            slimmed[key] = profile[key]

    return slimmed


def format_prompt_node(state: PairwiseState) -> Dict[str, Any]:
    """Node 1: Formats the configurable prompt template with User A and B profiles."""
    user_a_str = json.dumps(_slim_profile(state["user_a_profile"]), separators=(',', ':'))
    user_b_str = json.dumps(_slim_profile(state["user_b_profile"]), separators=(',', ':'))

    prompt = settings.PAIRWISE_REASONING_PROMPT_TEMPLATE.format(
        user_a_profile=user_a_str,
        user_b_profile=user_b_str
    )
    return {"prompt_text": prompt}

def get_message_content(response: Any) -> str:
    """Safely extract string content from LangChain AI response object or list."""
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)


def llm_reasoning_node(state: PairwiseState) -> Dict[str, Any]:
    """Node 2: Invokes LLM and parses JSON response. Model-agnostic — no tool use required."""
    import re
    try:
        llm = get_llm()
        messages = [
            SystemMessage(
                content=(
                    "You are an expert AI compatibility reasoning agent for Belong. "
                    "Return your analysis ONLY as a valid JSON object matching the required schema. "
                    "Do not include any explanation, markdown, or text outside the JSON object. "
                    "Start your response with '{' and end with '}'."
                )
            ),
            HumanMessage(content=state.get("prompt_text", "")),
        ]

        raw_response = _retry_llm_invoke(llm.invoke, messages)
        content = get_message_content(raw_response).strip()

        if not content:
            raise RuntimeError("LLM returned empty response")

        # Strip markdown fences if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        # Parse and validate
        try:
            data = json.loads(content)
        except Exception:
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                data = json.loads(match.group(0))
            else:
                raise

        if "overall_verdict" not in data:
            data["overall_verdict"] = "partial_alignment"

        return {"parsed_output": PairwiseCompatibilityOutput.model_validate(data), "error": None}

    except Exception as e:
        logger.error(f"Error during pairwise LLM reasoning: {e}", exc_info=True)
        return {"parsed_output": None, "error": str(e)}


def _build_signal_index(profile: Dict[str, Any]) -> Dict[str, str]:
    """Build a flat {signal_id: quote} index from a structured profile dict.
    
    Walks all fields in 'self', 'wants', and 'constraints' and indexes each
    signal by its 'id' field so the reasoning model's ID citations can be resolved
    to actual user quotes without regenerating evidence strings.
    """
    index: Dict[str, str] = {}
    for section in ("self", "wants", "constraints"):
        section_data = profile.get(section, {})
        if not isinstance(section_data, dict):
            continue
        for field_signals in section_data.values():
            if not isinstance(field_signals, list):
                continue
            for signal in field_signals:
                if isinstance(signal, dict) and "id" in signal:
                    index[signal["id"]] = signal.get("quote", signal.get("label", ""))

    # Also index other_signals and novel_signals
    for other_key in ("other_signals", "novel_signals"):
        other_list = profile.get(other_key)
        if isinstance(other_list, list):
            for signal in other_list:
                if isinstance(signal, dict) and "id" in signal:
                    index[signal["id"]] = signal.get("quote", signal.get("label", ""))
    return index


def validation_node(state: PairwiseState) -> Dict[str, Any]:
    """Node 3: Validates verdict consistency and resolves evidence IDs to actual quotes."""
    parsed = state.get("parsed_output")
    if not parsed:
        return {"error": state.get("error") or "Failed to parse structured compatibility output."}

    valid_verdicts = {"strong_alignment", "partial_alignment", "unclear", "conflict"}
    if parsed.overall_verdict not in valid_verdicts:
        logger.warning(f"Normalizing unrecognized overall verdict '{parsed.overall_verdict}' to 'unclear'")
        parsed.overall_verdict = "unclear"

    # Build signal index for both users so we can resolve ID citations → actual quotes
    index_a = _build_signal_index(state.get("user_a_profile", {}))
    index_b = _build_signal_index(state.get("user_b_profile", {}))

    # Attach resolved quotes to state for downstream display (not mutating the Pydantic model)
    resolved_evidence: Dict[str, Any] = {}
    for dim_name in ("emotional_needs", "core_values", "lifestyle", "conflict_style"):
        dim: Optional[DimensionDetail] = getattr(parsed.dimension_results, dim_name, None)
        if dim is None:
            continue
        resolved_evidence[dim_name] = {
            "verdict": dim.verdict,
            "reasoning": dim.reasoning,
            "evidence_a": [{"id": sid, "quote": index_a.get(sid, f"[ID {sid} not found]")} for sid in dim.evidence_a_ids],
            "evidence_b": [{"id": sid, "quote": index_b.get(sid, f"[ID {sid} not found]")} for sid in dim.evidence_b_ids],
        }

    return {"parsed_output": parsed, "resolved_evidence": resolved_evidence}

# --- Build LangGraph Workflow ---

def build_compatibility_graph() -> CompiledStateGraph:
    workflow = StateGraph(PairwiseState)  # type: ignore[type-var]

    workflow.add_node("format_prompt", format_prompt_node)
    workflow.add_node("llm_reasoning", llm_reasoning_node)
    workflow.add_node("validation", validation_node)

    workflow.set_entry_point("format_prompt")
    workflow.add_edge("format_prompt", "llm_reasoning")
    workflow.add_edge("llm_reasoning", "validation")
    workflow.add_edge("validation", END)

    return workflow.compile()

compatibility_agent: CompiledStateGraph = build_compatibility_graph()

class PairwiseCompatibilityAgent:
    """Interface class to invoke the LangGraph pairwise reasoning graph."""

    async def evaluate_pair(
        self, 
        user_a_profile: Dict[str, Any], 
        user_b_profile: Dict[str, Any]
    ) -> PairwiseCompatibilityOutput:
        """Executes pairwise reasoning between User A and User B profiles."""
        initial_state: PairwiseState = {
            "user_a_profile": user_a_profile,
            "user_b_profile": user_b_profile,
            "prompt_text": None,
            "parsed_output": None,
            "error": None
        }

        final_state = await compatibility_agent.ainvoke(initial_state)

        if final_state.get("error"):
            raise RuntimeError(f"Pairwise reasoning failed: {final_state['error']}")

        parsed = final_state.get("parsed_output")
        if not parsed:
            raise RuntimeError("Pairwise reasoning produced empty output.")

        return parsed
