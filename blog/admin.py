from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count
from .models import BlogComment, KnowledgeGraphScreenshot


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    """Admin interface for blog comments with moderation capabilities."""
    
    list_display = [
        'id', 
        'get_author_display', 
        'get_blog_post',
        'truncated_content', 
        'status_badge',
        'created_at',
        'is_reply',
        'replies_count'
    ]
    
    list_filter = [
        'status',
        'created_at',
        'blog_category',
        ('author', admin.EmptyFieldListFilter),
        ('parent', admin.EmptyFieldListFilter),
    ]
    
    search_fields = [
        'content',
        'author__username',
        'author__email',
        'author_name',
        'author_email',
        'blog_template_name',
        'ip_address'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'ip_address',
        'user_agent',
        'moderated_at',
        'moderated_by',
        'is_edited',
        'edited_at'
    ]
    
    fieldsets = (
        ('Blog Post', {
            'fields': ('blog_template_name', 'blog_category')
        }),
        ('Author Information', {
            'fields': ('author', 'author_name', 'author_email')
        }),
        ('Comment', {
            'fields': ('content', 'parent')
        }),
        ('Moderation', {
            'fields': ('status', 'moderation_note', 'moderated_at', 'moderated_by'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'is_edited', 'edited_at', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_comments', 'reject_comments', 'mark_as_spam']
    
    date_hierarchy = 'created_at'
    
    def get_author_display(self, obj):
        """Display author with visual indicators for staff and anonymous users."""
        author = obj.get_author_display()
        if obj.author:
            if obj.author.is_staff:
                return format_html('<strong style="color: #0066cc;">👤 {}</strong>', author)
            return format_html('👤 {}', author)
        return format_html('💭 {}', author or 'Anonymous')
    get_author_display.short_description = 'Author'
    get_author_display.admin_order_field = 'author__username'
    
    def get_blog_post(self, obj):
        """Display blog post with clickable link to the actual post."""
        display = f"{obj.blog_category}/{obj.blog_template_name}" if obj.blog_category else obj.blog_template_name
        url = obj.get_blog_url()
        return format_html('<a href="{}" target="_blank">{}</a>', url, display)
    get_blog_post.short_description = 'Blog Post'
    get_blog_post.admin_order_field = 'blog_template_name'
    
    def truncated_content(self, obj):
        """Display first 50 characters of comment content."""
        max_length = 50
        if len(obj.content) > max_length:
            return f"{obj.content[:max_length]}..."
        return obj.content
    truncated_content.short_description = 'Content'
    
    def status_badge(self, obj):
        """Display comment status as a colored badge for quick visual identification."""
        colors = {
            'pending': '#FFA500',
            'approved': '#28a745',
            'rejected': '#dc3545',
            'spam': '#6c757d'
        }
        color = colors.get(obj.status, '#000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def is_reply(self, obj):
        """Indicate whether this comment is a reply to another comment."""
        return '✓' if obj.parent else '✗'
    is_reply.short_description = 'Reply?'
    is_reply.admin_order_field = 'parent'
    
    def replies_count(self, obj):
        """Show count of approved replies to this comment."""
        count = obj.replies.filter(status='approved').count()
        if count > 0:
            return format_html('<strong>{}</strong>', count)
        return '0'
    replies_count.short_description = 'Replies'
    
    def approve_comments(self, request, queryset):
        """Bulk action to approve multiple comments at once."""
        count = 0
        for comment in queryset:
            if comment.status != 'approved':
                comment.approve(user=request.user)
                count += 1
        self.message_user(request, f'{count} comments approved.')
    approve_comments.short_description = 'Approve selected comments'
    
    def reject_comments(self, request, queryset):
        """Bulk action to reject multiple comments at once."""
        count = 0
        for comment in queryset:
            if comment.status != 'rejected':
                comment.reject(user=request.user)
                count += 1
        self.message_user(request, f'{count} comments rejected.')
    reject_comments.short_description = 'Reject selected comments'
    
    def mark_as_spam(self, request, queryset):
        """Bulk action to mark multiple comments as spam."""
        count = 0
        for comment in queryset:
            if comment.status != 'spam':
                comment.mark_as_spam(user=request.user)
                count += 1
        self.message_user(request, f'{count} comments marked as spam.')
    mark_as_spam.short_description = 'Mark selected as spam'
    
    def get_queryset(self, request):
        """Optimize queryset to reduce database queries by prefetching related data."""
        qs = super().get_queryset(request)
        return qs.select_related('author', 'parent', 'moderated_by').annotate(
            reply_count=Count('replies')
        )
    
    def has_change_permission(self, request, obj=None):
        """All staff members can view and moderate comments."""
        return request.user.is_staff
    
    def has_add_permission(self, request):
        """Prevent adding comments through admin interface - comments should come from the blog."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can permanently delete comments."""
        return request.user.is_superuser


@admin.register(KnowledgeGraphScreenshot)
class KnowledgeGraphScreenshotAdmin(admin.ModelAdmin):
    """Admin interface for managing knowledge graph screenshots."""
    
    list_display = [
        'id',
        'get_thumbnail',
        'created_at',
        'updated_at',
        'get_hash_display',
        'image_size'
    ]
    
    list_filter = [
        'created_at',
        'updated_at'
    ]
    
    readonly_fields = [
        'get_preview',
        'graph_data_hash',
        'created_at',
        'updated_at',
        'get_image_url'
    ]
    
    fieldsets = (
        ('Screenshot', {
            'fields': ('get_preview', 'image', 'get_image_url')
        }),
        ('Metadata', {
            'fields': ('graph_data_hash', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    actions = ['regenerate_screenshot']
    
    def get_thumbnail(self, obj):
        """Display a small thumbnail of the screenshot in the list view."""
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="60" style="border-radius: 4px; object-fit: cover;" />',
                obj.image.url
            )
        return '-'
    get_thumbnail.short_description = 'Thumbnail'
    
    def get_preview(self, obj):
        """Display a larger preview of the screenshot in the detail view."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 800px; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
                obj.image.url
            )
        return 'No screenshot available'
    get_preview.short_description = 'Preview'
    
    def get_hash_display(self, obj):
        """Display the first 8 characters of the hash for easier identification."""
        if obj.graph_data_hash:
            return format_html(
                '<code style="background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace;">{}</code>',
                obj.graph_data_hash[:8]
            )
        return '-'
    get_hash_display.short_description = 'Graph Hash'
    get_hash_display.admin_order_field = 'graph_data_hash'
    
    def get_image_url(self, obj):
        """Display the URL of the image for easy copying."""
        if obj.image:
            return format_html(
                '<input type="text" value="{}" readonly style="width: 400px;" onclick="this.select();" />',
                obj.image.url
            )
        return '-'
    get_image_url.short_description = 'Image URL'
    
    def image_size(self, obj):
        """Display the file size of the screenshot."""
        if obj.image:
            try:
                size_bytes = obj.image.size
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.1f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.1f} MB"
            except:
                return '-'
        return '-'
    image_size.short_description = 'File Size'
    
    def regenerate_screenshot(self, request, queryset):
        """Action to trigger regeneration of the knowledge graph screenshot."""
        from django.core.management import call_command
        from django.contrib import messages
        
        try:
            # Call the management command to regenerate
            call_command('generate_knowledge_graph_screenshot')
            messages.success(request, 'Knowledge graph screenshot has been regenerated successfully.')
        except Exception as e:
            messages.error(request, f'Error regenerating screenshot: {str(e)}')
    regenerate_screenshot.short_description = 'Regenerate knowledge graph screenshot'
    
    def has_add_permission(self, request):
        """Prevent manually adding screenshots - they should be generated via management command."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete screenshots."""
        return request.user.is_superuser
