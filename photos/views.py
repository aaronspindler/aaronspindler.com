"""
Views for the photos application with improved error handling and logging.
"""
import logging
from typing import Optional, Dict, Any, Type
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Prefetch, QuerySet
from django.http import HttpRequest, HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.utils.translation import gettext_lazy as _

from .models import Album, Photo

# Set up logger
logger = logging.getLogger(__name__)


class AlbumListView(ListView):
    """
    Display published albums on the home page with enhanced error handling and logging.
    
    Attributes:
        model: The Album model
        template_name: Template for rendering the album list
        context_object_name: Name of the context variable for albums
        paginate_by: Number of albums per page
    """
    model: Type[Album] = Album
    template_name: str = 'photos/album_list.html'
    context_object_name: str = 'albums'
    paginate_by: int = 12
    
    def get_queryset(self) -> QuerySet[Album]:
        """
        Filter for published albums only, ordered by 'order' field, then by created_at descending.
        
        Returns:
            QuerySet[Album]: Filtered and ordered queryset of published albums
            
        Raises:
            Exception: If database query fails
        """
        try:
            logger.debug("Fetching published albums for list view")
            
            queryset = Album.objects.filter(
                is_published=True
            ).prefetch_related('photos').order_by('order', '-created_at')
            
            logger.info(f"Retrieved {queryset.count()} published albums")
            return queryset
            
        except Exception as e:
            logger.error(f"Error fetching albums: {str(e)}", exc_info=True)
            # Return empty queryset to display empty state instead of error page
            return Album.objects.none()
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """
        Add additional context data for the template.
        
        Args:
            **kwargs: Additional keyword arguments
            
        Returns:
            Dict[str, Any]: Context dictionary with albums and metadata
        """
        try:
            context = super().get_context_data(**kwargs)
            
            # Add total album count for display
            context['total_albums'] = self.get_queryset().count()
            
            # Add error flag if queryset is empty due to error
            if not context.get('albums') and hasattr(self, '_query_error'):
                context['query_error'] = True
                context['error_message'] = _("Unable to load albums at this time. Please try again later.")
            
            logger.debug(f"Context prepared with {context.get('total_albums', 0)} albums")
            return context
            
        except Exception as e:
            logger.error(f"Error preparing context data: {str(e)}", exc_info=True)
            return super().get_context_data(**kwargs)
    
    def paginate_queryset(self, queryset: QuerySet, page_size: int) -> tuple:
        """
        Paginate the queryset with improved error handling.
        
        Args:
            queryset: The queryset to paginate
            page_size: Number of items per page
            
        Returns:
            tuple: (paginator, page, object_list, is_paginated)
        """
        try:
            return super().paginate_queryset(queryset, page_size)
            
        except PageNotAnInteger:
            logger.warning("Invalid page number provided, defaulting to page 1")
            # Default to first page
            self.kwargs['page'] = 1
            return super().paginate_queryset(queryset, page_size)
            
        except EmptyPage:
            logger.warning(f"Page number out of range, showing last page")
            # Show last page if page number is out of range
            paginator = self.get_paginator(queryset, page_size)
            self.kwargs['page'] = paginator.num_pages
            return super().paginate_queryset(queryset, page_size)
            
        except Exception as e:
            logger.error(f"Pagination error: {str(e)}", exc_info=True)
            # Return unpaginated results on error
            return (None, None, queryset, False)
    
    def handle_no_permission(self) -> HttpResponse:
        """
        Handle permission denied errors.
        
        Returns:
            HttpResponse: Response with permission denied message
        """
        logger.warning("Permission denied for album list view")
        raise PermissionDenied(_("You don't have permission to view albums."))
    
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Dispatch the request with error handling.
        
        Args:
            request: The HTTP request
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            HttpResponse: The response
        """
        try:
            logger.info(f"Album list view accessed by {request.user if request.user.is_authenticated else 'anonymous'}")
            return super().dispatch(request, *args, **kwargs)
            
        except PermissionDenied:
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error in album list view: {str(e)}", exc_info=True)
            return render(request, 'photos/error.html', {
                'error_message': _("An unexpected error occurred. Please try again later.")
            }, status=500)


class AlbumDetailView(DetailView):
    """
    Show all photos in a specific album with enhanced error handling and logging.
    
    Attributes:
        model: The Album model
        template_name: Template for rendering the album detail
        context_object_name: Name of the context variable for the album
    """
    model: Type[Album] = Album
    template_name: str = 'photos/album_detail.html'
    context_object_name: str = 'album'
    
    def get_queryset(self) -> QuerySet[Album]:
        """
        Get published albums with prefetched photos.
        
        Returns:
            QuerySet[Album]: Filtered queryset with prefetched photos
            
        Raises:
            Http404: If album is not found or not published
        """
        try:
            logger.debug(f"Fetching album details for pk={self.kwargs.get('pk')}")
            
            queryset = Album.objects.filter(
                is_published=True
            ).prefetch_related(
                Prefetch('photos', queryset=Photo.objects.order_by('order', '-created_at'))
            )
            
            return queryset
            
        except Exception as e:
            logger.error(f"Error fetching album: {str(e)}", exc_info=True)
            raise Http404(_("Album not found or unavailable."))
    
    def get_object(self, queryset: Optional[QuerySet] = None) -> Album:
        """
        Get the album object with enhanced error handling.
        
        Args:
            queryset: Optional queryset to use
            
        Returns:
            Album: The album instance
            
        Raises:
            Http404: If album doesn't exist or isn't published
        """
        try:
            obj = super().get_object(queryset)
            
            # Additional check for unpublished albums
            if not obj.is_published:
                logger.warning(f"Attempt to access unpublished album {obj.pk}")
                raise Http404(_("This album is not available."))
            
            logger.info(f"Album '{obj.title}' (ID: {obj.pk}) accessed")
            return obj
            
        except Album.DoesNotExist:
            logger.warning(f"Album with pk={self.kwargs.get('pk')} not found")
            raise Http404(_("Album not found."))
            
        except Http404:
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error getting album: {str(e)}", exc_info=True)
            raise Http404(_("Unable to load album."))
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """
        Add photos and additional metadata to context.
        
        Args:
            **kwargs: Additional keyword arguments
            
        Returns:
            Dict[str, Any]: Context dictionary with album, photos, and metadata
        """
        try:
            context = super().get_context_data(**kwargs)
            
            # Get photos with error handling
            album = context['album']
            try:
                photos = album.photos.all()
                context['photos'] = photos
                context['photo_count'] = photos.count()
                
                # Add navigation helpers
                if photos.exists():
                    context['first_photo'] = photos.first()
                    context['has_multiple_photos'] = photos.count() > 1
                
                logger.debug(f"Album '{album.title}' has {photos.count()} photos")
                
            except Exception as e:
                logger.error(f"Error fetching photos for album {album.pk}: {str(e)}", exc_info=True)
                context['photos'] = []
                context['photo_count'] = 0
                context['photos_error'] = True
                context['error_message'] = _("Unable to load photos for this album.")
            
            # Add breadcrumb data
            context['breadcrumbs'] = [
                {'title': _('Albums'), 'url': '/albums/'},
                {'title': album.title, 'url': None}
            ]
            
            return context
            
        except Exception as e:
            logger.error(f"Error preparing context data: {str(e)}", exc_info=True)
            return super().get_context_data(**kwargs)
    
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Dispatch the request with comprehensive error handling.
        
        Args:
            request: The HTTP request
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            HttpResponse: The response
        """
        try:
            album_pk = kwargs.get('pk')
            logger.info(f"Album detail view accessed for album {album_pk} by {request.user if request.user.is_authenticated else 'anonymous'}")
            
            response = super().dispatch(request, *args, **kwargs)
            
            # Log successful access
            if response.status_code == 200:
                logger.info(f"Album {album_pk} successfully displayed")
            
            return response
            
        except Http404:
            logger.warning(f"404 error for album {kwargs.get('pk')}")
            raise
            
        except PermissionDenied:
            logger.warning(f"Permission denied for album {kwargs.get('pk')}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error in album detail view: {str(e)}", exc_info=True)
            return render(request, 'photos/error.html', {
                'error_message': _("An unexpected error occurred while loading this album.")
            }, status=500)


def handle_404(request: HttpRequest, exception: Optional[Exception] = None) -> HttpResponse:
    """
    Custom 404 handler for the photos app.
    
    Args:
        request: The HTTP request
        exception: The exception that triggered the 404
        
    Returns:
        HttpResponse: 404 error page
    """
    logger.warning(f"404 error: {request.path}")
    return render(request, 'photos/404.html', {
        'message': _("The album or photo you're looking for doesn't exist.")
    }, status=404)


def handle_500(request: HttpRequest) -> HttpResponse:
    """
    Custom 500 handler for the photos app.
    
    Args:
        request: The HTTP request
        
    Returns:
        HttpResponse: 500 error page
    """
    logger.error(f"500 error on {request.path}")
    return render(request, 'photos/500.html', {
        'message': _("An internal server error occurred. We've been notified and will fix it soon.")
    }, status=500)