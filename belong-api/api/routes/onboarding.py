from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from config import settings
from onboarding.repository import OnboardingRepository
from onboarding.graph import onboarding_graph
from embeddings.service import EmbeddingService

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

class StartSessionRequest(BaseModel):
    user_id: UUID

class StartSessionResponse(BaseModel):
    conversation_id: UUID
    user_id: UUID
    first_question: str
    status: str

class SendMessageRequest(BaseModel):
    conversation_id: UUID
    message: str

class SendMessageResponse(BaseModel):
    conversation_id: UUID
    assistant_response: str
    status: str
    current_area_index: int
    follow_up_count: int

class ConversationDetailsResponse(BaseModel):
    conversation_id: UUID
    user_id: UUID
    status: str
    state: Dict[str, Any]
    messages: List[Dict[str, Any]]

@router.post("/session", response_model=StartSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(payload: StartSessionRequest):
    # Initialize onboarding state
    first_q = settings.ONBOARDING_QUESTIONS[0]
    initial_state = {
        "user_id": str(payload.user_id),
        "covered_areas": [],
        "current_area_index": 0,
        "follow_up_count": 0,
        "extracted_signals": {},
        "latest_user_input": None,
        "latest_assistant_response": first_q.prompt,
        "status": "active"
    }

    conversation = await OnboardingRepository.create_conversation(
        user_id=payload.user_id,
        initial_state=initial_state
    )

    conv_id = UUID(str(conversation["id"]))
    
    # Save the initial assistant prompt in conversation_messages
    await OnboardingRepository.add_message(
        conversation_id=conv_id,
        role="assistant",
        content=first_q.prompt,
        question_id=first_q.id
    )

    return StartSessionResponse(
        conversation_id=conv_id,
        user_id=payload.user_id,
        first_question=first_q.prompt,
        status="active"
    )

@router.post("/message", response_model=SendMessageResponse)
async def send_message(payload: SendMessageRequest, background_tasks: BackgroundTasks):
    conversation = await OnboardingRepository.get_conversation(payload.conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {payload.conversation_id} not found."
        )

    if conversation["status"] == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Onboarding conversation has already been completed."
        )

    current_state = {
        "conversation_id": str(payload.conversation_id),
        "user_id": str(conversation["user_id"]),
        "status": conversation["status"],
        "current_area_index": conversation.get("current_area_index", 0),
        "follow_up_count": conversation.get("follow_up_count", 0),
        "covered_areas": conversation.get("covered_areas", []),
        "extracted_signals": conversation.get("extracted_signals", {}),
        "latest_user_input": payload.message,
        "latest_assistant_response": None
    }

    # Record user message in DB
    current_idx = current_state.get("current_area_index", 0)
    current_q_id = (
        settings.ONBOARDING_QUESTIONS[current_idx].id 
        if current_idx < len(settings.ONBOARDING_QUESTIONS) 
        else None
    )
    
    await OnboardingRepository.add_message(
        conversation_id=payload.conversation_id,
        role="user",
        content=payload.message,
        question_id=current_q_id
    )

    # Run one step of the LangGraph graph
    new_state = await onboarding_graph.ainvoke(current_state)

    assistant_reply = new_state.get(
        "latest_assistant_response", 
        "Thank you for sharing that!"
    )
    new_status = new_state.get("status", "active")

    # Record assistant message in DB
    await OnboardingRepository.add_message(
        conversation_id=payload.conversation_id,
        role="assistant",
        content=assistant_reply,
        question_id=current_q_id
    )

    # Persist state back to DB
    await OnboardingRepository.update_conversation_state(
        conversation_id=payload.conversation_id,
        state=new_state,
        status=new_status
    )

    # Trigger background embedding generation upon onboarding completion
    if new_status == "completed":
        embedding_service = EmbeddingService()
        background_tasks.add_task(
            embedding_service.generate_and_store_embeddings, 
            conversation["user_id"]
        )

    return SendMessageResponse(
        conversation_id=payload.conversation_id,
        assistant_response=assistant_reply,
        status=new_status,
        current_area_index=new_state.get("current_area_index", 0),
        follow_up_count=new_state.get("follow_up_count", 0)
    )

@router.get("/{conversation_id}", response_model=ConversationDetailsResponse)
async def get_conversation_details(conversation_id: UUID):
    conversation = await OnboardingRepository.get_conversation(conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found."
        )

    messages = await OnboardingRepository.get_messages(conversation_id)

    reconstructed_state = {
        "current_area_index": conversation.get("current_area_index", 0),
        "follow_up_count": conversation.get("follow_up_count", 0),
        "covered_areas": conversation.get("covered_areas", []),
        "extracted_signals": conversation.get("extracted_signals", {})
    }

    return ConversationDetailsResponse(
        conversation_id=UUID(str(conversation["id"])),
        user_id=UUID(str(conversation["user_id"])),
        status=conversation["status"],
        state=reconstructed_state,
        messages=messages
    )
