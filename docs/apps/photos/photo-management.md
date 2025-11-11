# Photo Management System

## Overview

The photo management system provides comprehensive photo organization, automatic multi-resolution image generation, EXIF metadata extraction, and album management with downloadable zip files.

## Features

- **Multi-Resolution Images**: Automatic generation of 5 optimized sizes (thumbnail, small, medium, large, original)
- **EXIF Metadata Extraction**: Camera, lens, GPS, exposure settings, and more
- **WebP Support**: Modern image format with better compression
- **Album Management**: Organize photos into public or private albums
- **Downloadable Albums**: Generate zip files for bulk downloads
- **Duplicate Detection**: Perceptual hashing to identify similar photos
- **Full-Text Search**: Search photos and albums by title, description, location
- **S3 Storage**: Cloud storage support for scalability
- **Lazy Loading**: Responsive image loading with srcset

## Photo Model

### Fields

**Core Fields**:
- `title`: Photo title (max 200 characters)
- `description`: Detailed description (optional)
- `taken_at`: Date/time photo was taken
- `uploaded_at`: Upload timestamp (auto)

**Image Files**:
- `original_image`: Original uploaded image
- `large_image`: 1200px width
- `medium_image`: 800px width
- `small_image`: 400px width
- `thumbnail_image`: 150x150px (square crop)

**EXIF Metadata**:
- `camera_make`: Camera manufacturer
- `camera_model`: Camera model
- `lens_make`: Lens manufacturer
- `lens_model`: Lens model
- `focal_length`: Focal length in mm
- `aperture`: F-stop value
- `shutter_speed`: Exposure time
- `iso`: ISO sensitivity
- `gps_latitude`: GPS latitude
- `gps_longitude`: GPS longitude
- `gps_altitude`: GPS altitude in meters

**Additional Fields**:
- `location`: Human-readable location name
- `view_count`: Number of views
- `phash`: Perceptual hash for duplicate detection
- `search_vector`: PostgreSQL full-text search vector

### Auto-Processing

When a photo is uploaded:

1. **Image Generation**: Creates 4 additional sizes automatically
2. **EXIF Extraction**: Parses metadata from original image
3. **WebP Conversion**: Generates WebP versions for modern browsers
4. **Perceptual Hash**: Calculates phash for duplicate detection
5. **Search Index**: Updates full-text search vector
6. **Storage**: Uploads all versions to S3 (if configured)

## PhotoAlbum Model

### Fields

**Core Fields**:
- `title`: Album title (max 200 characters)
- `description`: Album description
- `slug`: URL-friendly slug (auto-generated)
- `cover_photo`: Featured photo for album thumbnail

**Organization**:
- `photos`: Many-to-many relationship with Photo model
- `order`: Display order for album list
- `created_at`: Creation timestamp

**Visibility**:
- `is_private`: Boolean flag for private albums
- `password`: Optional password protection

**Download**:
- `download_enabled`: Allow zip download
- `zip_file`: Generated zip file
- `zip_updated_at`: Last zip generation timestamp

**Search**:
- `search_vector`: PostgreSQL full-text search vector

## Uploading Photos

### Via Django Admin

1. Navigate to Django admin: `/admin/photos/photo/`
2. Click "Add Photo"
3. Fill in fields:
   - Upload original image (required)
   - Title (required)
   - Description (optional)
   - Location (optional)
4. Save photo
5. System automatically processes image

### Via Python API

```python
from photos.models import Photo
from django.core.files import File

# Create photo with automatic processing
with open('path/to/photo.jpg', 'rb') as f:
    photo = Photo.objects.create(
        title='Sunset at the Beach',
        description='Beautiful sunset captured in California',
        location='Santa Monica, CA',
        original_image=File(f, name='sunset.jpg')
    )

# EXIF metadata is automatically extracted
print(f"Camera: {photo.camera_make} {photo.camera_model}")
print(f"Settings: f/{photo.aperture}, {photo.shutter_speed}s, ISO {photo.iso}")
print(f"Location: {photo.gps_latitude}, {photo.gps_longitude}")
```

## Creating Albums

### Via Django Admin

1. Navigate to: `/admin/photos/photoalbum/`
2. Click "Add Photo Album"
3. Fill in fields:
   - Title (required)
   - Slug (auto-generated from title)
   - Description
   - Cover photo (select existing photo)
4. Select photos to include
5. Configure visibility and download settings
6. Save album

### Via Python API

