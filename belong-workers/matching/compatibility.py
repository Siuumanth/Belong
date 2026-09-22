import json
import logging
import os
from typing import Any, Dict, Optional, TypedDict, cast
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph

from config import settings
from matching.schemas import PairwiseCompatibilityOutput, DimensionDetail

logger = logging.getLogger(__name__)

class PairwiseState(TypedDict):
    user_a_profile: Dict[str, Any]
    user_b_profile: Dict[str, Any]
    prompt_text: Optional[str]
    parsed_output: Optional[PairwiseCompatibilityOutput]
    error: Optional[str]

def get_llm():
    """Factory function to instantiate configured LLM (Groq default)."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "groq":
        api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY")
        try:
            from langchain_groq import ChatGroq
            return ChatGroq(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                groq_api_key=api_key
            )
        except (ImportError, ModuleNotFoundError):
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                api_key=api_key or "missing_key",
                base_url="https://api.groq.com/openai/v1"
            )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE
        )
    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")

# --- LangGraph Nodes ---

def format_prompt_node(state: PairwiseState) -> Dict[str, Any]:
    """Node 1: Formats the configurable prompt template with User A and B profiles."""
    user_a_str = json.dumps(state["user_a_profile"], indent=2)
    user_b_str = json.dumps(state["user_b_profile"], indent=2)

    prompt = settings.PAIRWISE_REASONING_PROMPT_TEMPLATE.format(
        user_a_profile=user_a_str,
        user_b_profile=user_b_str
    )
    return {"prompt_text": prompt}

def llm_reasoning_node(state: PairwiseState) -> Dict[str, Any]:
    """Node 2: Invokes Groq LLM with structured output constraint."""
    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(PairwiseCompatibilityOutput)
        
        prompt_text = state.get("prompt_text", "")
        response = cast(PairwiseCompatibilityOutput, structured_llm.invoke([
            HumanMessage(content=prompt_text)
        ]))

        return {"parsed_output": response, "error": None}
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
