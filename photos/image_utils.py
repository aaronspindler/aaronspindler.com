import hashlib
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from io import BytesIO

import imagehash
import numpy as np
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageFilter
from PIL.ExifTags import GPSTAGS, TAGS

logger = logging.getLogger(__name__)


class ImageType:
    PORTRAIT = "portrait"
    GROUP = "group"
    LANDSCAPE = "landscape"
    ARCHITECTURE = "architecture"
    MACRO = "macro"
    FOOD = "food"
    DOCUMENT = "document"
    UNKNOWN = "unknown"

    CHOICES = [
        (PORTRAIT, "Portrait"),
        (GROUP, "Group Photo"),
        (LANDSCAPE, "Landscape/Nature"),
        (ARCHITECTURE, "Architecture"),
        (MACRO, "Macro/Close-up"),
        (FOOD, "Food"),
        (DOCUMENT, "Document/Text"),
        (UNKNOWN, "Unknown"),
    ]


class ImageTypeClassifier:
    """
    Classifies images into categories to optimize smart cropping strategy.
    Uses heuristics based on faces, colors, edges, and content analysis.
    """

    # Color ranges for detection (HSV format)
    SKY_BLUE_RANGE = ((90, 50, 100), (130, 255, 255))
    GREEN_RANGE = ((35, 40, 40), (85, 255, 255))
    WARM_FOOD_RANGE = ((0, 50, 50), (30, 255, 255))

    # Thresholds for classification
    PORTRAIT_FACE_RATIO = 0.03  # Single face must be at least 3% of image
    GROUP_MIN_FACES = 2
    LANDSCAPE_SKY_RATIO = 0.15  # 15% sky in upper portion
    LANDSCAPE_GREEN_RATIO = 0.20  # 20% green vegetation
    ARCHITECTURE_LINE_THRESHOLD = 50  # Number of strong lines
    FOOD_WARM_RATIO = 0.25  # 25% warm colors
    DOCUMENT_CONTRAST_THRESHOLD = 0.7  # High contrast ratio
    MACRO_BLUR_RATIO = 0.4  # 40% of edges in center

    @classmethod
    def classify(cls, img, faces=None):
        """
        Classify an image into a category.

        Args:
            img: PIL Image object (RGB mode)
            faces: Optional pre-detected faces list [(x, y, w, h), ...]

        Returns:
            str: Image type constant from ImageType class
        """
        if img.mode != "RGB":
            img = img.convert("RGB")

        width, height = img.size
        img_area = width * height

        # Get faces if not provided
        if faces is None:
            from photos.image_utils import SmartCrop

            faces = SmartCrop.detect_faces(img)

        # Check for portrait/group based on faces
        if faces:
            total_face_area = sum(w * h for x, y, w, h in faces)
            face_ratio = total_face_area / img_area

            if len(faces) >= cls.GROUP_MIN_FACES:
                return ImageType.GROUP

            if len(faces) == 1 and face_ratio >= cls.PORTRAIT_FACE_RATIO:
                largest_face = max(faces, key=lambda f: f[2] * f[3])
                face_center_y = (largest_face[1] + largest_face[3] / 2) / height
                # Portrait if face is in upper 2/3 and reasonably sized
                if face_center_y < 0.7:
                    return ImageType.PORTRAIT

        # Try OpenCV-based analysis
        try:
            import cv2

            img_array = np.array(img)
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)

            # Check for document (high contrast, mostly white/black)
            if cls._is_document(img, img_array):
                return ImageType.DOCUMENT

            # Check for architecture (strong lines)
            if cls._is_architecture(img_cv):
                return ImageType.ARCHITECTURE

            # Check for landscape (sky + vegetation)
            if cls._is_landscape(hsv, height):
                return ImageType.LANDSCAPE

            # Check for food (warm colors, centered subject)
            if cls._is_food(hsv, img_area):
                return ImageType.FOOD

            # Check for macro (sharp center, blurred edges)
            if cls._is_macro(img_array):
                return ImageType.MACRO

        except ImportError:
            pass

        return ImageType.UNKNOWN

    @classmethod
    def _is_document(cls, img, img_array):
        """Check if image is a document/text."""
        gray = img.convert("L")
        histogram = gray.histogram()
        total_pixels = sum(histogram)

        # Check bimodal distribution (peaks at dark and light)
        dark_pixels = sum(histogram[:64]) / total_pixels
        light_pixels = sum(histogram[192:]) / total_pixels

        # Documents typically have very high contrast
        if dark_pixels + light_pixels > cls.DOCUMENT_CONTRAST_THRESHOLD:
            return True

        return False

    @classmethod
    def _is_architecture(cls, img_cv):
        """Check if image contains architecture (strong lines)."""
        import cv2

        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)

        # Detect lines using Hough transform
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, threshold=100, minLineLength=min(img_cv.shape[:2]) // 10, maxLineGap=10
        )

        if lines is None:
            return False

        # Count vertical and horizontal lines
        vertical_count = 0
        horizontal_count = 0

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)

            if angle < 15 or angle > 165:  # Horizontal
                horizontal_count += 1
            elif 75 < angle < 105:  # Vertical
                vertical_count += 1

        # Architecture typically has many vertical and horizontal lines
        total_strong_lines = vertical_count + horizontal_count
        return total_strong_lines >= cls.ARCHITECTURE_LINE_THRESHOLD

    @classmethod
    def _is_landscape(cls, hsv, height):
        """Check if image is a landscape (sky in upper portion, vegetation)."""
        import cv2

        # Check upper 40% for sky
        upper_portion = hsv[: int(height * 0.4), :, :]

        # Create mask for sky blue colors
        sky_mask = cv2.inRange(upper_portion, np.array(cls.SKY_BLUE_RANGE[0]), np.array(cls.SKY_BLUE_RANGE[1]))
        sky_ratio = np.count_nonzero(sky_mask) / sky_mask.size

        # Check full image for green vegetation
        green_mask = cv2.inRange(hsv, np.array(cls.GREEN_RANGE[0]), np.array(cls.GREEN_RANGE[1]))
        green_ratio = np.count_nonzero(green_mask) / green_mask.size

        # Landscape if we have sky OR significant vegetation
        if sky_ratio >= cls.LANDSCAPE_SKY_RATIO:
            return True
        if green_ratio >= cls.LANDSCAPE_GREEN_RATIO:
            return True

        return False

    @classmethod
    def _is_food(cls, hsv, img_area):
        """Check if image is food photography (warm colors, centered)."""
        import cv2

        height, width = hsv.shape[:2]

        # Check center region for warm colors
        center_y1, center_y2 = int(height * 0.25), int(height * 0.75)
        center_x1, center_x2 = int(width * 0.25), int(width * 0.75)
        center_region = hsv[center_y1:center_y2, center_x1:center_x2]

        warm_mask = cv2.inRange(center_region, np.array(cls.WARM_FOOD_RANGE[0]), np.array(cls.WARM_FOOD_RANGE[1]))
        warm_ratio = np.count_nonzero(warm_mask) / warm_mask.size

        # Food photos typically have warm colors in the center
        return warm_ratio >= cls.FOOD_WARM_RATIO

    @classmethod
    def _is_macro(cls, img_array):
        """Check if image is macro/close-up (sharp center, blurred edges)."""
        import cv2

        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        height, width = gray.shape

        # Calculate Laplacian variance (sharpness) for center and edges
        center_y1, center_y2 = int(height * 0.3), int(height * 0.7)
        center_x1, center_x2 = int(width * 0.3), int(width * 0.7)

        center = gray[center_y1:center_y2, center_x1:center_x2]
        center_sharpness = cv2.Laplacian(center, cv2.CV_64F).var()

        # Check edge regions
        edge_regions = [
            gray[:center_y1, :],  # Top
            gray[center_y2:, :],  # Bottom
            gray[:, :center_x1],  # Left
            gray[:, center_x2:],  # Right
        ]

        edge_sharpness = np.mean(
            [cv2.Laplacian(region, cv2.CV_64F).var() for region in edge_regions if region.size > 0]
        )

        # Macro if center is significantly sharper than edges
        if edge_sharpness > 0:
            sharpness_ratio = center_sharpness / edge_sharpness
            return sharpness_ratio > 2.0

        return False

    @classmethod
    def get_crop_strategy(cls, image_type):
        """
        Get cropping strategy parameters for an image type.

        Returns:
            dict: Strategy parameters including:
                - face_weight: Weight for face detection (0-1)
                - saliency_weight: Weight for saliency detection
                - prefer_center: Whether to bias toward center
                - aspect_preference: Preferred aspect ratio adjustment
                - focal_y_bias: Vertical bias for focal point (0=top, 1=bottom)
        """
        strategies = {
            ImageType.PORTRAIT: {
                "face_weight": 0.9,
                "saliency_weight": 0.1,
                "prefer_center": False,
                "focal_y_bias": 0.35,  # Bias toward upper portion (faces)
            },
            ImageType.GROUP: {
                "face_weight": 0.8,
                "saliency_weight": 0.2,
                "prefer_center": True,
                "focal_y_bias": 0.4,
            },
            ImageType.LANDSCAPE: {
                "face_weight": 0.0,
                "saliency_weight": 0.7,
                "prefer_center": False,
                "focal_y_bias": 0.45,  # Slightly above center (horizon)
            },
            ImageType.ARCHITECTURE: {
                "face_weight": 0.0,
                "saliency_weight": 0.5,
                "prefer_center": True,
                "focal_y_bias": 0.5,  # Center for symmetry
            },
            ImageType.MACRO: {
                "face_weight": 0.0,
                "saliency_weight": 0.9,
                "prefer_center": True,
                "focal_y_bias": 0.5,
            },
            ImageType.FOOD: {
                "face_weight": 0.0,
                "saliency_weight": 0.8,
                "prefer_center": True,
                "focal_y_bias": 0.5,  # Center for table-top shots
            },
            ImageType.DOCUMENT: {
                "face_weight": 0.0,
                "saliency_weight": 0.3,
                "prefer_center": True,
                "focal_y_bias": 0.4,  # Slightly up for headers
            },
            ImageType.UNKNOWN: {
                "face_weight": 0.7,
                "saliency_weight": 0.3,
                "prefer_center": False,
                "focal_y_bias": 0.5,
            },
        }
        return strategies.get(image_type, strategies[ImageType.UNKNOWN])


