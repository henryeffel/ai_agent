from abc import ABC, abstractmethod

from ieum.schemas.action_plan import ActionCreate
from ieum.schemas.knowledge import KnowledgeSearchHit
from ieum.schemas.meeting import MeetingAnalysis


class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return a stable provider identifier."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the configured model identifier."""

    @abstractmethod
    def analyze_meeting(self, transcript: str) -> MeetingAnalysis:
        """Convert a meeting transcript into validated structured data."""

    @abstractmethod
    def generate_grounded_actions(
        self,
        analysis: MeetingAnalysis,
        evidence: list[KnowledgeSearchHit],
    ) -> list[ActionCreate]:
        """Generate executable actions supported by retrieved evidence."""
