from django import forms
from django.forms import ClearableFileInput
from .models import Photo


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
        label='Select images',
        help_text='You can select multiple images at once',
        required=True
    )
    album = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        help_text='Optional: Add all uploaded photos to this album'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import PhotoAlbum
        self.fields['album'].queryset = PhotoAlbum.objects.all()
    
    def save(self):
        """Save all uploaded images as Photo objects."""
        images = self.cleaned_data['images']
        album = self.cleaned_data.get('album')
        created_photos = []
        
        # Handle single file or list of files
        if not isinstance(images, list):
            images = [images]
        
        for image_file in images:
            # Create a photo for each uploaded file
            photo = Photo(
                image=image_file,
                # Title will be empty by default, can be edited later
            )
            photo.save()
            created_photos.append(photo)
            
            # Add to album if specified
            if album:
                album.photos.add(photo)
        
        return created_photos