@contextmanager
def reset_file_pointer(file_obj):
    """
    Context manager to automatically reset file pointer.

    Usage:
        with reset_file_pointer(image_file) as f:
            img = Image.open(f)
    """
    initial_position = file_obj.tell() if hasattr(file_obj, "tell") else 0
    try:
        yield file_obj
    finally:
        if hasattr(file_obj, "seek"):
            file_obj.seek(initial_position)


class ImageMetadataExtractor:
    """
    Extracts basic metadata from images without EXIF processing.
    """

    @staticmethod
    def extract_basic_metadata(image_file):
        """
        Extract basic metadata like dimensions and file size.

        Args:
            image_file: Django ImageField file or file-like object

        Returns:
            dict: Dictionary containing width, height, file_size, and format
        """
        with reset_file_pointer(image_file):
            img = Image.open(image_file)
            metadata = {
                "width": img.width,
                "height": img.height,
                "file_size": image_file.size if hasattr(image_file, "size") else None,
                "format": img.format,
                "mode": img.mode,
            }
            return metadata


class ExifExtractor:
    """
    Extracts and processes EXIF data from images.
    """

    @staticmethod
    def make_exif_serializable(exif_data):
        """
        Convert EXIF data to JSON-serializable format.

        Args:
            exif_data: Dictionary containing EXIF data with potentially non-serializable values

        Returns:
            dict: JSON-serializable version of the EXIF data
        """
        serializable = {}
        for key, value in exif_data.items():
            # Check for specific non-serializable types
            if isinstance(value, (tuple, bytes, bytearray)):
                serializable[key] = str(value)
            else:
                try:
                    json.dumps(value)  # Test if serializable
                    serializable[key] = value
                except (TypeError, ValueError):
                    serializable[key] = str(value)  # Convert non-serializable to string
        return serializable

    @staticmethod
    def extract_exif(image_file):
        """
        Extract EXIF data from an image file.

        Args:
            image_file: Django ImageField file or file-like object

        Returns:
            dict: Dictionary containing extracted EXIF data
        """
        try:
            image_file.seek(0)
            img = Image.open(image_file)

            exif_data = img._getexif() if hasattr(img, "_getexif") else None

            if not exif_data:
                return {}

            readable_exif = {}
            for tag_id, value in exif_data.items():
                tag = TAGS.get(tag_id, tag_id)
                readable_exif[tag] = value

            extracted_data = {
                "full_exif": readable_exif,
                "camera_make": (readable_exif.get("Make", "").strip() if "Make" in readable_exif else ""),
                "camera_model": (readable_exif.get("Model", "").strip() if "Model" in readable_exif else ""),
                "lens_model": (readable_exif.get("LensModel", "").strip() if "LensModel" in readable_exif else ""),
                "iso": readable_exif.get("ISOSpeedRatings") or readable_exif.get("ISO"),
                "date_taken": ExifExtractor._parse_datetime(
                    readable_exif.get("DateTimeOriginal") or readable_exif.get("DateTime")
                ),
            }

            focal_length = readable_exif.get("FocalLength")
            if focal_length:
                extracted_data["focal_length"] = ExifExtractor._format_focal_length(focal_length)

            aperture = readable_exif.get("FNumber") or readable_exif.get("ApertureValue")
            if aperture:
                extracted_data["aperture"] = ExifExtractor._format_aperture(aperture)

            shutter_speed = readable_exif.get("ExposureTime") or readable_exif.get("ShutterSpeedValue")
            if shutter_speed:
                extracted_data["shutter_speed"] = ExifExtractor._format_shutter_speed(shutter_speed)
            gps_info = readable_exif.get("GPSInfo")
            if gps_info:
                gps_data = ExifExtractor._extract_gps(gps_info)
                extracted_data.update(gps_data)

            return extracted_data

        except Exception as e:
            print(f"Error extracting EXIF data: {e}")
            return {}

    @staticmethod
    def _parse_datetime(datetime_str):
        """Parse EXIF datetime string to Python datetime object."""
        if not datetime_str:
            return None
        try:
            naive_dt = datetime.strptime(datetime_str, "%Y:%m:%d %H:%M:%S")  # EXIF format: 'YYYY:MM:DD HH:MM:SS'
            return timezone.make_aware(naive_dt)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _format_focal_length(focal_length):
        """Format focal length value."""
        try:
            if isinstance(focal_length, tuple):
                if focal_length[1] == 0:
                    return str(focal_length)
                value = focal_length[0] / focal_length[1]
            else:
                value = float(focal_length)

            if value == int(value):  # Format as integer if whole number
                return f"{int(value)}mm"
            else:
                return f"{value:.1f}mm"
        except Exception:
            return str(focal_length)

    @staticmethod
    def _format_aperture(aperture):
        """Format aperture value."""
        try:
            if isinstance(aperture, tuple):
                if aperture[1] == 0:
                    return str(aperture)
                value = aperture[0] / aperture[1]
            else:
                value = float(aperture)

            return f"f/{value:.1f}"
        except Exception:
            return str(aperture)

    @staticmethod
    def _format_shutter_speed(shutter_speed):
        """Format shutter speed value."""
        try:
            if isinstance(shutter_speed, tuple):
                numerator = shutter_speed[0]
                denominator = shutter_speed[1]

                if denominator == 0:
                    return str(shutter_speed)

                if numerator < denominator:  # Less than 1 second - show as fraction
                    from math import gcd

                    common = gcd(numerator, denominator)
                    return f"{numerator // common}/{denominator // common}"
                else:  # 1 second or more - show as decimal
                    value = numerator / denominator
                    if value == int(value):
                        return f"{int(value)}s"
                    else:
                        return f"{value:.1f}s"
            else:
                value = float(shutter_speed)
                if value < 1:
                    return f"1/{int(1 / value)}"  # Convert to fraction format
                else:
                    return f"{value:.1f}s"
        except Exception:
            return str(shutter_speed)

    @staticmethod
    def _extract_gps(gps_info):
        """Extract GPS coordinates from EXIF GPS info."""
        gps_data = {}

        try:
            gps_readable = {}
            for tag_id, value in gps_info.items():
                tag = GPSTAGS.get(tag_id, tag_id)
                gps_readable[tag] = value

            lat = gps_readable.get("GPSLatitude")
            lat_ref = gps_readable.get("GPSLatitudeRef")
            if lat and lat_ref:
                lat_decimal = ExifExtractor._convert_to_degrees(lat)
                if lat_ref == "S":
                    lat_decimal = -lat_decimal
                gps_data["gps_latitude"] = Decimal(str(lat_decimal))

            lon = gps_readable.get("GPSLongitude")
            lon_ref = gps_readable.get("GPSLongitudeRef")
            if lon and lon_ref:
                lon_decimal = ExifExtractor._convert_to_degrees(lon)
                if lon_ref == "W":
                    lon_decimal = -lon_decimal
                gps_data["gps_longitude"] = Decimal(str(lon_decimal))
            alt = gps_readable.get("GPSAltitude")
            alt_ref = gps_readable.get("GPSAltitudeRef")
            if alt:
                if isinstance(alt, tuple):
                    alt_value = alt[0] / alt[1] if alt[1] != 0 else 0
                else:
                    alt_value = float(alt)

                if alt_ref == 1:  # Below sea level
                    alt_value = -alt_value

                gps_data["gps_altitude"] = Decimal(str(alt_value))

        except Exception as e:
            print(f"Error extracting GPS data: {e}")

        return gps_data

    @staticmethod
    def _convert_to_degrees(value):
        """Convert GPS coordinates to decimal degrees."""
        try:
            # Format: ((degrees, 1), (minutes, 1), (seconds, divisor))
            d = value[0][0] / value[0][1] if value[0][1] != 0 else 0
            m = value[1][0] / value[1][1] if value[1][1] != 0 else 0
            s = value[2][0] / value[2][1] if value[2][1] != 0 else 0

            return d + (m / 60.0) + (s / 3600.0)
        except Exception:
            return 0


