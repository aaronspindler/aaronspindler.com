"""
Optimized views for the photos application with caching and performance improvements.
"""
import logging
from typing import Optional, Dict, Any, Type
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Prefetch, QuerySet, Count, Q
from django.http import HttpRequest, HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage, PageNotAnInteger
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page, cache_control
from django.views.decorators.vary import vary_on_headers

from .models import Album, Photo
from .cache import (
    conditional_cache_page, cache_result, cache_album_photos,
    cache_album_count, invalidate_album_cache, CACHE_TIMEOUTS
)

# Set up logger
logger = logging.getLogger(__name__)


class OptimizedAlbumListView(ListView):
    """
    Optimized album list view with caching and query optimization.
    """
    model: Type[Album] = Album
    template_name: str = 'photos/album_list.html'
    context_object_name: str = 'albums'
    paginate_by: int = 12
    
    @method_decorator(conditional_cache_page(CACHE_TIMEOUTS['album_list'], key_prefix='album_list'))
    @method_decorator(vary_on_headers('Accept-Language', 'Accept-Encoding'))
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Dispatch with caching for anonymous users.
        """
        try:
            logger.info(f"Album list accessed by {request.user if request.user.is_authenticated else 'anonymous'}")
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in album list view: {str(e)}", exc_info=True)
            return render(request, 'photos/error.html', {
                'error_message': _("An unexpected error occurred.")
            }, status=500)
    
    def get_queryset(self) -> QuerySet[Album]:
        """
        Optimized queryset with proper prefetching and annotation.
        """
        try:
            # Use select_related for ForeignKey relationships
            # Use prefetch_related for reverse ForeignKey and ManyToMany
            # Annotate with photo count to avoid N+1 queries
            queryset = Album.objects.filter(
                is_published=True
            ).annotate(
                photo_count_annotated=Count('photos')
            ).prefetch_related(
                Prefetch(
                    'photos',
                    queryset=Photo.objects.only(
                        'id', 'album_id', 'thumbnail', 'order', 'created_at'
                    ).order_by('order', '-created_at')[:4]  # Only prefetch first 4 photos for preview
                )
            ).order_by('order', '-created_at')
            
            logger.debug(f"Fetching optimized album queryset")
            return queryset
            
        except Exception as e:
            logger.error(f"Error fetching albums: {str(e)}", exc_info=True)
            return Album.objects.none()
    
    @cache_result(timeout=CACHE_TIMEOUTS['stats'], key_prefix='album_stats')
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """
        Cached context data with additional statistics.
        """
        context = super().get_context_data(**kwargs)
        
        try:
            # Add cached statistics
            total_albums = Album.objects.filter(is_published=True).count()
            total_photos = Photo.objects.filter(album__is_published=True).count()
            
            context.update({
                'total_albums': total_albums,
                'total_photos': total_photos,
                'has_content': total_albums > 0,
            })
            
        except Exception as e:
            logger.error(f"Error adding context data: {str(e)}")
        
        return context


class OptimizedAlbumDetailView(DetailView):
    """
    Optimized album detail view with caching and efficient photo loading.
    """
    model: Type[Album] = Album
    template_name: str = 'photos/album_detail.html'
    context_object_name: str = 'album'
    
    @method_decorator(conditional_cache_page(CACHE_TIMEOUTS['album_detail'], key_prefix='album_detail'))
    @method_decorator(vary_on_headers('Accept-Language', 'Accept-Encoding'))
    @method_decorator(cache_control(public=True, max_age=300))
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Dispatch with caching headers.
        """
        album_pk = kwargs.get('pk')
        logger.info(f"Album {album_pk} accessed by {request.user if request.user.is_authenticated else 'anonymous'}")
        
        try:
            response = super().dispatch(request, *args, **kwargs)
            
            # Add ETag for browser caching
            if response.status_code == 200:
                from django.utils.cache import patch_response_headers
                patch_response_headers(response, cache_timeout=CACHE_TIMEOUTS['album_detail'])
            
            return response
            
        except Http404:
            logger.warning(f"Album {album_pk} not found")
            raise
        except Exception as e:
            logger.error(f"Error in album detail view: {str(e)}", exc_info=True)
            return render(request, 'photos/error.html', {
                'error_message': _("Error loading album.")
            }, status=500)
    
    def get_queryset(self) -> QuerySet[Album]:
        """
        Optimized queryset with selective field loading.
        """
        return Album.objects.filter(
            is_published=True
        ).select_related().prefetch_related(
            Prefetch(
                'photos',
                queryset=Photo.objects.select_related('album').only(
                    'id', 'album_id', 'title', 'caption',
                    'original_image', 'thumbnail', 'order', 'created_at'
                ).order_by('order', '-created_at')
            )
        )
    
    def get_object(self, queryset: Optional[QuerySet] = None) -> Album:
        """
        Get album with caching.
        """
        obj = super().get_object(queryset)
        
        if not obj.is_published:
            logger.warning(f"Attempt to access unpublished album {obj.pk}")
            raise Http404(_("Album not available."))
        
        return obj
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """
        Optimized context with cached photo data.
        """
        context = super().get_context_data(**kwargs)
        album = context['album']
        
        try:
            # Use cached photo retrieval
            photos = cache_album_photos(album.pk)
            photo_count = cache_album_count(album.pk)
            
            context.update({
                'photos': photos,
                'photo_count': photo_count,
                'has_photos': photo_count > 0,
                'first_photo': photos[0] if photos else None,
                'has_multiple_photos': photo_count > 1,
            })
            
            # Add navigation data
            context['breadcrumbs'] = [
                {'title': _('Albums'), 'url': '/'},
                {'title': album.title, 'url': None}
            ]
            
            # Add metadata for SEO
            context['meta'] = {
                'title': album.title,
                'description': album.description[:160] if album.description else '',
                'image': album.cover_image.url if album.cover_image else None,
            }
            
        except Exception as e:
            logger.error(f"Error getting photos for album {album.pk}: {str(e)}")
            context['photos_error'] = True
        
        return context


