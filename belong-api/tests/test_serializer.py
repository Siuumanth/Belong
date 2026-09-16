import unittest
from profile.models import (
    StructuredProfileJSON,
    SelfProfile,
    WantsProfile,
    ConstraintsProfile,
    EvidenceItem,
)
from embeddings.serializer import CanonicalSerializer

class TestCanonicalSerializer(unittest.TestCase):
    def test_canonical_serializer_formatting(self):
        serializer = CanonicalSerializer(confidence_threshold=0.5)

        profile = StructuredProfileJSON(
            self=SelfProfile(
                values=[
                    EvidenceItem(label="Values", summary="honesty", quote="I value honesty.", question_id="q4", confidence=0.9),
                    EvidenceItem(label="Values", summary="independence", quote="I need space.", question_id="q4", confidence=0.85),
                ],
                lifestyle=[
                    EvidenceItem(label="Lifestyle", summary="enjoys travelling", quote="I love trips.", question_id="q4", confidence=0.95),
                ],
                conflict_style=[
                    EvidenceItem(label="Conflict", summary="prefers discussing problems openly", quote="Let's talk.", question_id="q3", confidence=0.88),
                ],
                provides=[
                    EvidenceItem(label="Provides", summary="emotional support", quote="I listen.", question_id="q3", confidence=0.92),
                ],
            ),
            wants=WantsProfile(
                partner_traits=[
                    EvidenceItem(label="PartnerTraits", summary="emotionally available", quote="Be open.", question_id="q1", confidence=0.91),
                    EvidenceItem(label="PartnerTraits", summary="independent", quote="Have own life.", question_id="q1", confidence=0.87),
                ],
                desired_lifestyle=[
                    EvidenceItem(label="DesiredLifestyle", summary="active lifestyle", quote="Move.", question_id="q4", confidence=0.75),
                ],
            ),
            constraints=ConstraintsProfile(),
        )

        self_text = serializer.serialize_self(profile)
        wants_text = serializer.serialize_wants(profile)

        # Assert category headers and field contents
        self.assertIn("SELF", self_text)
        self.assertIn("Values: honesty, independence.", self_text)
        self.assertIn("Lifestyle: enjoys travelling.", self_text)
        self.assertIn("Conflict style: prefers discussing problems openly.", self_text)
        self.assertIn("Provides: emotional support.", self_text)

        # Assert empty categories are omitted
        self.assertNotIn("Personality:", self_text)
        self.assertNotIn("Interests:", self_text)
        self.assertNotIn("Life goals:", self_text)

        # Assert quotes and metadata are excluded from embedding text
        self.assertNotIn("quote:", self_text)
        self.assertNotIn("question_id", self_text)
        self.assertNotIn("I value honesty.", self_text)

        # Assert WANTS formatting
        self.assertIn("WANTS", wants_text)
        self.assertIn("Partner traits: emotionally available, independent.", wants_text)
        self.assertIn("Desired lifestyle: active lifestyle.", wants_text)
        self.assertNotIn("Partner values:", wants_text)

    def test_confidence_filtering(self):
        serializer = CanonicalSerializer(confidence_threshold=0.5)

        profile = StructuredProfileJSON(
            self=SelfProfile(
                values=[
                    EvidenceItem(label="Values", summary="integrity", quote="...", question_id="q4", confidence=0.9),
                    EvidenceItem(label="Values", summary="unreliable signal", quote="...", question_id="q4", confidence=0.3),  # below 0.5
                ]
            )
        )

        self_text = serializer.serialize_self(profile)
        self.assertIn("integrity", self_text)
        self.assertNotIn("unreliable signal", self_text)

    def test_empty_profile(self):
        serializer = CanonicalSerializer()
        empty_profile = StructuredProfileJSON()

        self_text, wants_text = serializer.serialize(empty_profile)
        self.assertEqual(self_text, "")
        self.assertEqual(wants_text, "")

if __name__ == "__main__":
    unittest.main()
