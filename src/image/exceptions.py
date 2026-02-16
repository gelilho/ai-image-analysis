"""Custom exceptions for the image analysis module."""


class ImageAnalysisError(Exception):
    """Base exception for image analysis operations."""

    pass


class ValidationError(ImageAnalysisError):
    """Raised when input validation fails."""

    pass