class LazyLoadPhotoView(DetailView):
    """
    View for lazy loading individual photos via AJAX.
    """
    model: Type[Photo] = Photo
    template_name: str = 'photos/partials/photo_item.html'
    context_object_name: str = 'photo'
    
    @method_decorator(cache_page(CACHE_TIMEOUTS['photo'], key_prefix='photo'))
    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Dispatch with photo caching.
        """
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            raise Http404("This endpoint is for AJAX requests only")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self) -> QuerySet[Photo]:
        """
        Optimized photo queryset.
        """
        return Photo.objects.select_related('album').only(
            'id', 'album_id', 'title', 'caption',
            'original_image', 'thumbnail'
        )


@cache_page(CACHE_TIMEOUTS['stats'], key_prefix='gallery_stats')
def gallery_stats_view(request: HttpRequest) -> HttpResponse:
    """
    Cached view for gallery statistics.
    """
    from django.db.models import Sum, Avg
    from django.core.cache import cache
    
    stats_key = 'photos:gallery:stats:complete'
    stats = cache.get(stats_key)
    
    if stats is None:
        stats = {
            'total_albums': Album.objects.filter(is_published=True).count(),
            'total_photos': Photo.objects.filter(album__is_published=True).count(),
            'avg_photos_per_album': Photo.objects.filter(
                album__is_published=True
            ).values('album').annotate(
                count=Count('id')
            ).aggregate(
                avg=Avg('count')
            )['avg'] or 0,
            'recent_albums': Album.objects.filter(
                is_published=True
            ).order_by('-created_at')[:5].values('id', 'title', 'created_at'),
        }
        
        cache.set(stats_key, stats, CACHE_TIMEOUTS['stats'])
    
    return render(request, 'photos/stats.html', {'stats': stats})


def prefetch_album_images(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Endpoint to prefetch and cache album images for better performance.
    """
    from django.http import JsonResponse
    
    try:
        album = get_object_or_404(Album, pk=pk, is_published=True)
        
        # Warm the cache for this album
        from .cache import warm_album_cache
        warm_album_cache(album.pk)
        
        # Get photo URLs for prefetching
        photos = Photo.objects.filter(album=album).values_list(
            'thumbnail', 'original_image'
        )
        
        urls = []
        for thumb, original in photos:
            if thumb:
                urls.append(thumb)
            if original:
                urls.append(original)
        
        return JsonResponse({
            'status': 'success',
            'album_id': album.pk,
            'urls': urls[:20]  # Limit to first 20 images
        })
        
    except Exception as e:
        logger.error(f"Error prefetching album {pk}: {str(e)}")
        return JsonResponse({'status': 'error'}, status=500)