```python
from photos.models import PhotoAlbum, Photo

# Create album
album = PhotoAlbum.objects.create(
    title='California Trip 2025',
    description='Photos from our California adventure',
    is_private=False,
    download_enabled=True
)

# Add photos
photos = Photo.objects.filter(location__icontains='California')
album.photos.add(*photos)

# Set cover photo
album.cover_photo = photos.first()
album.save()
```

## Album Zip Generation

### Manual Generation

Generate zip files for downloadable albums:

```bash
# Generate for all albums with download enabled
python manage.py generate_album_zips --all

# Generate for specific album by ID
python manage.py generate_album_zips --album-id 1

# Generate for specific album by slug
python manage.py generate_album_zips --album-slug "california-trip-2025"

# Use Celery for async processing
python manage.py generate_album_zips --album-id 1 --async
```

**Command Options**:
- `--all`: Process all albums with `download_enabled=True`
- `--album-id`: Process specific album by ID
- `--album-slug`: Process specific album by slug
- `--async`: Use Celery for background processing

### Automatic Generation

Albums automatically regenerate zip files when:
- Photos are added to the album
- Photos are removed from the album
- Album settings change

**Celery Task**: Background zip generation via `photos.tasks.generate_album_zip_task`

### Download Workflow

1. User visits album page
2. If `download_enabled=True`, download button appears
3. User clicks download button
4. System checks if zip exists and is up-to-date
5. If needed, generates new zip (or queues Celery task)
6. User downloads zip file

## EXIF Metadata

### Supported Fields

**Camera Information**:
- Make and model
- Lens make and model
- Focal length
- Focal length (35mm equivalent)

**Exposure Settings**:
- Aperture (f-stop)
- Shutter speed (exposure time)
- ISO sensitivity
- Exposure compensation
- Metering mode
- Flash status

**Location Data**:
- GPS coordinates (latitude, longitude, altitude)
- GPS timestamp
- Location name (manually entered)

**Other Metadata**:
- Date/time taken
- Orientation
- Copyright information
- Software used

### Accessing EXIF Data

```python
from photos.models import Photo

photo = Photo.objects.get(id=1)

# Check if EXIF data exists
if photo.camera_make:
    print(f"Camera: {photo.camera_make} {photo.camera_model}")
    print(f"Lens: {photo.lens_make} {photo.lens_model}")
    print(f"Focal Length: {photo.focal_length}mm")
    print(f"Aperture: f/{photo.aperture}")
    print(f"Shutter Speed: {photo.shutter_speed}s")
    print(f"ISO: {photo.iso}")

# Check if GPS data exists
if photo.gps_latitude and photo.gps_longitude:
    print(f"Location: {photo.gps_latitude}, {photo.gps_longitude}")
    print(f"Altitude: {photo.gps_altitude}m")
```

## Duplicate Detection

The system uses perceptual hashing to identify duplicate or similar photos.

### How It Works

1. **Hash Generation**: Calculates phash for each uploaded photo
2. **Similarity Comparison**: Compares phash values
3. **Threshold**: Photos with similar hashes are flagged as potential duplicates
4. **Manual Review**: Admin reviews flagged duplicates

### Finding Duplicates

```python
from photos.models import Photo
import imagehash
from PIL import Image

# Find photos with similar perceptual hashes
photo = Photo.objects.get(id=1)
photo_phash = imagehash.hex_to_hash(photo.phash)

# Find similar photos (Hamming distance < 10)
similar_photos = []
for other in Photo.objects.exclude(id=photo.id):
    if other.phash:
        other_phash = imagehash.hex_to_hash(other.phash)
        distance = photo_phash - other_phash
        if distance < 10:  # Threshold for similarity
            similar_photos.append((other, distance))

# Sort by similarity
similar_photos.sort(key=lambda x: x[1])
for similar_photo, distance in similar_photos[:5]:
    print(f"{similar_photo.title} - Distance: {distance}")
```

## Search Integration

Photos and albums are indexed for full-text search.

### Indexed Fields

**Photo**:
- Title (weight: A)
- Description (weight: B)
- Location (weight: B)
- Camera make/model (weight: C)
- Lens make/model (weight: C)

**PhotoAlbum**:
- Title (weight: A)
- Description (weight: B)

### Search Examples

```python
from django.contrib.postgres.search import SearchQuery, SearchRank
from photos.models import Photo, PhotoAlbum

# Search photos by keyword
query = SearchQuery('sunset')
photos = Photo.objects.annotate(
    rank=SearchRank('search_vector', query)
).filter(rank__gte=0.01).order_by('-rank')

# Search by location
query = SearchQuery('California')
photos = Photo.objects.annotate(
    rank=SearchRank('search_vector', query)
).filter(rank__gte=0.01).order_by('-rank')

# Search albums
query = SearchQuery('vacation')
albums = PhotoAlbum.objects.annotate(
    rank=SearchRank('search_vector', query)
).filter(rank__gte=0.01).order_by('-rank')
```

