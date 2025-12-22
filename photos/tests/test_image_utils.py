import gc
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from unittest.mock import Mock, patch

from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image

from photos.image_utils import (
    DuplicateDetector,
    ExifExtractor,
    ImageMetadataExtractor,
    ImageOptimizer,
    SmartCrop,
    reset_file_pointer,
)


class TestUtilityFunctions(TestCase):
    def test_reset_file_pointer_context_manager(self):
        content = b"Test content for file pointer"
        file_obj = BytesIO(content)

        file_obj.seek(5)
        initial_pos = file_obj.tell()
        self.assertEqual(initial_pos, 5)

        with reset_file_pointer(file_obj) as f:
            f.seek(10)
            self.assertEqual(f.tell(), 10)

        self.assertEqual(file_obj.tell(), 5)


class ImageMetadataExtractorTestCase(TestCase):
    def tearDown(self):
        gc.collect()

    def _create_test_image(self, size=(10, 10), format="JPEG", mode="RGB"):
        img = Image.new(mode, size, color="blue")
        img_io = BytesIO()
        img.save(img_io, format=format, quality=50)
        img_io.seek(0)
        return img_io

    def test_extract_basic_metadata(self):
        test_image = self._create_test_image(size=(20, 10))
        test_image.size = 1024  # Set file size attribute

        metadata = ImageMetadataExtractor.extract_basic_metadata(test_image)

        self.assertEqual(metadata["width"], 20)
        self.assertEqual(metadata["height"], 10)
        self.assertEqual(metadata["file_size"], 1024)
        self.assertEqual(metadata["format"], "JPEG")
        self.assertEqual(metadata["mode"], "RGB")

    def test_extract_metadata_png(self):
        test_image = self._create_test_image(size=(15, 10), format="PNG")
        test_image.size = 512

        metadata = ImageMetadataExtractor.extract_basic_metadata(test_image)

        self.assertEqual(metadata["width"], 15)
        self.assertEqual(metadata["height"], 10)
        self.assertEqual(metadata["format"], "PNG")

    def test_extract_metadata_no_file_size(self):
        test_image = self._create_test_image()

        metadata = ImageMetadataExtractor.extract_basic_metadata(test_image)

        self.assertIsNone(metadata["file_size"])
        self.assertIn("width", metadata)
        self.assertIn("height", metadata)


