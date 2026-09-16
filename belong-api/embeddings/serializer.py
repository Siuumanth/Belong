from typing import List, Dict, Any, Tuple, Union, Optional
from profile.models import StructuredProfileJSON, EvidenceItem, SelfProfile, WantsProfile
from config import settings

class CanonicalSerializer:
    """Canonical Semantic Serializer for converting structured profile JSON into

    clean, section-based, retrieval-focused text representations for vector embeddings.
    """

    def __init__(self, confidence_threshold: float = None):
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.EMBEDDING_CONFIDENCE_THRESHOLD
        )

    def _extract_summaries(self, items: List[Union[EvidenceItem, Dict[str, Any]]]) -> List[str]:
        """Extracts item summaries while filtering out low-confidence extractions

        and stripping quotes/metadata.
        """
        summaries = []
        for item in items:
            if isinstance(item, EvidenceItem):
                conf = item.confidence
                summary = item.summary
            elif isinstance(item, dict):
                conf = item.get("confidence", 1.0)
                summary = item.get("summary", "")
            else:
                continue

            if conf >= self.confidence_threshold and summary and summary.strip():
                summaries.append(summary.strip())
        return summaries

    def serialize_self(self, profile: Union[StructuredProfileJSON, Dict[str, Any]]) -> str:
        """Serializes the SELF aspect of a structured profile into canonical text representation.

        Format:
        SELF

        Values: honesty, independence.
        Lifestyle: enjoys travelling, active lifestyle.
        ...
        """
        if isinstance(profile, StructuredProfileJSON):
            self_data = profile.self
        elif isinstance(profile, dict):
            self_data = profile.get("self", {})
        else:
            return ""

        # Map field name to human-readable label
        categories = [
            ("Values", getattr(self_data, "values", []) if isinstance(self_data, SelfProfile) else self_data.get("values", [])),
            ("Lifestyle", getattr(self_data, "lifestyle", []) if isinstance(self_data, SelfProfile) else self_data.get("lifestyle", [])),
            ("Personality", getattr(self_data, "personality_signals", []) if isinstance(self_data, SelfProfile) else self_data.get("personality_signals", [])),
            ("Interests", getattr(self_data, "interests", []) if isinstance(self_data, SelfProfile) else self_data.get("interests", [])),
            ("Life goals", getattr(self_data, "life_goals", []) if isinstance(self_data, SelfProfile) else self_data.get("life_goals", [])),
            ("Conflict style", getattr(self_data, "conflict_style", []) if isinstance(self_data, SelfProfile) else self_data.get("conflict_style", [])),
            ("Provides", getattr(self_data, "provides", []) if isinstance(self_data, SelfProfile) else self_data.get("provides", [])),
            ("Emotional needs", getattr(self_data, "emotional_needs", []) if isinstance(self_data, SelfProfile) else self_data.get("emotional_needs", [])),
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

        if not has_content:
            return ""

        return "\n\n".join([lines[0], "\n".join(lines[1:])])

    def serialize_wants(self, profile: Union[StructuredProfileJSON, Dict[str, Any]]) -> str:
        """Serializes the WANTS aspect of a structured profile into canonical text representation.

        Format:
        WANTS

        Partner traits: emotionally available, independent.
        Emotional needs: reassurance, emotional support.
        ...
        """
        if isinstance(profile, StructuredProfileJSON):
            wants_data = profile.wants
        elif isinstance(profile, dict):
            wants_data = profile.get("wants", {})
        else:
            return ""

        categories = [
            ("Partner traits", getattr(wants_data, "partner_traits", []) if isinstance(wants_data, WantsProfile) else wants_data.get("partner_traits", [])),
            ("Partner values", getattr(wants_data, "partner_values", []) if isinstance(wants_data, WantsProfile) else wants_data.get("partner_values", [])),
            ("Relationship expectations", getattr(wants_data, "relationship_expectations", []) if isinstance(wants_data, WantsProfile) else wants_data.get("relationship_expectations", [])),
            ("Desired lifestyle", getattr(wants_data, "desired_lifestyle", []) if isinstance(wants_data, WantsProfile) else wants_data.get("desired_lifestyle", [])),
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

    def serialize(self, profile: Union[StructuredProfileJSON, Dict[str, Any]]) -> Tuple[str, str]:
        """Returns tuple of (self_text, wants_text) for a profile."""
        return self.serialize_self(profile), self.serialize_wants(profile)
