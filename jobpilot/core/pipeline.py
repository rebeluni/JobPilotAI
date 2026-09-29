"""
PipelineStage interface for JobPilot AI.
Every modular stage implements this base class, consuming and producing core schemas.
"""

from abc import ABC, abstractmethod
from typing import Any


class PipelineStage(ABC):
    """
    Abstract base class for all pipeline stages.
    Inputs and outputs must adhere to schemas in jobpilot.core.schemas.
    """
    stage_name: str = "base_stage"

    @abstractmethod
    async def run(self, input_data: Any) -> Any:
        """
        Process input data and produce output.
        Must return safe passthrough or raise appropriate domain error.
        """
        pass

    async def health_check(self) -> bool:
        """
        Verify if this stage's external dependencies (services, models, binaries) are reachable.
        Returns False if dependencies are missing or unhealthy.
        """
        return True