class ExifExtractorTestCase(TestCase):
    def tearDown(self):
        gc.collect()

    def test_make_exif_serializable(self):
        exif_data = {
            "Make": "Canon",
            "Model": "EOS R5",
            "DateTimeOriginal": "2024:01:15 14:30:00",
            "FNumber": (28, 10),  # Non-serializable tuple
            "ExposureTime": (1, 250),  # Non-serializable tuple
            "ISOSpeedRatings": 400,
            "Binary": bytes([0x01, 0x02, 0x03]),  # Non-serializable bytes
        }

        serializable = ExifExtractor.make_exif_serializable(exif_data)

        import json

        json.dumps(serializable)  # Should not raise error

        self.assertEqual(serializable["Make"], "Canon")
        self.assertEqual(serializable["Model"], "EOS R5")
        self.assertEqual(serializable["ISOSpeedRatings"], 400)
        # Non-serializable values should be converted to strings
        self.assertIsInstance(serializable["FNumber"], str)
        self.assertIsInstance(serializable["Binary"], str)

    @patch("PIL.Image.open")
    def test_extract_exif_full_data(self, mock_open):
        mock_img = Mock()
        mock_exif_data = {
            271: "Canon",  # Make
            272: "EOS R5",  # Model
            42036: "RF 24-70mm F2.8L IS USM",  # LensModel
            33437: (28, 10),  # FNumber
            33434: (1, 250),  # ExposureTime
            37377: (8, 1),  # ShutterSpeedValue
            37378: (28, 10),  # ApertureValue
            37386: (50, 1),  # FocalLength
            34855: 400,  # ISOSpeedRatings
            36867: "2024:01:15 14:30:00",  # DateTimeOriginal
            36868: "2024:01:15 14:30:00",  # DateTimeDigitized
            306: "2024:01:15 14:30:00",  # DateTime
            34853: {
                1: "N",  # GPSLatitudeRef
                2: ((40, 1), (42, 1), (46, 1)),  # GPSLatitude
                3: "W",  # GPSLongitudeRef
                4: ((74, 1), (0, 1), (23, 1)),  # GPSLongitude
                5: 0,  # GPSAltitudeRef (above sea level)
                6: (100, 1),  # GPSAltitude
            },
        }
        mock_img._getexif.return_value = mock_exif_data
        mock_open.return_value = mock_img

        mock_file = Mock()
        mock_file.seek = Mock()

        result = ExifExtractor.extract_exif(mock_file)

        self.assertEqual(result["camera_make"], "Canon")
        self.assertEqual(result["camera_model"], "EOS R5")
        self.assertEqual(result["lens_model"], "RF 24-70mm F2.8L IS USM")
        self.assertEqual(result["aperture"], "f/2.8")
        self.assertEqual(result["shutter_speed"], "1/250")
        self.assertEqual(result["focal_length"], "50mm")
        self.assertEqual(result["iso"], 400)
        self.assertIsNotNone(result["date_taken"])
        self.assertIsNotNone(result["gps_latitude"])
        self.assertIsNotNone(result["gps_longitude"])
        self.assertIsNotNone(result["gps_altitude"])

    def test_parse_datetime(self):
        dt = ExifExtractor._parse_datetime("2024:03:15 14:30:00")
        expected = timezone.make_aware(datetime(2024, 3, 15, 14, 30, 0))
        self.assertEqual(dt, expected)

        # Invalid format
        dt = ExifExtractor._parse_datetime("2024-03-15 14:30:00")
        self.assertIsNone(dt)

        dt = ExifExtractor._parse_datetime(None)
        self.assertIsNone(dt)

        dt = ExifExtractor._parse_datetime("")
        self.assertIsNone(dt)

    def test_format_focal_length(self):
        # Tuple format (common in EXIF)
        self.assertEqual(ExifExtractor._format_focal_length((50, 1)), "50mm")
        self.assertEqual(ExifExtractor._format_focal_length((85, 1)), "85mm")
        self.assertEqual(ExifExtractor._format_focal_length((35, 2)), "17.5mm")

        # Float format
        self.assertEqual(ExifExtractor._format_focal_length(50.0), "50mm")
        self.assertEqual(ExifExtractor._format_focal_length(24.5), "24.5mm")

        self.assertEqual(ExifExtractor._format_focal_length((50, 0)), "(50, 0)")

    def test_format_aperture(self):
        # Tuple format
        self.assertEqual(ExifExtractor._format_aperture((28, 10)), "f/2.8")
        self.assertEqual(ExifExtractor._format_aperture((40, 10)), "f/4.0")
        self.assertEqual(ExifExtractor._format_aperture((18, 10)), "f/1.8")

        # Float format
        self.assertEqual(ExifExtractor._format_aperture(2.8), "f/2.8")
        self.assertEqual(ExifExtractor._format_aperture(1.4), "f/1.4")

        self.assertEqual(ExifExtractor._format_aperture((28, 0)), "(28, 0)")

    def test_format_shutter_speed(self):
        self.assertEqual(ExifExtractor._format_shutter_speed((1, 250)), "1/250")
        self.assertEqual(ExifExtractor._format_shutter_speed((1, 1000)), "1/1000")
        self.assertEqual(ExifExtractor._format_shutter_speed((1, 60)), "1/60")

        self.assertEqual(ExifExtractor._format_shutter_speed((2, 1)), "2s")
        self.assertEqual(ExifExtractor._format_shutter_speed((5, 2)), "2.5s")

        # Float format
        self.assertEqual(ExifExtractor._format_shutter_speed(0.004), "1/250")
        self.assertEqual(ExifExtractor._format_shutter_speed(2.0), "2.0s")

        self.assertEqual(ExifExtractor._format_shutter_speed((1, 0)), "(1, 0)")

    def test_convert_to_degrees(self):
        gps_data = ((40, 1), (42, 1), (46, 1))
        degrees = ExifExtractor._convert_to_degrees(gps_data)
        self.assertAlmostEqual(degrees, 40.712778, places=5)

        gps_data = ((45, 1), (30, 1), (0, 1))
        degrees = ExifExtractor._convert_to_degrees(gps_data)
        self.assertAlmostEqual(degrees, 45.5, places=5)

        gps_data = ((90, 2), (60, 2), (3600, 100))
        degrees = ExifExtractor._convert_to_degrees(gps_data)
        self.assertAlmostEqual(degrees, 45.51, places=2)

    def test_extract_gps(self):
        gps_info = {
            1: "N",  # GPSLatitudeRef
            2: ((40, 1), (42, 1), (46, 1)),  # GPSLatitude
            3: "W",  # GPSLongitudeRef
            4: ((74, 1), (0, 1), (23, 1)),  # GPSLongitude
            5: 0,  # GPSAltitudeRef (0 = above sea level)
            6: (100, 1),  # GPSAltitude
        }

        gps_data = ExifExtractor._extract_gps(gps_info)

        self.assertAlmostEqual(float(gps_data["gps_latitude"]), 40.712778, places=5)

        self.assertAlmostEqual(float(gps_data["gps_longitude"]), -74.006389, places=5)

        self.assertEqual(gps_data["gps_altitude"], Decimal("100"))

    def test_extract_gps_south_east(self):
        gps_info = {
            1: "S",  # GPSLatitudeRef
            2: ((33, 1), (51, 1), (0, 1)),  # GPSLatitude (Sydney)
            3: "E",  # GPSLongitudeRef
            4: ((151, 1), (12, 1), (0, 1)),  # GPSLongitude (Sydney)
            5: 1,  # GPSAltitudeRef (1 = below sea level)
            6: (50, 1),  # GPSAltitude
        }

        gps_data = ExifExtractor._extract_gps(gps_info)

        self.assertLess(float(gps_data["gps_latitude"]), 0)

        self.assertGreater(float(gps_data["gps_longitude"]), 0)

        self.assertEqual(gps_data["gps_altitude"], Decimal("-50"))


