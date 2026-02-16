"""
Image processing module.

Handles image fetching, validation, and preparation for LLM inference.
Refactored to eliminate redundant fetching and separate concerns.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from typing import List, Optional

import requests
from PIL import Image
from PIL.Image import Image as PILImage

logger = logging.getLogger(__name__)


class ImageError(Enum):
    """Specific image error types for image processing."""

    NONE = "none"
    INVALID_FORMAT = "invalid_format"
    TOO_LARGE = "too_large"
    CORRUPTED = "corrupted"
    URL_INACCESSIBLE = "url_inaccessible"
    LOW_QUALITY = "low_quality"
    MISSING = "missing"
    PROCESSING_ERROR = "processing_error"
    INCOMPLETE = "incomplete"


@dataclass
class ImageConfig:
    """Configuration for image processing thresholds and constraints."""

    allowed_mime_types: List[str] = field(
        default_factory=lambda: [
            "image/jpeg",
            "image/png",
            "application/pdf",
        ]
    )
    max_file_size_mb: float = 20.0
    reject_size_mb: float = 20.0
    min_file_size_mb: float = 0.05
    max_width: int = 1200
    max_height: int = 1200
    default_quality: int = 85
    min_quality_size_mb: float = 0.05
    min_dimensions: int = 200
    max_images: int = 10
    fetch_timeout_seconds: int = 10

    def __post_init__(self):
        if self.allowed_mime_types is None:
            self.allowed_mime_types = [
                "image/jpeg",
                "image/png",
                "application/pdf",
            ]


@dataclass
class FetchedImage:
    """Container for a successfully fetched image with metadata."""

    url: str
    content: bytes
    content_type: str
    size_bytes: int
    image_type: str  # 'outsole', 'defect', 'tag', or 'unknown'

    @property
    def size_mb(self) -> float:
        """Return size in megabytes."""
        return self.size_bytes / (1024 * 1024)


@dataclass
class ImageFetchResult:
    """Result of fetching images."""

    images: List[FetchedImage]
    errors: List[str]
    error_type: ImageError

    @property
    def success(self) -> bool:
        """Whether any images were successfully fetched."""
        return len(self.images) > 0 and self.error_type == ImageError.NONE

    @property
    def has_all_types(self) -> bool:
        """Whether all required image types are present."""
        types_found = {img.image_type for img in self.images}
        return {"outsole", "defect", "tag"}.issubset(types_found)


@dataclass
class ValidationResult:
    """Result of validating a single image."""

    valid: bool
    error_type: ImageError
    processed_data: Optional[bytes]
    message: str = ""


class ImageClassifier:
    """Classifies images by type based on URL patterns and position."""

    @staticmethod
    def classify(url: str = "", position: int = -1) -> str:
        """
        Classify image as 'outsole', 'defect', 'tag', or 'unknown'.

        Args:
            url: The image URL (may contain type hints)
            position: Position in the image list (0-indexed)

        Returns:
            Image type classification
        """
        # Try URL hints first
        url_lower = url.lower()
        if "outsole" in url_lower or "sole" in url_lower or "bottom" in url_lower:
            return "outsole"
        elif (
            "defect" in url_lower
            or "damage" in url_lower
            or "issue" in url_lower
            or "problem" in url_lower
        ):
            return "defect"
        elif (
            "tag" in url_lower
            or "label" in url_lower
            or "inside" in url_lower
            or "inner" in url_lower
        ):
            return "tag"

        # Fallback to position-based assumption
        position_map = {0: "outsole", 1: "defect", 2: "tag"}
        return position_map.get(position, "unknown")


class ImageValidator:
    """Validates and processes image data according to quality thresholds."""

    def __init__(self, config: ImageConfig):
        """
        Initialize validator with configuration.

        Args:
            config: Image processing configuration
        """
        self.config = config

    def validate_and_process(
        self, image_data: bytes, image_index: int = 0
    ) -> ValidationResult:
        """
        Validate and optionally process a single image.

        Args:
            image_data: Raw image bytes
            image_index: Image index for logging

        Returns:
            ValidationResult with validation status and processed data
        """
        try:
            # Try to open image
            try:
                image: PILImage = Image.open(BytesIO(image_data))
            except Exception as e:
                logger.error(f"Cannot open image {image_index}: {e}")
                return ValidationResult(
                    valid=False,
                    error_type=ImageError.CORRUPTED,
                    processed_data=None,
                    message=f"Image {image_index} is corrupted or unreadable",
                )

            # Get image properties
            width, height = image.size
            file_size_mb = len(image_data) / (1024 * 1024)

            # Check dimensions for quality
            if (
                width < self.config.min_dimensions
                or height < self.config.min_dimensions
            ):
                logger.warning(
                    f"Image {image_index} dimensions too small: {width}x{height}"
                )
                return ValidationResult(
                    valid=False,
                    error_type=ImageError.LOW_QUALITY,
                    processed_data=None,
                    message=f"Image {image_index} dimensions too small: {width}x{height}",
                )

            # Check file size for quality
            if file_size_mb < self.config.min_quality_size_mb:
                logger.warning(
                    f"Image {image_index} file size too small: {file_size_mb:.2f}MB"
                )
                return ValidationResult(
                    valid=False,
                    error_type=ImageError.LOW_QUALITY,
                    processed_data=None,
                    message=f"Image {image_index} file size too small",
                )

            # Process image if it needs resizing
            if (
                file_size_mb > self.config.max_file_size_mb
                or width > self.config.max_width
                or height > self.config.max_height
            ):
                processed_data = self._resize_image(image)
                logger.debug(
                    f"Image {image_index} resized from {width}x{height} to "
                    f"{image.size[0]}x{image.size[1]}"
                )
                return ValidationResult(
                    valid=True,
                    error_type=ImageError.NONE,
                    processed_data=processed_data,
                    message="Image resized",
                )

            # Image is acceptable as-is
            return ValidationResult(
                valid=True,
                error_type=ImageError.NONE,
                processed_data=image_data,
                message="Image valid",
            )

        except Exception as e:
            logger.error(f"Image validation error for image {image_index}: {e}")
            return ValidationResult(
                valid=False,
                error_type=ImageError.PROCESSING_ERROR,
                processed_data=None,
                message=f"Processing error: {str(e)}",
            )

    def _resize_image(self, image: PILImage) -> bytes:
        """
        Resize an image to fit within configured constraints.

        Args:
            image: PIL Image object

        Returns:
            Processed image bytes
        """
        # Resize while maintaining aspect ratio
        image.thumbnail((self.config.max_width, self.config.max_height))

        # Convert RGBA to RGB if necessary
        if image.mode == "RGBA":
            image = image.convert("RGB")

        # Save with optimization
        with BytesIO() as output:
            image.save(
                output,
                format="JPEG",
                quality=self.config.default_quality,
                optimize=True,
            )
            return output.getvalue()


class ImageFetchingService:
    """
    Service for fetching images from URLs.

    This service fetches images once and returns structured results
    that can be cached and reused throughout the processing pipeline.
    """

    def __init__(self, config: Optional[ImageConfig] = None):
        """
        Initialize the fetching service.

        Args:
            config: Image processing configuration (uses defaults if not provided)
        """
        self.config = config or ImageConfig()
        self.validator = ImageValidator(self.config)
        self.classifier = ImageClassifier()

    def fetch_images(
        self, image_urls: str, case_number: str = "UNKNOWN"
    ) -> ImageFetchResult:
        """
        Fetch and validate images from comma-separated URL string.

        This is the main entry point that should be called once during
        preprocessing to fetch all images for analysis.

        Args:
            image_urls: Comma-separated string of image URLs
            case_number: Case identifier for logging

        Returns:
            ImageFetchResult containing fetched images and any errors
        """
        logger.info(f"Fetching images for case: {case_number}")

        # Check for missing URLs
        if not image_urls or not image_urls.strip():
            logger.warning(f"No image URLs for case {case_number}")
            return ImageFetchResult(
                images=[],
                errors=["No image URLs provided"],
                error_type=ImageError.MISSING,
            )

        # Parse URLs
        url_list = [url.strip() for url in image_urls.split(",") if url.strip()]

        # Check URL count
        if len(url_list) > self.config.max_images:
            logger.warning(
                f"Too many images: {len(url_list)}, maximum is {self.config.max_images}"
            )
            return ImageFetchResult(
                images=[],
                errors=[
                    f"Too many images ({len(url_list)}). Maximum is {self.config.max_images}"
                ],
                error_type=ImageError.PROCESSING_ERROR,
            )

        # Fetch all images
        fetched_images = []
        errors = []

        for idx, url in enumerate(url_list):
            result = self._fetch_single_image(url, idx)

            if result is not None:
                fetched_images.append(result)
            else:
                errors.append(f"Failed to fetch image {idx} from {url[:50]}...")

        # Determine overall error status
        if not fetched_images:
            error_type = ImageError.URL_INACCESSIBLE if errors else ImageError.MISSING
            return ImageFetchResult(
                images=[],
                errors=errors or ["No valid images after fetching"],
                error_type=error_type,
            )

        # Check if we have all required image types
        types_found = {img.image_type for img in fetched_images}
        required_types = {"outsole", "defect", "tag"}

        if not required_types.issubset(types_found):
            missing = required_types - types_found
            return ImageFetchResult(
                images=fetched_images,
                errors=[f"Missing required image types: {', '.join(missing)}"],
                error_type=ImageError.INCOMPLETE,
            )

        logger.info(
            f"Successfully fetched {len(fetched_images)} images for case {case_number}"
        )

        return ImageFetchResult(
            images=fetched_images, errors=errors, error_type=ImageError.NONE
        )

    def _fetch_single_image(self, url: str, position: int) -> Optional[FetchedImage]:
        """
        Fetch and validate a single image.

        Args:
            url: Image URL
            position: Position in the URL list

        Returns:
            FetchedImage if successful, None otherwise
        """
        try:
            # Fetch with timeout
            response = requests.get(url, timeout=self.config.fetch_timeout_seconds)

            if response.status_code != 200:
                logger.warning(
                    f"HTTP {response.status_code} for URL at position {position}"
                )
                return None

            content_type = response.headers.get("Content-Type", "")

            # Validate content type
            if content_type not in self.config.allowed_mime_types:
                logger.warning(
                    f"Invalid content type at position {position}: {content_type}"
                )
                return None

            content = response.content
            size_bytes = len(content)
            size_mb = size_bytes / (1024 * 1024)

            # Check size limits
            if size_mb > self.config.reject_size_mb:
                logger.warning(
                    f"Image too large at position {position}: {size_mb:.1f}MB"
                )
                return None

            # Validate and process image if it's an actual image (not PDF)
            if "image" in content_type:
                validation = self.validator.validate_and_process(content, position)

                if not validation.valid:
                    logger.warning(
                        f"Image validation failed at position {position}: {validation.message}"
                    )
                    return None

                # Use processed data if available
                if validation.processed_data:
                    content = validation.processed_data
                    size_bytes = len(content)

            # Classify image type
            image_type = self.classifier.classify(url, position)

            logger.debug(
                f"Fetched image at position {position}: {content_type}, "
                f"{size_bytes // 1024}KB, type={image_type}"
            )

            return FetchedImage(
                url=url,
                content=content,
                content_type=content_type,
                size_bytes=size_bytes,
                image_type=image_type,
            )

        except requests.Timeout:
            logger.error(f"Timeout fetching image at position {position}")
            return None
        except requests.RequestException as e:
            logger.error(f"Request error fetching image at position {position}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching image at position {position}: {e}")
            return None