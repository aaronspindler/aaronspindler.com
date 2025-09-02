from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Resume, PersonalInfo, WorkExperience, Achievement, Education, 
    Skill, Project, Certification, Award, Publication, Language, 
    Reference, CustomSection
)


class PersonalInfoInline(admin.StackedInline):
    model = PersonalInfo
    extra = 0
    fields = (
        ('first_name', 'last_name'),
        'title',
        ('email', 'phone'),
        'location',
        ('linkedin', 'github', 'website'),
        'summary'
    )


class AchievementInline(admin.TabularInline):
    model = Achievement
    extra = 1
    fields = ('description', 'order')


class WorkExperienceInline(admin.StackedInline):
    model = WorkExperience
    extra = 0
    fields = (
        ('company', 'position'),
        'location',
        ('start_date', 'end_date', 'is_current'),
        'description',
        'order'
    )
    readonly_fields = ('is_current',)


class EducationInline(admin.StackedInline):
    model = Education
    extra = 0
    fields = (
        'institution',
        ('degree_type', 'field_of_study'),
        'location',
        ('start_date', 'end_date'),
        ('gpa', 'honors'),
        'relevant_coursework',
        'order'
    )


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1
    fields = ('name', 'category', 'proficiency', 'years_of_experience', 'order')


class ProjectInline(admin.StackedInline):
    model = Project
    extra = 0
    fields = (
        'title',
        'description',
        'technologies',
        'url',
        ('start_date', 'end_date', 'is_ongoing'),
        'order'
    )


class CertificationInline(admin.TabularInline):
    model = Certification
    extra = 0
    fields = ('name', 'issuing_organization', 'issue_date', 'expiry_date', 'credential_url', 'order')


class AwardInline(admin.TabularInline):
    model = Award
    extra = 0
    fields = ('title', 'issuer', 'date', 'description', 'order')


class PublicationInline(admin.StackedInline):
    model = Publication
    extra = 0
    fields = (
        'title',
        'authors',
        'publication_name',
        'date',
        ('url', 'doi'),
        'description',
        'order'
    )


class LanguageInline(admin.TabularInline):
    model = Language
    extra = 0
    fields = ('name', 'proficiency', 'order')


class ReferenceInline(admin.StackedInline):
    model = Reference
    extra = 0
    fields = (
        ('name', 'title'),
        'company',
        ('email', 'phone'),
        'relationship',
        'notes',
        'order'
    )


class CustomSectionInline(admin.StackedInline):
    model = CustomSection
    extra = 0
    fields = ('title', 'content', 'order')


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'updated_at', 'created_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('title', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
    inlines = [
        PersonalInfoInline,
        WorkExperienceInline,
        EducationInline,
        SkillInline,
        ProjectInline,
        CertificationInline,
        AwardInline,
        PublicationInline,
        LanguageInline,
        ReferenceInline,
        CustomSectionInline,
    ]
    
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = ('position', 'company', 'start_date', 'end_date', 'is_current', 'resume')
    list_filter = ('is_current', 'resume', 'start_date')
    search_fields = ('position', 'company', 'description')
    date_hierarchy = 'start_date'
    inlines = [AchievementInline]
    
    fieldsets = (
        (None, {
            'fields': ('resume', 'company', 'position', 'location')
        }),
        ('Dates', {
            'fields': (('start_date', 'end_date'), 'is_current')
        }),
        ('Details', {
            'fields': ('description', 'order')
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        return ['is_current']


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('institution', 'degree_type', 'field_of_study', 'end_date', 'gpa', 'resume')
    list_filter = ('degree_type', 'resume')
    search_fields = ('institution', 'field_of_study', 'relevant_coursework')
    date_hierarchy = 'end_date'
    
    fieldsets = (
        (None, {
            'fields': ('resume', 'institution', 'degree_type', 'field_of_study', 'location')
        }),
        ('Dates', {
            'fields': (('start_date', 'end_date'),)
        }),
        ('Academic Performance', {
            'fields': ('gpa', 'honors', 'relevant_coursework')
        }),
        ('Display', {
            'fields': ('order',)
        }),
    )


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'proficiency', 'years_of_experience', 'resume')
    list_filter = ('category', 'proficiency', 'resume')
    search_fields = ('name',)
    ordering = ('category', 'order', 'name')
    
    fieldsets = (
        (None, {
            'fields': ('resume', 'name', 'category')
        }),
        ('Proficiency', {
            'fields': ('proficiency', 'years_of_experience')
        }),
        ('Display', {
            'fields': ('order',)
        }),
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_date', 'end_date', 'is_ongoing', 'resume')
    list_filter = ('is_ongoing', 'resume')
    search_fields = ('title', 'description', 'technologies')
    date_hierarchy = 'start_date'
    
    fieldsets = (
        (None, {
            'fields': ('resume', 'title', 'description')
        }),
        ('Technologies & Links', {
            'fields': ('technologies', 'url')
        }),
        ('Timeline', {
            'fields': (('start_date', 'end_date'), 'is_ongoing')
        }),
        ('Display', {
            'fields': ('order',)
        }),
    )


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'issuing_organization', 'issue_date', 'expiry_date', 'is_valid_display', 'resume')
    list_filter = ('issuing_organization', 'resume')
    search_fields = ('name', 'issuing_organization', 'credential_id')
    date_hierarchy = 'issue_date'
    
    def is_valid_display(self, obj):
        if obj.is_valid:
            return format_html('<span style="color: green;">✓ Valid</span>')
        return format_html('<span style="color: red;">✗ Expired</span>')
    is_valid_display.short_description = 'Status'
    
    fieldsets = (
        (None, {
            'fields': ('resume', 'name', 'issuing_organization')
        }),
        ('Dates', {
            'fields': (('issue_date', 'expiry_date'),)
        }),
        ('Credentials', {
            'fields': ('credential_id', 'credential_url')
        }),
        ('Display', {
            'fields': ('order',)
        }),
    )


@admin.register(Award)
class AwardAdmin(admin.ModelAdmin):
    list_display = ('title', 'issuer', 'date', 'resume')
    list_filter = ('resume', 'issuer')
    search_fields = ('title', 'issuer', 'description')
    date_hierarchy = 'date'


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ('title', 'publication_name', 'date', 'resume')
    list_filter = ('resume', 'publication_name')
    search_fields = ('title', 'authors', 'publication_name', 'description')
    date_hierarchy = 'date'


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'proficiency', 'resume')
    list_filter = ('proficiency', 'resume')
    search_fields = ('name',)


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'company', 'relationship', 'resume')
    list_filter = ('resume', 'company')
    search_fields = ('name', 'title', 'company', 'relationship')
    
    fieldsets = (
        (None, {
            'fields': ('resume', 'name', 'title', 'company')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone')
        }),
        ('Relationship', {
            'fields': ('relationship', 'notes')
        }),
        ('Display', {
            'fields': ('order',)
        }),
    )


@admin.register(CustomSection)
class CustomSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'resume', 'order')
    list_filter = ('resume',)
    search_fields = ('title', 'content')
    ordering = ('order', 'title')