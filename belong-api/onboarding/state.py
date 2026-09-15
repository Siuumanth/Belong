from typing import List, Dict, Any, Optional, TypedDict

class OnboardingState(TypedDict, total=False):
    conversation_id: str
    user_id: str
    covered_areas: List[str]
    current_area_index: int
    follow_up_count: int
    extracted_signals: Dict[str, Any]
    latest_user_input: Optional[str]
    latest_assistant_response: Optional[str]
    status: str