class SmartCropTestCase(TestCase):
    def _create_test_image_with_pattern(self):
        img = Image.new("RGB", (200, 200), color="white")
        for x in range(100, 200):
            for y in range(100, 200):
                if (x + y) % 10 < 5:
                    img.putpixel((x, y), (0, 0, 0))
                else:
                    img.putpixel((x, y), (255, 255, 255))
        return img

    def test_find_focal_point(self):
        img = self._create_test_image_with_pattern()

        focal_point = SmartCrop.find_focal_point(img)

        self.assertIsInstance(focal_point, tuple)
        self.assertEqual(len(focal_point), 2)
        self.assertGreaterEqual(focal_point[0], 0.0)
        self.assertLessEqual(focal_point[0], 1.0)
        self.assertGreaterEqual(focal_point[1], 0.0)
        self.assertLessEqual(focal_point[1], 1.0)

    def test_saliency_focal_point(self):
        img = Image.new("RGB", (200, 200), color=(240, 240, 240))
        for x in range(50, 100):
            for y in range(50, 100):
                if ((x - 75) ** 2 + (y - 75) ** 2) < 400:  # Circle radius ~20
                    img.putpixel((x, y), (255, 0, 0))

        focal_point = SmartCrop._saliency_focal_point(img)

        if focal_point is not None:
            self.assertIsInstance(focal_point, tuple)
            self.assertEqual(len(focal_point), 2)
            self.assertGreaterEqual(focal_point[0], 0.0)
            self.assertLessEqual(focal_point[0], 1.0)
            self.assertGreaterEqual(focal_point[1], 0.0)
            self.assertLessEqual(focal_point[1], 1.0)

    def test_smart_crop_landscape(self):
        img = Image.new("RGB", (300, 200), color="blue")

        cropped = SmartCrop.smart_crop(img, 100, 100, focal_point=(0.7, 0.3))

        self.assertEqual(cropped.size, (100, 100))

    def test_smart_crop_portrait(self):
        img = Image.new("RGB", (200, 300), color="green")

        cropped = SmartCrop.smart_crop(img, 200, 100, focal_point=(0.5, 0.8))

        self.assertEqual(cropped.size, (200, 100))

    def test_smart_crop_auto_focal_point(self):
        img = self._create_test_image_with_pattern()

        cropped = SmartCrop.smart_crop(img, 50, 50)

        self.assertEqual(cropped.size, (50, 50))

    def test_smart_crop_edge_cases(self):
        img = Image.new("RGB", (200, 200), color="red")

        cropped1 = SmartCrop.smart_crop(img, 100, 100, focal_point=(0, 0))
        cropped2 = SmartCrop.smart_crop(img, 100, 100, focal_point=(1, 1))

        self.assertEqual(cropped1.size, (100, 100))
        self.assertEqual(cropped2.size, (100, 100))


