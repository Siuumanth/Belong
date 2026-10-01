from typing import List, Dict, Any, Tuple, Union, Optional
from config import settings

class CanonicalSerializer:
    """Canonical Semantic Serializer for converting structured profile JSON into
    clean, section-based, retrieval-focused text representations for vector embeddings.
    """

    def __init__(self, confidence_threshold: Optional[float] = None):
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else getattr(settings, "EMBEDDING_CONFIDENCE_THRESHOLD", 0.5)
        )

    def _extract_summaries(self, items: List[Any]) -> List[str]:
        """Extracts item summaries while filtering out low-confidence extractions
        and stripping quotes/metadata.
        """
        summaries = []
        if not isinstance(items, list):
            return summaries

        for item in items:
            if isinstance(item, dict):
                conf = item.get("confidence", 1.0)
                summary = item.get("summary", "")
            elif hasattr(item, "summary"):
                conf = getattr(item, "confidence", 1.0)
                summary = getattr(item, "summary", "")
            else:
                continue

            if conf >= self.confidence_threshold and summary and str(summary).strip():
                summaries.append(str(summary).strip())
        return summaries

    def serialize_self(self, profile: Union[Dict[str, Any], Any]) -> str:
        """Serializes the SELF aspect of a structured profile into canonical text representation."""
        if isinstance(profile, dict):
            self_data = profile.get("self", {})
        elif hasattr(profile, "self"):
            self_data = getattr(profile, "self", {})
        else:
            return ""

        def get_field(obj: Any, field: str) -> List[Any]:
            if isinstance(obj, dict):
                return obj.get(field, [])
            return getattr(obj, field, [])

        categories = [
            ("Values", get_field(self_data, "values")),
            ("Lifestyle", get_field(self_data, "lifestyle")),
            ("Personality", get_field(self_data, "personality_signals")),
            ("Interests", get_field(self_data, "interests")),
            ("Life goals", get_field(self_data, "life_goals")),
            ("Conflict style", get_field(self_data, "conflict_style")),
            ("Provides", get_field(self_data, "provides")),
            ("Emotional needs", get_field(self_data, "emotional_needs")),
        ]

        lines = ["SELF"]
        has_content = False

        for label, items in categories:
            summaries = self._extract_summaries(items)
            if summaries:
                has_content = True
                summary_str = ", ".join(summaries)
                if not summary_str.endswith("."):
                    summary_str += "."
                lines.append(f"{label}: {summary_str}")

        # Novel insights (escape hatch signals)
        novel_signals = []
        if isinstance(profile, dict):
            novel_signals = profile.get("novel_signals", []) or self_data.get("novel_signals", [])
        if novel_signals:
            novel_summaries = self._extract_summaries(novel_signals)
            if novel_summaries:
                has_content = True
                lines.append(f"Novel insights: {', '.join(novel_summaries)}.")

        # Compact Raw Dialogue summary (token budget capped ~200 chars)
        raw_dialogue = ""
        if isinstance(profile, dict):
            raw_dialogue = profile.get("raw_dialogue", "") or profile.get("raw_answers", "")
        if raw_dialogue and isinstance(raw_dialogue, str) and raw_dialogue.strip():
            has_content = True
            compact_raw = raw_dialogue.strip()
            if len(compact_raw) > 250:
                compact_raw = compact_raw[:250].rsplit(" ", 1)[0] + "..."
            lines.append(f"Raw dialogue: {compact_raw}")

        if not has_content:
            return ""

        return "\n\n".join([lines[0], "\n".join(lines[1:])])

    def serialize_wants(self, profile: Union[Dict[str, Any], Any]) -> str:
        """Serializes the WANTS aspect of a structured profile into canonical text representation."""
        if isinstance(profile, dict):
            wants_data = profile.get("wants", {})
        elif hasattr(profile, "wants"):
            wants_data = getattr(profile, "wants", {})
        else:
            return ""

        def get_field(obj: Any, field: str) -> List[Any]:
            if isinstance(obj, dict):
                return obj.get(field, [])
            return getattr(obj, field, [])

        categories = [
            ("Partner traits", get_field(wants_data, "partner_traits")),
            ("Partner values", get_field(wants_data, "partner_values")),
            ("Relationship expectations", get_field(wants_data, "relationship_expectations")),
            ("Desired lifestyle", get_field(wants_data, "desired_lifestyle")),
        ]

        lines = ["WANTS"]
        has_content = False

        for label, items in categories:
            summaries = self._extract_summaries(items)
            if summaries:
                has_content = True
                summary_str = ", ".join(summaries)
                if not summary_str.endswith("."):
                    summary_str += "."
                lines.append(f"{label}: {summary_str}")

        if not has_content:
            return ""

        return "\n\n".join([lines[0], "\n".join(lines[1:])])

    def serialize(self, profile: Union[Dict[str, Any], Any]) -> Tuple[str, str]:
        """Returns tuple of (self_text, wants_text) for a profile."""
        return self.serialize_self(profile), self.serialize_wants(profile)
