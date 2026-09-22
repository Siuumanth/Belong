import json
import logging
import os
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from config import settings
from onboarding.state import OnboardingState
from onboarding.prompts import (
    CHATBOT_SYSTEM_PROMPT,
    SIGNAL_EXTRACTION_PROMPT,
    VAGUENESS_CHECK_PROMPT,
)
from profile.repository import ProfileRepository
from profile.models import ProfileCreate, ProfileUpdate

logger = logging.getLogger(__name__)

def get_llm():
    """Factory function to get the configured LLM client."""
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
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.LLM_PROVIDER}")


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
            elif isinstance(part, dict):
                if "text" in part and isinstance(part["text"], str):
                    parts.append(part["text"])
                else:
                    parts.append(str(part))
            else:
                parts.append(str(part))
        return "".join(parts)
    return str(content)

HIGH_PRIORITY_FIELDS = [
    {
        "keys": ["self.provides"],
        "topic": "What You Provide to a Partner",
        "prompt": "And separately, what do you feel you bring to a relationship as a partner?",
    },
    {
        "keys": ["self.emotional_needs"],
        "topic": "Emotional Needs",
        "prompt": "When you're feeling stressed or overwhelmed, what helps you feel supported by a partner?",
    },
    {
        "keys": ["self.conflict_style"],
        "topic": "Conflict Style",
        "prompt": "When there's a disagreement or tension, how do you usually handle it?",
    },
    {
        "keys": ["constraints.dealbreakers"],
        "topic": "Dealbreakers",
        "prompt": "Are there any specific dealbreakers or absolute boundaries that are non-negotiable for you in a partner?",
    },
    {
        "keys": ["wants.partner_traits", "wants.relationship_expectations"],
        "topic": "Partner Traits & Intent",
        "prompt": "What key traits, values, or expectations are most important to you in a partner?",
    },
]