class SmartCrop:
    """
    Smart cropping functionality to find the most interesting part of an image.
    Uses face detection, saliency detection, edge detection, and entropy analysis.
    Automatically classifies images and applies type-specific cropping strategies.
    """

    # Default weight for blending face detection with saliency (0.0 = saliency only, 1.0 = face only)
    # This is overridden by image type-specific strategies
    FACE_WEIGHT = 0.7

    @staticmethod
    def _calculate_iou(box1, box2):
        """
        Calculate Intersection over Union (IoU) between two bounding boxes.

        Args:
            box1: (x, y, w, h) tuple
            box2: (x, y, w, h) tuple

        Returns:
            float: IoU value between 0 and 1
        """
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2

        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)

        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - inter_area

        if union_area == 0:
            return 0.0

        return inter_area / union_area

    @staticmethod
    def _apply_nms(faces, iou_threshold=0.4):
        """
        Apply Non-Maximum Suppression to filter overlapping face detections.

        Args:
            faces: List of (x, y, w, h) face bounding boxes
            iou_threshold: IoU threshold above which detections are considered overlapping

        Returns:
            list: Filtered list of face bounding boxes with overlapping detections removed
        """
        if len(faces) <= 1:
            return faces

        faces_list = list(faces)
        filtered = []

        while faces_list:
            current = faces_list.pop(0)
            filtered.append(current)

            remaining = []
            for face in faces_list:
                iou = SmartCrop._calculate_iou(current, face)
                if iou < iou_threshold:
                    remaining.append(face)

            faces_list = remaining

        return filtered

    @staticmethod
    def _filter_by_size(faces, img_width, img_height, min_relative_size=0.02):
        """
        Filter out faces that are too small relative to the image size.

        Args:
            faces: List of (x, y, w, h) face bounding boxes
            img_width: Image width in pixels
            img_height: Image height in pixels
            min_relative_size: Minimum face area as fraction of image area (default: 2%)

        Returns:
            list: Filtered list of face bounding boxes
        """
        if not faces:
            return []

        min_area = img_width * img_height * min_relative_size
        filtered = []

        for x, y, w, h in faces:
            face_area = w * h
            if face_area >= min_area:
                filtered.append((x, y, w, h))

        return filtered

    @staticmethod
    def detect_faces(img):
        """
        Detect faces in an image using OpenCV Haar cascades.

        Args:
            img: PIL Image object (RGB mode)

        Returns:
            list: List of face bounding boxes as (x, y, w, h) tuples, or empty list if none found
        """
        try:
            import cv2
        except ImportError:
            return []

        img_array = np.array(img)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        width, height = img.size

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

        min_size = max(30, int(min(width, height) * 0.015))

        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(min_size, min_size))

        if len(faces) == 0:
            return []

        faces = [tuple(face) for face in faces]
        initial_count = len(faces)

        faces = SmartCrop._filter_by_size(faces, width, height, min_relative_size=0.01)
        after_size_filter = len(faces)

        faces = SmartCrop._apply_nms(faces, iou_threshold=0.5)
        final_count = len(faces)

        if initial_count > 0:
            logger.debug(
                f"Face detection: {initial_count} initial detections, "
                f"{after_size_filter} after size filter, {final_count} after NMS"
            )

        return faces

    @staticmethod
    def _get_face_focal_point(faces, img_width, img_height):
        """
        Calculate the focal point from detected faces.

        Uses weighted average of face centers, with larger faces weighted more heavily.

        Args:
            faces: List of (x, y, w, h) face bounding boxes
            img_width: Image width in pixels
            img_height: Image height in pixels

        Returns:
            tuple: (x, y) as normalized coordinates (0-1), or None if no faces
        """
        if not faces:
            return None

        total_weight = 0
        weighted_x = 0
        weighted_y = 0

        for x, y, w, h in faces:
            face_area = w * h
            center_x = x + w / 2
            center_y = y + h / 2

            weighted_x += center_x * face_area
            weighted_y += center_y * face_area
            total_weight += face_area

        if total_weight == 0:
            return None

        return (weighted_x / total_weight / img_width, weighted_y / total_weight / img_height)

    @staticmethod
    def find_focal_point(img, return_saliency_map=False, return_image_type=False):
        """
        Find the focal point of an image using image type-aware detection.

        Classifies the image first, then applies type-specific cropping strategies:
        - Portrait/Group: Higher weight on face detection
        - Landscape: Focus on horizon and interesting features
        - Architecture: Center-biased with line detection awareness
        - Macro/Food: Strong saliency with center bias
        - Document: Upper-center focus for headers

        Args:
            img: PIL Image object
            return_saliency_map: If True, returns saliency_map_bytes in result
            return_image_type: If True, returns detected image_type in result

        Returns:
            tuple: Depending on flags:
                   - Default: (x, y)
                   - return_saliency_map: ((x, y), bytes or None)
                   - return_image_type: ((x, y), image_type)
                   - Both: ((x, y), bytes or None, image_type)
        """
        if img.mode != "RGB":
            img = img.convert("RGB")

        width, height = img.size

        # Detect faces first (needed for both classification and focal point)
        faces = SmartCrop.detect_faces(img)
        face_point = SmartCrop._get_face_focal_point(faces, width, height)

        if face_point is not None:
            logger.debug(f"Face detection succeeded: {len(faces)} face(s) detected, focal point: {face_point}")
        else:
            logger.debug(f"Face detection: no faces detected (checked {len(faces)} detections)")

        # Classify the image type
        image_type = ImageTypeClassifier.classify(img, faces=faces)
        strategy = ImageTypeClassifier.get_crop_strategy(image_type)
        logger.info(f"Image classified as: {image_type}, using strategy: {strategy}")

        # Get saliency-based focal point (pass faces for visualization)
        if return_saliency_map:
            saliency_point, saliency_map = SmartCrop._saliency_focal_point(img, return_map=True, faces=faces)
        else:
            saliency_point = SmartCrop._saliency_focal_point(img, faces=faces)
            saliency_map = None

        if saliency_point is not None:
            logger.debug(f"Saliency detection succeeded, focal point: {saliency_point}")
        else:
            logger.debug("Saliency detection failed or unavailable")

        # Get type-specific weights
        face_weight = strategy["face_weight"]
        focal_y_bias = strategy["focal_y_bias"]
        prefer_center = strategy["prefer_center"]

        # Calculate focal point based on image type strategy
        if face_point is not None and saliency_point is not None and face_weight > 0:
            # Blend face and saliency with type-specific weights
            x = face_weight * face_point[0] + (1 - face_weight) * saliency_point[0]
            y = face_weight * face_point[1] + (1 - face_weight) * saliency_point[1]
            focal_point = (x, y)
            logger.info(
                f"Focal point ({image_type}): blended face ({face_point}) and "
                f"saliency ({saliency_point}) with weight {face_weight}, result: {focal_point}"
            )
        elif face_point is not None and face_weight > 0:
            focal_point = face_point
            logger.info(f"Focal point ({image_type}): face detection only, result: {focal_point}")
        elif saliency_point is not None:
            focal_point = saliency_point
            # Apply center bias for certain image types
            if prefer_center:
                center_weight = 0.3
                x = (1 - center_weight) * saliency_point[0] + center_weight * 0.5
                y = (1 - center_weight) * saliency_point[1] + center_weight * focal_y_bias
                focal_point = (x, y)
                logger.info(
                    f"Focal point ({image_type}): saliency with center bias, "
                    f"original: {saliency_point}, result: {focal_point}"
                )
            else:
                logger.info(f"Focal point ({image_type}): saliency detection only, result: {focal_point}")
        else:
            # Both failed, fall back to entropy + edge detection
            edge_point = SmartCrop._edge_detection_focal_point(img)
            entropy_point = SmartCrop._entropy_focal_point(img)

            x = edge_point[0] * 0.3 + entropy_point[0] * 0.7
            # Apply type-specific vertical bias
            y = edge_point[1] * 0.3 + entropy_point[1] * 0.7
            y = y * (1 - 0.2) + focal_y_bias * 0.2  # Slight bias toward type preference
            focal_point = (x, y)
            logger.info(
                f"Focal point ({image_type}): fallback to entropy+edge detection, "
                f"edge: {edge_point}, entropy: {entropy_point}, result: {focal_point}"
            )

        # Build return value based on flags
        if return_saliency_map and return_image_type:
            return (focal_point, saliency_map, image_type)
        elif return_saliency_map:
            return (focal_point, saliency_map)
        elif return_image_type:
            return (focal_point, image_type)

        return focal_point

    @staticmethod
    def _saliency_focal_point(img, return_map=False, faces=None):
        """
        Find focal point using saliency detection (human attention modeling).

        Args:
            img: PIL Image object
            return_map: If True, returns (focal_point, saliency_map_bytes), else just focal_point
            faces: Optional list of detected face bounding boxes (x, y, w, h) for visualization

        Returns:
            tuple or None: If return_map=True: ((x, y), bytes) or (None, None)
                          If return_map=False: (x, y) or None
        """
        try:
            import cv2
        except ImportError:
            logger.debug("Saliency detection: OpenCV not available")
            return (None, None) if return_map else None

        # Check if saliency module is available (requires opencv-contrib-python)
        if not hasattr(cv2, "saliency"):
            logger.debug("Saliency detection: OpenCV saliency module not available (requires opencv-contrib-python)")
            return (None, None) if return_map else None

        # Convert PIL to OpenCV format
        img_array = np.array(img)
        if len(img_array.shape) == 3:
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_cv = img_array

        # Try fine-grained saliency first (slower but more accurate for complex images)
        saliency = cv2.saliency.StaticSaliencyFineGrained_create()
        success, saliency_map = saliency.computeSaliency(img_cv)

        if not success:
            logger.debug("Saliency detection: Fine-grained method failed, trying spectral residual")
            # Fall back to spectral residual saliency (faster, good for general cases)
            saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
            success, saliency_map = saliency.computeSaliency(img_cv)

            if not success:
                logger.debug("Saliency detection: Both methods failed")
                return (None, None) if return_map else None

        # Find center of mass of saliency map
        saliency_map = (saliency_map * 255).astype(np.uint8)

        # Apply threshold to focus on salient regions (top 20%)
        # This reduces influence of low-saliency background noise
        threshold = np.percentile(saliency_map, 80)
        saliency_map = np.where(saliency_map >= threshold, saliency_map, 0)

        height, width = saliency_map.shape

        total_weight = np.sum(saliency_map)
        if total_weight == 0:
            focal_point = (0.5, 0.5)
            if return_map:
                return (focal_point, None)
            return focal_point

        y_coords, x_coords = np.ogrid[:height, :width]
        x_center = np.sum(x_coords * saliency_map) / total_weight
        y_center = np.sum(y_coords * saliency_map) / total_weight

        focal_point = (x_center / width, y_center / height)

        if return_map:
            # Draw a red dot at the focal point for visualization
            focal_x_px = int(x_center)
            focal_y_px = int(y_center)

            # Convert grayscale to BGR for colored marker
            saliency_map_color = cv2.cvtColor(saliency_map, cv2.COLOR_GRAY2BGR)

            # Draw red circle at focal point (outer ring) - larger and thicker
            cv2.circle(saliency_map_color, (focal_x_px, focal_y_px), 25, (0, 0, 255), 3)
            # Draw red filled circle at center - larger
            cv2.circle(saliency_map_color, (focal_x_px, focal_y_px), 10, (0, 0, 255), -1)
            # Add white outline for better visibility - larger
            cv2.circle(saliency_map_color, (focal_x_px, focal_y_px), 26, (255, 255, 255), 2)
            cv2.circle(saliency_map_color, (focal_x_px, focal_y_px), 11, (255, 255, 255), 2)

            # Draw blue rectangles around detected faces
            if faces:
                for x, y, w, h in faces:
                    # Blue rectangle with white border for visibility
                    cv2.rectangle(saliency_map_color, (x, y), (x + w, y + h), (255, 255, 255), 4)
                    cv2.rectangle(saliency_map_color, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # Encode saliency map as PNG for storage
            success, buffer = cv2.imencode(".png", saliency_map_color)
            saliency_map_bytes = buffer.tobytes() if success else None
            return (focal_point, saliency_map_bytes)

        return focal_point

    @staticmethod
    def _edge_detection_focal_point(img):
        """
        Find focal point using edge detection.
        """
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edges = edges.filter(ImageFilter.GaussianBlur(radius=2))
        edge_array = np.array(edges)

        # Find center of mass of edges
        height, width = edge_array.shape
        y_coords, x_coords = np.ogrid[:height, :width]

        total_weight = np.sum(edge_array)
        if total_weight == 0:
            return (0.5, 0.5)  # Center if no edges found

        x_center = np.sum(x_coords * edge_array) / total_weight
        y_center = np.sum(y_coords * edge_array) / total_weight
        return (x_center / width, y_center / height)

    @staticmethod
    def _entropy_focal_point(img, grid_size=10):
        """
        Find focal point using entropy (information density).
        Areas with more detail/texture have higher entropy.
        """
        width, height = img.size
        cell_width = width // grid_size
        cell_height = height // grid_size

        # If image is too small for grid analysis, return center
        if cell_width < 2 or cell_height < 2:
            return (0.5, 0.5)

        max_entropy = 0
        best_x, best_y = width // 2, height // 2

        # Ensure step size is at least 1
        step_x = max(1, cell_width // 2)
        step_y = max(1, cell_height // 2)

        for y in range(0, height - cell_height, step_y):
            for x in range(0, width - cell_width, step_x):
                box = (x, y, x + cell_width, y + cell_height)
                region = img.crop(box)
                entropy = SmartCrop._calculate_entropy(region)

                if entropy > max_entropy:
                    max_entropy = entropy
                    best_x = x + cell_width // 2
                    best_y = y + cell_height // 2

        return (best_x / width, best_y / height)

    @staticmethod
    def _calculate_entropy(img):
        """
        Calculate the entropy of an image region.
        Higher entropy means more information/detail.
        """
        if img.mode != "L":
            img = img.convert("L")

        histogram = img.histogram()
        entropy = 0
        total_pixels = sum(histogram)

        for count in histogram:
            if count > 0:
                probability = count / total_pixels
                entropy -= probability * np.log2(probability)

        return entropy

    @staticmethod
    def smart_crop(img, target_width, target_height, focal_point=None):
        """
        Crop an image smartly to target dimensions, centering on the focal point.

        Args:
            img: PIL Image object
            target_width: Target width
            target_height: Target height
            focal_point: Optional (x, y) focal point as percentages (0-1)

        Returns:
            PIL Image: Cropped image
        """
        width, height = img.size
        target_aspect = target_width / target_height
        current_aspect = width / height

        if focal_point is None:
            focal_point = SmartCrop.find_focal_point(img)

        # Convert focal point from percentages to pixels
        focal_x = int(focal_point[0] * width)
        focal_y = int(focal_point[1] * height)

        if current_aspect > target_aspect:
            # Image is wider than target - crop width
            new_width = int(height * target_aspect)
            new_height = height
        else:
            # Image is taller than target - crop height
            new_width = width
            new_height = int(width / target_aspect)

        left = focal_x - new_width // 2
        top = focal_y - new_height // 2
        left = max(0, min(left, width - new_width))
        top = max(0, min(top, height - new_height))
        right = left + new_width
        bottom = top + new_height

        cropped = img.crop((left, top, right, bottom))
        cropped = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)

        return cropped


class ImageOptimizer:
    """
    Handles image optimization and resizing for different use cases.
    """

    # Define size presets for different use cases
    SIZES = {
        "preview": None,  # Full size, highly compressed for fast loading
        "thumbnail": (400, 300),  # Smart-cropped version for grid display
        # 'original' will be the untouched original
    }

    # Quality settings for JPEG compression
    QUALITY_SETTINGS = {
        "preview": 65,  # Lower quality for fast loading
        "thumbnail": 80,  # Good quality for thumbnail display
        "original": 100,  # No compression
    }

    @classmethod
    def optimize_image(
        cls,
        image_file,
        size_name="original",
        maintain_aspect_ratio=True,
        use_smart_crop=True,
        focal_point=None,
    ):
        """
        Optimize an image file for a specific size.

        Args:
            image_file: Django ImageField file or file-like object
            size_name: One of 'preview', 'thumbnail', or 'original'
            maintain_aspect_ratio: If True, maintains aspect ratio when resizing
            use_smart_crop: If True and size_name is 'thumbnail', use smart cropping
            focal_point: Optional (x, y) focal point as percentages (0-1)

        Returns:
            tuple: (ContentFile: Optimized image, focal_point: (x, y) or None)
        """
        if size_name == "original":
            image_file.seek(0)
            return (ContentFile(image_file.read()), None)
        img = Image.open(image_file)
        computed_focal_point = None

        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        original_format = img.format or "JPEG"

        if size_name in cls.SIZES and cls.SIZES[size_name]:
            target_size = cls.SIZES[size_name]

            if use_smart_crop and size_name == "thumbnail":
                if focal_point is None:
                    computed_focal_point = SmartCrop.find_focal_point(img)
                else:
                    computed_focal_point = focal_point

                img = SmartCrop.smart_crop(img, target_size[0], target_size[1], computed_focal_point)
            elif maintain_aspect_ratio:
                img.thumbnail(target_size, Image.Resampling.LANCZOS)
            else:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
        output = BytesIO()
        quality = cls.QUALITY_SETTINGS.get(size_name, 90)

        save_format = "JPEG"
        if original_format in ["PNG", "GIF", "WEBP"]:
            save_format = original_format
        save_kwargs = {
            "format": save_format,
            "optimize": True,
        }

        if save_format == "JPEG":
            save_kwargs["quality"] = quality
            save_kwargs["progressive"] = True  # Progressive JPEG for better web loading

        img.save(output, **save_kwargs)
        output.seek(0)

        return (ContentFile(output.read()), computed_focal_point)

    @classmethod
    def generate_filename(cls, photo_uuid, size_name, original_ext=".jpg"):
        """
        Generate a filename for the optimized version using UUID.

        Args:
            photo_uuid: UUID of the photo (string)
            size_name: Size variant name ('thumbnail', 'preview', etc.)
            original_ext: Original file extension

        Returns:
            str: New filename with UUID and size suffix
        """
        ext = original_ext.lower()
        if size_name != "original" and ext not in [".png", ".gif", ".webp"]:
            ext = ".jpg"  # Convert to .jpg when optimizing (except PNG/GIF/WebP)

        if size_name == "original":
            return f"{photo_uuid}{ext}"

        return f"{photo_uuid}_{size_name}{ext}"

    @classmethod
    def process_uploaded_image(cls, image_file, photo_uuid, original_ext=".jpg"):
        """
        Process an uploaded image and create all size variants.

        The image type is automatically detected and used internally to optimize
        the smart crop focal point calculation.

        Args:
            image_file: Uploaded image file
            photo_uuid: UUID of the photo for naming (string)
            original_ext: Original file extension

        Returns:
            tuple: (variants dict, focal_point tuple or None, saliency_map_bytes or None)
        """
        variants = {}
        focal_point = None
        saliency_map_bytes = None

        # Compute focal point and saliency map once before processing variants
        # Image type is detected internally by find_focal_point to optimize cropping
        image_file.seek(0)
        img = Image.open(image_file)
        if img.mode != "RGB":
            img = img.convert("RGB")
        focal_point, saliency_map_bytes = SmartCrop.find_focal_point(img, return_saliency_map=True)

        logger.info(f"Processing image {photo_uuid}: focal_point={focal_point}")

        for size_name in ["preview", "thumbnail"]:
            image_file.seek(0)
            optimized, _ = cls.optimize_image(image_file, size_name, focal_point=focal_point)

            variant_filename = cls.generate_filename(photo_uuid, size_name, original_ext)
            optimized.name = variant_filename
            variants[size_name] = optimized

        return (variants, focal_point, saliency_map_bytes)

    @classmethod
    def compute_saliency_map(cls, image_file):
        """
        Compute and return the saliency map for debugging/visualization.

        Args:
            image_file: Django ImageField file or file-like object

        Returns:
            bytes or None: PNG-encoded saliency map bytes, or None if computation fails
        """
        import logging

        logger = logging.getLogger(__name__)

        try:
            image_file.seek(0)
            img = Image.open(image_file)

            if img.mode != "RGB":
                img = img.convert("RGB")

            _, saliency_map_bytes = SmartCrop.find_focal_point(img, return_saliency_map=True)

            if saliency_map_bytes is None:
                logger.warning(
                    "Saliency map computation returned None - OpenCV may not be available or saliency detection failed"
                )
                return None

            logger.debug(f"Successfully computed saliency map ({len(saliency_map_bytes)} bytes)")
            return saliency_map_bytes
        except Exception as e:
            logger.error(f"Error computing saliency map: {e}", exc_info=True)
            return None


class DuplicateDetector:
    """
    Handles duplicate image detection using various hashing methods.
    """

    @staticmethod
    def compute_and_store_hashes(image_file):
        """
        Compute both file and perceptual hashes in one operation.

        Args:
            image_file: Django ImageField file or file-like object

        Returns:
            dict: Dictionary containing 'file_hash' and 'perceptual_hash'
        """
        return {
            "file_hash": DuplicateDetector.compute_file_hash(image_file),
            "perceptual_hash": DuplicateDetector.compute_perceptual_hash(image_file),
        }

    @staticmethod
    def compute_file_hash(image_file, algorithm="sha256"):
        """
        Compute cryptographic hash of image file for exact duplicate detection.

        Args:
            image_file: Django ImageField file or file-like object
            algorithm: Hash algorithm to use ('md5', 'sha1', 'sha256')

        Returns:
            str: Hexadecimal hash string
        """
        try:
            if algorithm == "md5":
                hasher = hashlib.md5(usedforsecurity=False)  # File checksums, not crypto
            elif algorithm == "sha1":
                hasher = hashlib.sha1(usedforsecurity=False)  # File checksums, not crypto
            else:  # Default to sha256
                hasher = hashlib.sha256()

            image_file.seek(0)

            # Read in 8KB chunks for memory efficiency with large files
            for chunk in iter(lambda: image_file.read(8192), b""):
                hasher.update(chunk)

            image_file.seek(0)

            return hasher.hexdigest()
        except Exception as e:
            print(f"Error computing file hash: {e}")
            return None

    @staticmethod
    def compute_perceptual_hash(image_file, hash_size=16):
        """
        Compute perceptual hash for similar image detection.
        This can detect images that are visually similar even if they've been:
        - Resized
        - Compressed differently
        - Slightly color-adjusted
        - Had minor edits

        Args:
            image_file: Django ImageField file or file-like object
            hash_size: Size of the hash (higher = more precise, but less tolerant to changes)

        Returns:
            str: Hexadecimal perceptual hash string
        """
        try:
            image_file.seek(0)
            img = Image.open(image_file)

            if img.mode not in ("RGB", "L"):
                if img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert("RGB")

            # Average hash algorithm - good balance of speed and accuracy
            phash = imagehash.average_hash(img, hash_size=hash_size)
            image_file.seek(0)

            return str(phash)
        except Exception as e:
            print(f"Error computing perceptual hash: {e}")
            return None

    @staticmethod
    def compute_multiple_hashes(image_file):
        """
        Compute multiple types of perceptual hashes for comprehensive comparison.

        Args:
            image_file: Django ImageField file or file-like object

        Returns:
            dict: Dictionary containing different hash types
        """
        try:
            image_file.seek(0)
            img = Image.open(image_file)

            if img.mode not in ("RGB", "L"):
                if img.mode == "RGBA":
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    img = background
                else:
                    img = img.convert("RGB")

            # Multiple hash types for comprehensive comparison
            hashes = {
                "average": str(imagehash.average_hash(img)),
                "perceptual": str(imagehash.phash(img)),
                "difference": str(imagehash.dhash(img)),
                "wavelet": str(imagehash.whash(img)),
            }

            image_file.seek(0)

            return hashes
        except Exception as e:
            print(f"Error computing multiple hashes: {e}")
            return {}

    @staticmethod
    def compare_hashes(hash1, hash2, threshold=5):
        """
        Compare two perceptual hashes to determine similarity.

        Args:
            hash1: First perceptual hash (string)
            hash2: Second perceptual hash (string)
            threshold: Maximum Hamming distance for considering images similar
                      (lower = more strict, typical range: 0-10)

        Returns:
            tuple: (is_similar: bool, distance: int)
        """
        try:
            h1 = imagehash.hex_to_hash(hash1)
            h2 = imagehash.hex_to_hash(hash2)
            distance = h1 - h2  # Hamming distance
            is_similar = distance <= threshold

            return is_similar, distance
        except Exception as e:
            print(f"Error comparing hashes: {e}")
            return False, float("inf")

    @staticmethod
    def find_duplicates(image_file, existing_photos_queryset, exact_match_only=False):
        """
        Find duplicate or similar images in the database.

        Args:
            image_file: Image file to check for duplicates
            existing_photos_queryset: QuerySet of Photo objects to check against
            exact_match_only: If True, only check for exact file duplicates

        Returns:
            dict: {
                'exact_duplicates': [list of Photo objects with identical file hash],
                'similar_images': [list of (Photo, similarity_score) tuples],
                'file_hash': computed file hash of the input image,
                'perceptual_hash': computed perceptual hash of the input image
            }
        """
        result = {
            "exact_duplicates": [],
            "similar_images": [],
            "file_hash": None,
            "perceptual_hash": None,
        }

        try:
            file_hash = DuplicateDetector.compute_file_hash(image_file)
            result["file_hash"] = file_hash

            if not exact_match_only:
                perceptual_hash = DuplicateDetector.compute_perceptual_hash(image_file)
                result["perceptual_hash"] = perceptual_hash

            if file_hash:
                exact_matches = existing_photos_queryset.filter(file_hash=file_hash)
                result["exact_duplicates"] = list(exact_matches)

            if not exact_match_only and perceptual_hash:
                photos_with_hashes = existing_photos_queryset.exclude(perceptual_hash__isnull=True).exclude(
                    perceptual_hash=""
                )

                for photo in photos_with_hashes:
                    is_similar, distance = DuplicateDetector.compare_hashes(
                        perceptual_hash, photo.perceptual_hash, threshold=5
                    )

                    if is_similar and photo not in result["exact_duplicates"]:
                        result["similar_images"].append((photo, distance))

                # Sort by similarity score (lower distance = more similar)
                result["similar_images"].sort(key=lambda x: x[1])

        except Exception as e:
            print(f"Error finding duplicates: {e}")

        return result
