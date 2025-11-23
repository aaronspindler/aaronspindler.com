# Photos App Documentation

> **Smart photo management** with automatic multi-resolution generation, EXIF extraction, and album support.

## Overview

The photos app provides comprehensive photo management with automatic image processing, EXIF metadata extraction, and album organization. Photos are stored in AWS S3 with multiple resolution variants generated automatically.

**Key Features:**
- Multi-resolution image generation (thumbnail, small, medium, large, original)
- Automatic EXIF metadata extraction (camera, location, settings)
- Album management with public/private support
- Zip generation for album downloads
- WebP conversion for optimized delivery
- Search integration (searchable by title, description, location)
- AWS S3 storage with CloudFront CDN

## Documentation

### Core Documentation

- **[Photo Management](photo-management.md)** - Complete photo system guide
  - Multi-resolution image architecture
  - EXIF metadata extraction
  - AWS S3 storage configuration
  - Album management
  - Zip generation and downloads
  - WebP conversion
  - Search integration

### Related Documentation

**Core Docs:**
- [Architecture](../../architecture.md) - Photos app structure in Django apps section
- [Commands](../../commands.md) - Photo-related management commands (if any)
- [API Reference](../../api.md) - Photo and album API endpoints
- [Deployment](../../deployment.md) - S3 configuration for production

**Related Features:**
- [Search System](../../features/search.md) - Photos are searchable
- [Performance Monitoring](../../features/performance-monitoring.md) - Image optimization tracking

## Quick Start

### Adding Photos

1. **Upload via Django admin**:
   - Go to `/admin/photos/photo/add/`
   - Upload image file
   - Add title and description
   - Assign to album (optional)
   - Save

2. **Automatic processing**:
   - Multiple resolutions generated
   - EXIF metadata extracted
   - WebP versions created
   - Uploaded to S3

### Creating Albums

1. **Create album in Django admin**:
   - Go to `/admin/photos/photoalbum/add/`
   - Add name and description
   - Set public/private status
   - Add cover photo
   - Save

2. **Add photos to album**:
   - Edit photos
   - Select album from dropdown
   - Photos automatically included

**See [Photo Management](photo-management.md) for complete guide.**

## Project Structure

```
photos/
├── __init__.py
├── admin.py                    # Django admin configuration
├── models.py                   # Photo, PhotoAlbum models
├── views.py                    # Photo and album views
├── storage_backends.py         # S3 storage configuration
├── utils/
│   ├── exif.py                 # EXIF extraction
│   ├── image_processing.py     # Multi-resolution generation
│   └── zip_generation.py       # Album zip creation
├── templates/
│   └── photos/
│       ├── photo_detail.html
│       ├── photo_list.html
│       ├── album_detail.html
│       └── album_list.html
└── static/
    └── css/photos.css
```

## Key Components

### Models

**Photo**:
- Original image stored in S3
- Multiple resolution variants (thumbnail, small, medium, large)
- EXIF metadata fields (camera, lens, ISO, aperture, shutter speed, focal length)
- GPS coordinates and location name
- Timestamps (taken_at, uploaded_at)
- Search vector for full-text search

**PhotoAlbum**:
- Collection of photos
- Public/private visibility
- Cover photo
- Zip download support
- Search vector for full-text search

### Image Processing

**Resolution Variants:**
- **Thumbnail**: 150x150px (crop to square)
- **Small**: 400px max dimension
- **Medium**: 800px max dimension
- **Large**: 1600px max dimension
- **Original**: Full resolution

**Formats:**
- JPEG for compatibility
- WebP for optimized delivery (when supported)

**See [Photo Management](photo-management.md#multi-resolution-images) for complete details.**

### EXIF Extraction

Automatically extracted metadata:
- Camera make and model
- Lens information
- ISO speed
- Aperture (f-stop)
- Shutter speed
- Focal length
- GPS coordinates
- Date/time taken

**See [Photo Management](photo-management.md#exif-metadata) for implementation details.**

## Storage Architecture

### AWS S3 Configuration

**Buckets:**
- Production: `your-bucket-name`
- Media path: `media/photos/`

**Access:**
- Public read access for photo files
- CloudFront CDN for global delivery
- Signed URLs for private albums (future)

**Environment Variables:**
```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_STORAGE_BUCKET_NAME=your_bucket_name
AWS_S3_REGION_NAME=us-east-1
```

**See [Photo Management](photo-management.md#aws-s3-storage) and [Deployment](../../deployment.md) for configuration.**

## Common Tasks

### Photo Management

```python
# Django shell
python manage.py shell

# Get all photos
from photos.models import Photo
photos = Photo.objects.all()

# Get photos by album
album = PhotoAlbum.objects.get(name="Vacation 2024")
photos = album.photos.all()

# Get photos with GPS coordinates
photos_with_gps = Photo.objects.exclude(latitude__isnull=True)

# Search photos
from django.contrib.postgres.search import SearchQuery
query = SearchQuery('sunset')
results = Photo.objects.filter(search_vector=query)
```

### Album Operations

```python
# Create album
album = PhotoAlbum.objects.create(
    name="My Album",
    description="Description",
    public=True
)

# Add photos to album
photo.album = album
photo.save()

# Generate zip download
# Automatic when user requests download
```

## API Endpoints

- `GET /api/photos/` - List photos
- `GET /api/photos/{id}/` - Photo detail
- `GET /api/albums/` - List albums
- `GET /api/albums/{id}/` - Album detail
- `GET /api/albums/{id}/download/` - Download album as zip

**See [API Reference](../../api.md#photos) for complete API documentation.**

## Performance Optimization

### Image Delivery

- **CloudFront CDN**: Global content delivery
- **WebP Format**: 25-35% smaller than JPEG
- **Lazy Loading**: Images load as they enter viewport
- **Responsive Images**: Serve appropriate resolution per device

### Database Optimization

- **Indexes**: On album, taken_at, uploaded_at
- **Search Vectors**: GIN index for full-text search
- **Select Related**: Optimize album queries

**See [Photo Management](photo-management.md#performance-optimization) for details.**

## Future Enhancements

### Planned Features

**Phase 2:**
- Face detection and tagging
- Automatic categorization (ML-based)
- Geolocation-based browsing
- Timeline view

**Phase 3:**
- Photo editing (crop, rotate, filters)
- Bulk upload with progress tracking
- RAW file support
- Photo sharing with expiring links

**Phase 4:**
- AI-powered search ("show me photos with dogs")
- Automatic duplicate detection
- Photo stories/slideshows
- Integration with photo services (Google Photos, iCloud)

## Contributing

When contributing to the photos app:

1. **Test with various image formats** (JPEG, PNG, HEIC)
2. **Verify EXIF extraction** for different cameras
3. **Test S3 uploads** in development (use Localstack)
4. **Optimize image processing** for performance
5. **Document new features** in this directory

**See [Photo Management](photo-management.md) for complete contribution guidelines.**

---

**Questions?** Check the [Documentation Index](../../README.md) or create a GitHub issue.
