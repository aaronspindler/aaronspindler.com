from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import BlogComment, KnowledgeGraphScreenshot


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_author_display",
        "get_blog_post",
        "truncated_content",
        "status_badge",
        "created_at",
        "is_reply",
        "replies_count",
    ]

    list_filter = [
        "status",
        "created_at",
        "blog_category",
        ("author", admin.EmptyFieldListFilter),
        ("parent", admin.EmptyFieldListFilter),
    ]

    search_fields = [
        "content",
        "author__username",
        "author__email",
        "author_name",
        "author_email",
        "blog_template_name",
        "ip_address",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "ip_address",
        "user_agent",
        "moderated_at",
        "moderated_by",
        "is_edited",
        "edited_at",
    ]

    fieldsets = (
        ("Blog Post", {"fields": ("blog_template_name", "blog_category")}),
        ("Author Information", {"fields": ("author", "author_name", "author_email")}),
        ("Comment", {"fields": ("content", "parent")}),
        (
            "Moderation",
            {
                "fields": ("status", "moderation_note", "moderated_at", "moderated_by"),
                "classes": ("collapse",),
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                    "is_edited",
                    "edited_at",
                    "ip_address",
                    "user_agent",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["approve_comments", "reject_comments", "mark_as_spam"]

    date_hierarchy = "created_at"

    @admin.display(
        description="Author",
        ordering="author__username",
    )
    def get_author_display(self, obj):
        author = obj.get_author_display()
        if obj.author:
            if obj.author.is_staff:
                return format_html('<strong style="color: #0066cc;">👤 {}</strong>', author)
            return format_html("👤 {}", author)
        return format_html("💭 {}", author or "Anonymous")

    @admin.display(
        description="Blog Post",
        ordering="blog_template_name",
    )
    def get_blog_post(self, obj):
        display = f"{obj.blog_category}/{obj.blog_template_name}" if obj.blog_category else obj.blog_template_name
        url = obj.get_blog_url()
        return format_html('<a href="{}" target="_blank">{}</a>', url, display)

    @admin.display(description="Content")
    def truncated_content(self, obj):
        max_length = 50
        if len(obj.content) > max_length:
            return f"{obj.content[:max_length]}..."
        return obj.content

    @admin.display(
        description="Status",
        ordering="status",
    )
    def status_badge(self, obj):
        colors = {
            "pending": "#FFA500",
            "approved": "#28a745",
            "rejected": "#dc3545",
            "spam": "#6c757d",
        }
        color = colors.get(obj.status, "#000")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(
        description="Reply?",
        ordering="parent",
    )
    def is_reply(self, obj):
        return "✓" if obj.parent else "✗"

    @admin.display(description="Replies")
    def replies_count(self, obj):
        count = obj.replies.filter(status="approved").count()
        if count > 0:
            return format_html("<strong>{}</strong>", count)
        return "0"

    @admin.action(description="Approve selected comments")
    def approve_comments(self, request, queryset):
        count = 0
        for comment in queryset:
            if comment.status != "approved":
                comment.approve(user=request.user)
                count += 1
        self.message_user(request, f"{count} comments approved.")

    @admin.action(description="Reject selected comments")
    def reject_comments(self, request, queryset):
        count = 0
        for comment in queryset:
            if comment.status != "rejected":
                comment.reject(user=request.user)
                count += 1
        self.message_user(request, f"{count} comments rejected.")

    @admin.action(description="Mark selected as spam")
    def mark_as_spam(self, request, queryset):
        count = 0
        for comment in queryset:
            if comment.status != "spam":
                comment.mark_as_spam(user=request.user)
                count += 1
        self.message_user(request, f"{count} comments marked as spam.")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related("author", "parent", "moderated_by").annotate(reply_count=Count("replies"))

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(KnowledgeGraphScreenshot)
class KnowledgeGraphScreenshotAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "get_thumbnail",
        "created_at",
        "updated_at",
        "get_hash_display",
        "image_size",
    ]

    list_filter = ["created_at", "updated_at"]

    readonly_fields = [
        "get_preview",
        "graph_data_hash",
        "created_at",
        "updated_at",
        "get_image_url",
    ]

    fieldsets = (
        ("Screenshot", {"fields": ("get_preview", "image", "get_image_url")}),
        (
            "Metadata",
            {
                "fields": ("graph_data_hash", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    actions = ["regenerate_screenshot"]

    @admin.display(description="Thumbnail")
    def get_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="100" height="60" style="border-radius: 4px; object-fit: cover;" />',
                obj.image.url,
            )
        return "-"

    @admin.display(description="Preview")
    def get_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width: 800px; height: auto; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
                obj.image.url,
            )
        return "No screenshot available"

    @admin.display(
        description="Graph Hash",
        ordering="graph_data_hash",
    )
    def get_hash_display(self, obj):
        if obj.graph_data_hash:
            return format_html(
                '<code style="background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace;">{}</code>',
                obj.graph_data_hash[:8],
            )
        return "-"

    @admin.display(description="Image URL")
    def get_image_url(self, obj):
        if obj.image:
            return format_html(
                '<input type="text" value="{}" readonly style="width: 400px;" onclick="this.select();" />',
                obj.image.url,
            )
        return "-"

    @admin.display(description="File Size")
    def image_size(self, obj):
        if obj.image:
            try:
                size_bytes = obj.image.size
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.1f} KB"
                else:
                    return f"{size_bytes / (1024 * 1024):.1f} MB"
            except Exception:
                # Catch any file access errors and return placeholder
                return "-"
        return "-"

    @admin.action(description="Regenerate knowledge graph screenshot")
    def regenerate_screenshot(self, request, queryset):
        from django.contrib import messages
        from django.core.management import call_command

        try:
            call_command("generate_knowledge_graph_screenshot")
            messages.success(request, "Knowledge graph screenshot has been regenerated successfully.")
        except Exception as e:
            messages.error(request, f"Error regenerating screenshot: {str(e)}")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
