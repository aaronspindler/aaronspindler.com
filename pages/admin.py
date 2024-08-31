from django.contrib import admin
from .models import BlogPost, PageVisit, Tag

@admin.register(PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = ('page_name', 'ip_address', 'created_at')
    list_filter = ('page_name', 'created_at', 'ip_address')
    search_fields = ('page_name', 'ip_address')
    readonly_fields = ('created_at', 'ip_address', 'page_name')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'published', 'created_at', 'edited_at')
    list_filter = ('published', 'created_at', 'edited_at', 'tags')
    search_fields = ('title', 'short_content', 'content_html')
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ('tags',)
    readonly_fields = ('created_at', 'edited_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

