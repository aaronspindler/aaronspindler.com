from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count
from .models import BlogComment


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    """Admin interface for blog comments with moderation capabilities"""
    
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
        """Display author with appropriate styling"""
        author = obj.get_author_display()
        if obj.author:
            if obj.author.is_staff:
                return format_html('<strong style="color: #0066cc;">👤 {}</strong>', author)
            return format_html('👤 {}', author)
        return format_html('💭 {}', author or 'Anonymous')
    get_author_display.short_description = 'Author'
    get_author_display.admin_order_field = 'author__username'
    
    def get_blog_post(self, obj):
        """Display blog post with link"""
        display = f"{obj.blog_category}/{obj.blog_template_name}" if obj.blog_category else obj.blog_template_name
        url = obj.get_blog_url()
        return format_html('<a href="{}" target="_blank">{}</a>', url, display)
    get_blog_post.short_description = 'Blog Post'
    get_blog_post.admin_order_field = 'blog_template_name'
    
    def truncated_content(self, obj):
        """Display truncated content"""
        max_length = 50
        if len(obj.content) > max_length:
            return f"{obj.content[:max_length]}..."
        return obj.content
    truncated_content.short_description = 'Content'
    
    def status_badge(self, obj):
        """Display status with color coding"""
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
        """Check if comment is a reply"""
        return '✓' if obj.parent else '✗'
    is_reply.short_description = 'Reply?'
    is_reply.admin_order_field = 'parent'
    
    def replies_count(self, obj):
        """Count of replies to this comment"""
        count = obj.replies.filter(status='approved').count()
        if count > 0:
            return format_html('<strong>{}</strong>', count)
        return '0'
    replies_count.short_description = 'Replies'
    
    def approve_comments(self, request, queryset):
        """Bulk approve comments"""
        count = 0
        for comment in queryset:
            if comment.status != 'approved':
                comment.approve(user=request.user)
                count += 1
        self.message_user(request, f'{count} comments approved.')
    approve_comments.short_description = 'Approve selected comments'
    
    def reject_comments(self, request, queryset):
        """Bulk reject comments"""
        count = 0
        for comment in queryset:
            if comment.status != 'rejected':
                comment.reject(user=request.user)
                count += 1
        self.message_user(request, f'{count} comments rejected.')
    reject_comments.short_description = 'Reject selected comments'
    
    def mark_as_spam(self, request, queryset):
        """Bulk mark as spam"""
        count = 0
        for comment in queryset:
            if comment.status != 'spam':
                comment.mark_as_spam(user=request.user)
                count += 1
        self.message_user(request, f'{count} comments marked as spam.')
    mark_as_spam.short_description = 'Mark selected as spam'
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('author', 'parent', 'moderated_by').annotate(
            reply_count=Count('replies')
        )
    
    def has_change_permission(self, request, obj=None):
        """All staff can view and moderate comments"""
        return request.user.is_staff
    
    def has_add_permission(self, request):
        """Don't allow adding comments through admin"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete comments"""
        return request.user.is_superuser
