import json
import logging
from typing import Dict, Any
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
    if provider == "google":
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

async def extract_signals_node(state: OnboardingState) -> Dict[str, Any]:
    """Node 1: Extract structured evidence signals from latest user input."""
    user_input = state.get("latest_user_input")
    current_idx = state.get("current_area_index", 0)
    questions = settings.ONBOARDING_QUESTIONS
    
    if not user_input or current_idx >= len(questions):
        return {}

    question_cfg = questions[current_idx]
    prompt = SIGNAL_EXTRACTION_PROMPT.format(
        topic_id=question_cfg.id,
        target_dimensions=", ".join(question_cfg.targets),
        latest_user_input=user_input,
        question_id=question_cfg.id
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
            
            if field_path not in extracted_signals:
                extracted_signals[field_path] = []
            
            extracted_signals[field_path].append({
                "label": item.get("label", ""),
                "summary": item.get("summary", ""),
                "quote": item.get("quote", ""),
                "question_id": item.get("question_id", question_cfg.id),
                "confidence": item.get("confidence", 0.9)
            })

    except Exception as e:
        logger.error(f"Error in extract_signals_node: {e}")

    return {"extracted_signals": extracted_signals}

async def generate_response_node(state: OnboardingState) -> Dict[str, Any]:
    """Node 2: Evaluate answer depth and generate warm conversational response."""
    user_input = state.get("latest_user_input", "")
    current_idx = state.get("current_area_index", 0)
    follow_up_count = state.get("follow_up_count", 0)
    covered_areas = list(state.get("covered_areas", []))
    questions = settings.ONBOARDING_QUESTIONS
    
    # If all core questions were already covered
    if current_idx >= len(questions):
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
        
        # Save structured profile to profiles table
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
            is_follow_up_str = "No - all questions complete."
            next_prompt = "Profile complete!"

    # Generate warm chatbot message
    sys_prompt = CHATBOT_SYSTEM_PROMPT.format(
        current_topic=current_q.topic,
        current_question=next_prompt,
        is_follow_up=is_follow_up_str,
        latest_user_input=user_input
    )
    
    llm = get_llm()
    assistant_resp = await llm.ainvoke([
        SystemMessage(content=sys_prompt),
        HumanMessage(content=f"User's reply: {user_input}" if user_input else "Start the conversation.")
    ])

    new_status = "completed" if current_idx >= len(questions) and not needs_follow_up else "active"

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
