from django import forms
from django.core.exceptions import ValidationError
from django.forms import ClearableFileInput

from photos.image_utils import DuplicateDetector

from .models import Photo, PhotoAlbum


class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class PhotoBulkUploadForm(forms.Form):
    """Form for bulk uploading photos."""

    images = MultipleFileField(
        label="Select images",
        help_text="You can select multiple images at once",
        required=True,
    )
    album = forms.ModelChoiceField(
        queryset=None,
        required=False,
        help_text="Optional: Add all uploaded photos to this album",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import PhotoAlbum

        self.fields["album"].queryset = PhotoAlbum.objects.all()

    def save(self, skip_duplicates=True):
        """
        Save all uploaded images as Photo objects.

        Args:
            skip_duplicates: If True, silently skip duplicate images.
                           If False, raise ValidationError on duplicates.

        Returns:
            dict: {
                'created': List of successfully created Photo objects,
                'skipped': List of (filename, reason) tuples for skipped images,
                'errors': List of (filename, error) tuples for failed uploads
            }
        """
        images = self.cleaned_data["images"]
        album = self.cleaned_data.get("album")
        result = {"created": [], "skipped": [], "errors": []}

        if not isinstance(images, list):
            images = [images]

        for image_file in images:
            filename = getattr(image_file, "name", "unknown")

            try:
                existing_photos = Photo.objects.all()
                duplicates = DuplicateDetector.find_duplicates(image_file, existing_photos, exact_match_only=False)

                if duplicates["exact_duplicates"]:
                    duplicate = duplicates["exact_duplicates"][0]
                    if skip_duplicates:
                        result["skipped"].append(
                            (
                                filename,
                                f"Exact duplicate of '{duplicate}' (ID: {duplicate.pk})",
                            )
                        )
                        continue
                    else:
                        raise ValidationError(f"{filename}: Exact duplicate of '{duplicate}'")

                photo = Photo(
                    image=image_file,
                    # Store computed hashes to avoid recomputing
                    file_hash=duplicates.get("file_hash", ""),
                    perceptual_hash=duplicates.get("perceptual_hash", ""),
                )
                # Skip duplicate check in save since we already checked
                photo.save(skip_duplicate_check=True)
                result["created"].append(photo)

                if album:
                    album.photos.add(photo)

            except ValidationError as e:
                result["errors"].append((filename, str(e)))
            except Exception as e:
                result["errors"].append((filename, f"Upload failed: {str(e)}"))

        return result


class PhotoAlbumForm(forms.ModelForm):
    """Form for PhotoAlbum that explicitly allows empty albums."""

    class Meta:
        model = PhotoAlbum
        fields = ["title", "slug", "description", "is_private", "allow_downloads", "photos"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Explicitly mark photos as not required
        self.fields["photos"].required = False