### Rebuilding Search Index

```bash
# Rebuild photo search index
python manage.py rebuild_search_index --content-type photos

# Rebuild album search index
python manage.py rebuild_search_index --content-type albums

# Rebuild both
python manage.py rebuild_search_index
```

## Image Optimization

### Size Specifications

**Thumbnail**: 150x150px (square crop)
- Use case: Album covers, small previews
- Format: JPEG and WebP
- Quality: 85

**Small**: 400px width (aspect ratio preserved)
- Use case: Mobile devices, thumbnails
- Format: JPEG and WebP
- Quality: 85

**Medium**: 800px width (aspect ratio preserved)
- Use case: Tablets, small desktop displays
- Format: JPEG and WebP
- Quality: 90

**Large**: 1200px width (aspect ratio preserved)
- Use case: Desktop displays
- Format: JPEG and WebP
- Quality: 90

**Original**: Preserved as uploaded
- Use case: High-resolution display, downloads
- Format: Original format
- Quality: Original quality

### Responsive Images

Use srcset for automatic size selection:

```html
<img
    src="{{ photo.medium_image.url }}"
    srcset="
        {{ photo.small_image.url }} 400w,
        {{ photo.medium_image.url }} 800w,
        {{ photo.large_image.url }} 1200w
    "
    sizes="(max-width: 600px) 400px, (max-width: 1200px) 800px, 1200px"
    alt="{{ photo.title }}"
    loading="lazy"
>
```

### Storage Backend

**Development**: Local file system (`MEDIA_ROOT`)

**Production**: AWS S3 with CloudFront CDN
- Automatic upload to S3 on save
- CDN caching for fast delivery
- Organized by date: `photos/2025/01/15/filename.jpg`

## API Endpoints

### Album Detail

```http
GET /photos/album/<slug>/
```

**Response**: HTML page with album photos

### Album Download Status

```http
GET /photos/album/<slug>/download/status/
```

**Response**:
```json
{
  "status": "ready",
  "url": "https://s3.amazonaws.com/bucket/albums/album-slug.zip",
  "size": 15728640,
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Status Values**:
- `ready`: Zip file is available
- `generating`: Zip is being generated
- `error`: Generation failed
- `disabled`: Download not enabled

## Configuration

### Environment Variables

```bash
# Storage backend
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=us-east-1

# Image optimization
PHOTO_THUMBNAIL_SIZE=150
PHOTO_SMALL_SIZE=400
PHOTO_MEDIUM_SIZE=800
PHOTO_LARGE_SIZE=1200
PHOTO_QUALITY=90
```

### Django Settings

```python
# Image size configuration
PHOTO_SIZES = {
    'thumbnail': (150, 150),  # Square crop
    'small': (400, None),     # Width only
    'medium': (800, None),
    'large': (1200, None),
}

# EXIF fields to extract
EXIF_FIELDS = [
    'camera_make',
    'camera_model',
    'lens_make',
    'lens_model',
    'focal_length',
    'aperture',
    'shutter_speed',
    'iso',
    'gps_latitude',
    'gps_longitude',
]
```

## Troubleshooting

### EXIF Data Not Extracting

**Solutions**:
1. Check image file has EXIF metadata (use exiftool or similar)
2. Verify Pillow is installed with EXIF support
3. Check image format supports EXIF (JPEG, TIFF)
4. Review error logs for parsing issues

### Image Sizes Not Generating

**Solutions**:
1. Check Pillow is installed correctly
2. Verify storage backend is configured
3. Check file permissions (local storage)
4. Review S3 credentials and bucket access
5. Check error logs for processing failures

### Album Zip Not Generating

**Solutions**:
1. Check `download_enabled=True` for album
2. Verify Celery is running (for async generation)
3. Check storage backend for zip file upload
4. Review task logs in Celery/Flower
5. Try manual generation: `python manage.py generate_album_zips --album-id X`

### Search Not Finding Photos

**Solutions**:
1. Rebuild search index: `python manage.py rebuild_search_index --content-type photos`
2. Check PostgreSQL extensions: `pg_trgm`, `unaccent`
3. Verify `search_vector` field is populated
4. Check search query syntax
5. Clear cache and try again

## Related Documentation

- [Search System](search.md) - Full-text search implementation
- [Management Commands](../commands.md) - Command reference
- [API Reference](../api.md) - API documentation
- [Deployment](../deployment.md) - S3 configuration