class ImageOptimizerTestCase(TestCase):
    def _create_test_image_file(self, size=(200, 200), format="JPEG"):
        img = Image.new("RGB", size, color="yellow")
        img_io = BytesIO()
        img.save(img_io, format=format)
        img_io.seek(0)
        return img_io

    def test_optimize_image_original(self):
        test_file = self._create_test_image_file()
        original_content = test_file.read()
        test_file.seek(0)

        result, focal_point = ImageOptimizer.optimize_image(test_file, "original")

        self.assertEqual(result.read(), original_content)
        self.assertIsNone(focal_point)

    @patch("photos.image_utils.SmartCrop.find_focal_point")
    @patch("photos.image_utils.SmartCrop.smart_crop")
    def test_optimize_image_thumbnail_with_smart_crop(self, mock_smart_crop, mock_find_focal):
        test_file = self._create_test_image_file(size=(2000, 1500))

        mock_find_focal.return_value = (0.6, 0.4)
        mock_cropped = Image.new("RGB", (400, 300))
        mock_smart_crop.return_value = mock_cropped

        result, focal_point = ImageOptimizer.optimize_image(test_file, "thumbnail", use_smart_crop=True)

        mock_find_focal.assert_called_once()
        mock_smart_crop.assert_called_once()
        self.assertEqual(focal_point, (0.6, 0.4))

    def test_optimize_image_png_preservation(self):
        test_file = self._create_test_image_file(format="PNG")

        result, _ = ImageOptimizer.optimize_image(test_file, "preview")

        img = Image.open(result)
        self.assertEqual(img.format, "PNG")

    def test_optimize_image_rgba_conversion(self):
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        img_io = BytesIO()
        img.save(img_io, format="PNG")
        img_io.seek(0)

        result, _ = ImageOptimizer.optimize_image(img_io, "preview")

        # Should be converted to RGB JPEG
        img_result = Image.open(result)
        self.assertEqual(img_result.mode, "RGB")

    def test_generate_filename(self):
        self.assertEqual(ImageOptimizer.generate_filename("test-uuid", "original", ".png"), "test-uuid.png")

        # Preview/thumbnail convert to jpg (except PNG/GIF/WebP)
        self.assertEqual(
            ImageOptimizer.generate_filename("test-uuid", "preview", ".tiff"),
            "test-uuid_preview.jpg",
        )
        self.assertEqual(
            ImageOptimizer.generate_filename("test-uuid", "thumbnail", ".bmp"),
            "test-uuid_thumbnail.jpg",
        )

        self.assertEqual(
            ImageOptimizer.generate_filename("test-uuid", "preview", ".png"),
            "test-uuid_preview.png",
        )
        self.assertEqual(
            ImageOptimizer.generate_filename("test-uuid", "thumbnail", ".gif"),
            "test-uuid_thumbnail.gif",
        )
        self.assertEqual(
            ImageOptimizer.generate_filename("test-uuid", "preview", ".webp"),
            "test-uuid_preview.webp",
        )

    @patch("photos.image_utils.ImageOptimizer.optimize_image")
    def test_process_uploaded_image(self, mock_optimize):
        test_file = self._create_test_image_file()
        test_uuid = "test-uuid-123"

        mock_preview = ContentFile(b"preview_content")
        mock_preview.name = f"{test_uuid}_preview.jpg"
        mock_thumbnail = ContentFile(b"thumbnail_content")
        mock_thumbnail.name = f"{test_uuid}_thumbnail.jpg"

        mock_optimize.side_effect = [
            (mock_preview, (0.5, 0.5)),  # preview call
            (mock_thumbnail, None),  # thumbnail call (uses cached focal point)
        ]

        variants, focal_point, saliency_map_bytes = ImageOptimizer.process_uploaded_image(test_file, test_uuid)

        self.assertIn("preview", variants)
        self.assertIn("thumbnail", variants)
        self.assertEqual(variants["preview"].name, f"{test_uuid}_preview.jpg")
        self.assertEqual(variants["thumbnail"].name, f"{test_uuid}_thumbnail.jpg")
        self.assertEqual(focal_point, (0.5, 0.5))

        self.assertEqual(mock_optimize.call_count, 2)


