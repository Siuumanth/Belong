import json
import logging
import os
from typing import Dict, Any, Optional, TypedDict
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from config import settings
from matching.schemas import PairwiseCompatibilityOutput

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
        response: PairwiseCompatibilityOutput = structured_llm.invoke([
            HumanMessage(content=prompt_text)
        ])

        return {"parsed_output": response, "error": None}
    except Exception as e:
        logger.error(f"Error during pairwise LLM reasoning: {e}", exc_info=True)
        return {"parsed_output": None, "error": str(e)}

def validation_node(state: PairwiseState) -> Dict[str, Any]:
    """Node 3: Validates and ensures verdict consistency."""
    parsed = state.get("parsed_output")
    if not parsed:
        return {"error": state.get("error") or "Failed to parse structured compatibility output."}

    valid_verdicts = {"strong_alignment", "partial_alignment", "unclear", "conflict"}
    if parsed.overall_verdict not in valid_verdicts:
        logger.warning(f"Normalizing unrecognized overall verdict '{parsed.overall_verdict}' to 'unclear'")
        parsed.overall_verdict = "unclear"

    return {"parsed_output": parsed}

# --- Build LangGraph Workflow ---

def build_compatibility_graph() -> StateGraph:
    workflow = StateGraph(PairwiseState)

    workflow.add_node("format_prompt", format_prompt_node)
    workflow.add_node("llm_reasoning", llm_reasoning_node)
    workflow.add_node("validation", validation_node)

    workflow.set_entry_point("format_prompt")
    workflow.add_edge("format_prompt", "llm_reasoning")
    workflow.add_edge("llm_reasoning", "validation")
    workflow.add_edge("validation", END)

    return workflow.compile()

compatibility_agent = build_compatibility_graph()

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