def find_missing_high_priority_field(extracted_signals: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Checks if any high-priority field lacks extracted evidence."""
    for spec in HIGH_PRIORITY_FIELDS:
        if not any(len(extracted_signals.get(k, [])) > 0 for k in spec["keys"]):
            return spec
    return None

async def extract_signals_node(state: OnboardingState) -> Dict[str, Any]:
    """Node 1: Extract structured evidence signals from latest user input."""
    user_input = state.get("latest_user_input")
    current_idx = state.get("current_area_index", 0)
    questions = settings.ONBOARDING_QUESTIONS
    
    if not user_input:
        return {}

    if current_idx < len(questions):
        question_cfg = questions[current_idx]
        topic_id = question_cfg.id
        target_dimensions = ", ".join(question_cfg.targets)
    else:
        topic_id = "adaptive_probe"
        target_dimensions = "self.provides, self.emotional_needs, self.conflict_style, constraints.dealbreakers, wants.partner_traits, self.values"

    prompt = SIGNAL_EXTRACTION_PROMPT.format(
        topic_id=topic_id,
        target_dimensions=target_dimensions,
        latest_user_input=user_input,
        question_id=topic_id
    )

    extracted_signals = dict(state.get("extracted_signals", {}))

    try:
        llm = get_llm()
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        
        # Parse JSON from response
        content = get_message_content(response).strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)
        items = data.get("extracted_items", [])

        # Store signals under target_field paths (e.g. self.emotional_needs)
        for item in items:
            field_path = item.get("target_field")
            if not field_path:
                continue

            evidence_type = item.get("evidence_type", "explicit")
            confidence = item.get("confidence", 0.9)

            # Skip signals with insufficient evidence entirely
            if confidence < 0.25:
                logger.debug(f"Dropping signal for {field_path} — confidence {confidence} below threshold")
                continue

            if field_path not in extracted_signals:
                extracted_signals[field_path] = []

            # Deterministic signal ID: {topic_id}_{field_abbrev}_{index}
            field_abbrev = field_path.replace(".", "_").replace("self_", "s_").replace("wants_", "w_").replace("constraints_", "c_")
            signal_id = f"{topic_id}_{field_abbrev}_{len(extracted_signals[field_path]):02d}"

            extracted_signals[field_path].append({
                "id": signal_id,
                "label": item.get("label", ""),
                "summary": item.get("summary", ""),
                "quote": item.get("quote", ""),
                "question_id": item.get("question_id", topic_id),
                "confidence": confidence,
                "evidence_type": evidence_type,
            })

    except Exception as e:
        logger.error(f"Error in extract_signals_node: {e}")

    return {"extracted_signals": extracted_signals}

async def generate_response_node(state: OnboardingState) -> Dict[str, Any]:
    """Node 2: Evaluate answer depth and generate warm conversational response with coverage validation."""
    user_input = state.get("latest_user_input", "")
    current_idx = state.get("current_area_index", 0)
    follow_up_count = state.get("follow_up_count", 0)
    covered_areas = list(state.get("covered_areas", []))
    extracted_signals = state.get("extracted_signals", {})
    questions = settings.ONBOARDING_QUESTIONS
    max_total_probes = settings.MAX_FOLLOW_UPS + 2

    # Check if all core questions were already processed
    if current_idx >= len(questions):
        missing = find_missing_high_priority_field(extracted_signals)
        if missing and follow_up_count < max_total_probes:
            # Trigger adaptive probe for missing high-priority field
            sys_prompt = CHATBOT_SYSTEM_PROMPT.format(
                current_topic=missing["topic"],
                current_question=missing["prompt"],
                is_follow_up="Yes - targeted adaptive probe for high-priority profile coverage.",
                latest_user_input=user_input
            )
            llm = get_llm()
            assistant_resp = await llm.ainvoke([
                SystemMessage(content=sys_prompt),
                HumanMessage(content=f"User's reply: {user_input}" if user_input else "Continue onboarding.")
            ])
            return {
                "current_area_index": current_idx,
                "follow_up_count": follow_up_count + 1,
                "covered_areas": covered_areas,
                "latest_assistant_response": get_message_content(assistant_resp),
                "status": "active"
            }
        else:
            # Core questions and coverage checks complete
            conclusion_prompt = (
                "The user has completed all onboarding questions! "
                "Express warm appreciation, celebrate taking this step for meaningful connection, "
                "and explain that their profile is now being processed to find great compatibility matches."
            )
            llm = get_llm()
            resp = await llm.ainvoke([
                SystemMessage(content="You are Belong's warm onboarding assistant."),
                HumanMessage(content=conclusion_prompt)
            ])
            await finalize_profile(state)
            return {
                "latest_assistant_response": get_message_content(resp),
                "status": "completed"
            }

    current_q = questions[current_idx]
    
    # Check vagueness / need for follow-up if user provided input
    needs_follow_up = False
    if user_input and follow_up_count < settings.MAX_FOLLOW_UPS:
        try:
            llm = get_llm()
            v_prompt = VAGUENESS_CHECK_PROMPT.format(
                current_topic=current_q.topic,
                current_question=current_q.prompt,
                latest_user_input=user_input,
                follow_up_count=follow_up_count,
                max_follow_ups=settings.MAX_FOLLOW_UPS
            )
            v_resp = await llm.ainvoke([HumanMessage(content=v_prompt)])
            v_content = get_message_content(v_resp).strip()
            if "```json" in v_content:
                v_content = v_content.split("```json")[1].split("```")[0].strip()
            elif "```" in v_content:
                v_content = v_content.split("```")[1].split("```")[0].strip()
            v_data = json.loads(v_content)
            needs_follow_up = v_data.get("needs_follow_up", False)
        except Exception as e:
            logger.error(f"Error checking vagueness: {e}")

    if needs_follow_up:
        new_follow_up_count = follow_up_count + 1
        is_follow_up_str = "Yes - ask a gentle, specific follow-up probing deeper into this topic."
        next_prompt = current_q.prompt
    else:
        new_follow_up_count = follow_up_count
        if current_q.id not in covered_areas:
            covered_areas.append(current_q.id)
        
        next_idx = current_idx + 1
        if next_idx < len(questions):
            next_q = questions[next_idx]
            is_follow_up_str = "No - transition to the next topic naturally."
            next_prompt = next_q.prompt
            current_idx = next_idx
        else:
            current_idx = next_idx
            missing = find_missing_high_priority_field(extracted_signals)
            if missing and new_follow_up_count < max_total_probes:
                is_follow_up_str = "Yes - targeted adaptive probe for high-priority profile coverage."
                next_prompt = missing["prompt"]
            else:
                is_follow_up_str = "No - all questions complete."
                next_prompt = "Profile complete!"

    # Generate warm chatbot message
    sys_prompt = CHATBOT_SYSTEM_PROMPT.format(
        current_topic=current_q.topic if current_idx < len(questions) else "Profile Coverage",
        current_question=next_prompt,
        is_follow_up=is_follow_up_str,
        latest_user_input=user_input
    )
    
    llm = get_llm()
    assistant_resp = await llm.ainvoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"User's reply: {user_input}" if user_input else "Start the conversation.")
    ])

    new_status = "active"
    if current_idx >= len(questions) and not needs_follow_up:
        missing = find_missing_high_priority_field(extracted_signals)
        if not missing or new_follow_up_count >= max_total_probes:
            new_status = "completed"

    if new_status == "completed":
        await finalize_profile(state)

    return {
        "current_area_index": current_idx,
        "follow_up_count": new_follow_up_count,
        "covered_areas": covered_areas,
        "latest_assistant_response": get_message_content(assistant_resp),
        "status": new_status
    }

async def finalize_profile(state: OnboardingState):
    """Compiles extracted signals into the user's profile database record."""
    user_id_str = state.get("user_id")
    if not user_id_str:
        return
    
    from uuid import UUID
    user_id = UUID(user_id_str)
    signals = state.get("extracted_signals", {})
    
    # Structure profile into self/wants/constraints format
    profile_json = {
        "self": {
            "values": signals.get("self.values", []),
            "lifestyle": signals.get("self.lifestyle", []),
            "personality_signals": signals.get("self.personality_signals", []),
            "interests": signals.get("self.interests", []),
            "life_goals": signals.get("self.life_goals", []),
            "conflict_style": signals.get("self.conflict_style", []),
            "provides": signals.get("self.provides", []),
            "emotional_needs": signals.get("self.emotional_needs", []),
        },
        "wants": {
            "partner_traits": signals.get("wants.partner_traits", []),
            "partner_values": signals.get("wants.partner_values", []),
            "relationship_expectations": signals.get("wants.relationship_expectations", []),
            "desired_lifestyle": signals.get("wants.desired_lifestyle", []),
        },
        "constraints": {
            "dealbreakers": signals.get("constraints.dealbreakers", []),
        }
    }

    existing = await ProfileRepository.get_profile(user_id)
    if existing:
        await ProfileRepository.update_profile(user_id, ProfileUpdate(profile=profile_json))
    else:
        await ProfileRepository.create_profile(ProfileCreate(user_id=user_id, profile=profile_json))

def create_onboarding_graph():
    """Builds and compiles the LangGraph StateGraph."""
    workflow = StateGraph(OnboardingState)

    workflow.add_node("extract_signals", extract_signals_node)
    workflow.add_node("generate_response", generate_response_node)

    workflow.set_entry_point("extract_signals")
    workflow.add_edge("extract_signals", "generate_response")
    workflow.add_edge("generate_response", END)

    return workflow.compile()

# Global compiled graph instance
onboarding_graph = create_onboarding_graph()