class DuplicateDetectorTestCase(TestCase):
    def _create_test_image_file(self, content=b"test_content"):
        file_obj = BytesIO(content)
        return file_obj

    def test_compute_file_hash_sha256(self):
        test_file = self._create_test_image_file(b"Hello World!")

        hash_value = DuplicateDetector.compute_file_hash(test_file)

        expected_hash = "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"
        self.assertEqual(hash_value, expected_hash)

    def test_compute_file_hash_md5(self):
        test_file = self._create_test_image_file(b"Test content")

        hash_value = DuplicateDetector.compute_file_hash(test_file, algorithm="md5")

        self.assertIsNotNone(hash_value)
        self.assertEqual(len(hash_value), 32)  # MD5 hash is 32 hex chars

    def test_compute_file_hash_large_file(self):
        large_content = b"X" * 10240
        test_file = self._create_test_image_file(large_content)

        hash_value = DuplicateDetector.compute_file_hash(test_file)

        self.assertIsNotNone(hash_value)
        self.assertEqual(len(hash_value), 64)  # SHA-256 hash is 64 hex chars

        self.assertEqual(test_file.tell(), 0)

    @patch("PIL.Image.open")
    def test_compute_perceptual_hash(self, mock_open):
        mock_img = Mock(spec=Image.Image)
        mock_img.mode = "RGB"
        mock_img.size = (100, 100)
        mock_open.return_value = mock_img

        with patch("imagehash.average_hash") as mock_hash:
            mock_hash_obj = Mock()
            mock_hash_obj.__str__ = Mock(return_value="abcdef1234567890")
            mock_hash.return_value = mock_hash_obj

            test_file = BytesIO(b"image_data")
            hash_value = DuplicateDetector.compute_perceptual_hash(test_file)

            self.assertEqual(hash_value, "abcdef1234567890")
            mock_hash.assert_called_once_with(mock_img, hash_size=16)

    @patch("PIL.Image.open")
    def test_compute_perceptual_hash_rgba_conversion(self, mock_open):
        mock_img = Mock(spec=Image.Image)
        mock_img.mode = "RGBA"
        mock_img.size = (100, 100)
        mock_img.split.return_value = [Mock(), Mock(), Mock(), Mock()]  # RGBA channels
        mock_open.return_value = mock_img

        with patch("PIL.Image.new") as mock_new:
            mock_background = Mock(spec=Image.Image)
            mock_background.paste = Mock()
            mock_new.return_value = mock_background

            with patch("imagehash.average_hash") as mock_hash:
                mock_hash.return_value = Mock(__str__=Mock(return_value="hash123"))

                test_file = BytesIO(b"image_data")
                DuplicateDetector.compute_perceptual_hash(test_file)

                # Verify RGBA was converted
                mock_new.assert_called_once_with("RGB", (100, 100), (255, 255, 255))
                mock_background.paste.assert_called_once()

    @patch("PIL.Image.open")
    def test_compute_multiple_hashes(self, mock_open):
        mock_img = Mock(spec=Image.Image)
        mock_img.mode = "RGB"
        mock_open.return_value = mock_img

        with patch("imagehash.average_hash") as mock_avg:
            with patch("imagehash.phash") as mock_phash:
                with patch("imagehash.dhash") as mock_dhash:
                    with patch("imagehash.whash") as mock_whash:
                        mock_avg.return_value = Mock(__str__=Mock(return_value="avg123"))
                        mock_phash.return_value = Mock(__str__=Mock(return_value="phash456"))
                        mock_dhash.return_value = Mock(__str__=Mock(return_value="dhash789"))
                        mock_whash.return_value = Mock(__str__=Mock(return_value="whash000"))

                        test_file = BytesIO(b"image_data")
                        hashes = DuplicateDetector.compute_multiple_hashes(test_file)

                        self.assertEqual(hashes["average"], "avg123")
                        self.assertEqual(hashes["perceptual"], "phash456")
                        self.assertEqual(hashes["difference"], "dhash789")
                        self.assertEqual(hashes["wavelet"], "whash000")

    def test_compare_hashes(self):
        with patch("imagehash.hex_to_hash") as mock_hex:
            hash1_obj = Mock()
            hash2_obj = Mock()
            hash1_obj.__sub__ = Mock(return_value=3)  # Distance of 3
            mock_hex.side_effect = [hash1_obj, hash2_obj]

            is_similar, distance = DuplicateDetector.compare_hashes("hash1", "hash2", threshold=5)

            self.assertTrue(is_similar)
            self.assertEqual(distance, 3)

    def test_compare_hashes_not_similar(self):
        with patch("imagehash.hex_to_hash") as mock_hex:
            hash1_obj = Mock()
            hash2_obj = Mock()
            hash1_obj.__sub__ = Mock(return_value=10)  # Distance of 10
            mock_hex.side_effect = [hash1_obj, hash2_obj]

            is_similar, distance = DuplicateDetector.compare_hashes("hash1", "hash2", threshold=5)

            self.assertFalse(is_similar)
            self.assertEqual(distance, 10)

    @patch("photos.image_utils.DuplicateDetector.compute_perceptual_hash")
    @patch("photos.image_utils.DuplicateDetector.compute_file_hash")
    def test_find_duplicates_exact_match(self, mock_file_hash, mock_perceptual_hash):
        from photos.models import Photo

        existing1 = Photo.objects.create(file_hash="hash123", perceptual_hash="phash1")
        Photo.objects.create(file_hash="hash456", perceptual_hash="phash2")

        mock_file_hash.return_value = "hash123"  # Matches existing1
        mock_perceptual_hash.return_value = "phash_new"

        test_file = BytesIO(b"test_image")
        result = DuplicateDetector.find_duplicates(test_file, Photo.objects.all(), exact_match_only=False)

        self.assertEqual(len(result["exact_duplicates"]), 1)
        self.assertEqual(result["exact_duplicates"][0], existing1)
        self.assertEqual(result["file_hash"], "hash123")

    @patch("photos.image_utils.DuplicateDetector.compare_hashes")
    @patch("photos.image_utils.DuplicateDetector.compute_perceptual_hash")
    @patch("photos.image_utils.DuplicateDetector.compute_file_hash")
    def test_find_duplicates_similar_images(self, mock_file_hash, mock_perceptual_hash, mock_compare):
        from photos.models import Photo

        existing1 = Photo.objects.create(file_hash="hash1", perceptual_hash="phash1")
        Photo.objects.create(file_hash="hash2", perceptual_hash="phash2")

        mock_file_hash.return_value = "hash_new"  # No exact match
        mock_perceptual_hash.return_value = "phash_new"

        def compare_side_effect(hash1, hash2, threshold):
            if hash2 == "phash1":
                return True, 3  # Similar to existing1
            elif hash2 == "phash2":
                return False, 10  # Not similar to existing2
            return False, 100

        mock_compare.side_effect = compare_side_effect

        test_file = BytesIO(b"test_image")
        result = DuplicateDetector.find_duplicates(test_file, Photo.objects.all(), exact_match_only=False)

        self.assertEqual(len(result["exact_duplicates"]), 0)

        self.assertEqual(len(result["similar_images"]), 1)
        self.assertEqual(result["similar_images"][0][0], existing1)
        self.assertEqual(result["similar_images"][0][1], 3)  # Distance

    @patch("photos.image_utils.DuplicateDetector.compute_file_hash")
    def test_find_duplicates_exact_only(self, mock_file_hash):
        from photos.models import Photo

        Photo.objects.create(file_hash="hash123", perceptual_hash="phash")

        mock_file_hash.return_value = "hash456"  # No match

        test_file = BytesIO(b"test_image")
        result = DuplicateDetector.find_duplicates(test_file, Photo.objects.all(), exact_match_only=True)

        # Should not compute perceptual hash
        self.assertIsNone(result["perceptual_hash"])
        self.assertEqual(len(result["exact_duplicates"]), 0)
        self.assertEqual(len(result["similar_images"]), 0)

    @patch("photos.image_utils.DuplicateDetector.compute_perceptual_hash")
    @patch("photos.image_utils.DuplicateDetector.compute_file_hash")
    def test_compute_and_store_hashes(self, mock_file_hash, mock_perceptual_hash):
        mock_file_hash.return_value = "file_hash_123"
        mock_perceptual_hash.return_value = "perceptual_hash_456"

        test_file = BytesIO(b"test_image")
        result = DuplicateDetector.compute_and_store_hashes(test_file)

        self.assertEqual(result["file_hash"], "file_hash_123")
        self.assertEqual(result["perceptual_hash"], "perceptual_hash_456")
