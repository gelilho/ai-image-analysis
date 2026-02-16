"""Abstract base class for image analyzers."""

from abc import ABC, abstractmethod
from typing import Any


class AbstractImageAnalyzer(ABC):
    """Interface that all image analyzers must implement."""

    @abstractmethod
    def analyze_images(self, image_urls: list[str]) -> dict[str, Any]:
        """Analyze a list of images and return analysis results."""
        pass
