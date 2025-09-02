from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.generic import DetailView, ListView
from django.template.loader import render_to_string
from django.utils.text import slugify
from .models import (
    Resume, PersonalInfo, WorkExperience, Achievement, Education,
    Skill, Project, Certification, Award, Publication, Language,
    Reference, CustomSection
)
import json


class ResumeListView(ListView):
    """List all active resumes"""
    model = Resume
    template_name = 'resume/resume_list.html'
    context_object_name = 'resumes'
    
    def get_queryset(self):
        return Resume.objects.filter(is_active=True)


class ResumeDetailView(DetailView):
    """Display a full resume"""
    model = Resume
    template_name = 'resume/resume_detail.html'
    context_object_name = 'resume'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        resume = self.object
        
        # Organize skills by category
        skills_by_category = {}
        for skill in resume.skills.all():
            category = skill.get_category_display()
            if category not in skills_by_category:
                skills_by_category[category] = []
            skills_by_category[category].append(skill)
        
        context['skills_by_category'] = skills_by_category
        
        # Get work experiences with their achievements
        work_experiences = resume.work_experiences.prefetch_related('achievements')
        context['work_experiences'] = work_experiences
        
        # Get education
        context['education'] = resume.education.all()
        
        # Get projects
        context['projects'] = resume.projects.all()
        
        # Get certifications
        context['certifications'] = resume.certifications.all()
        
        # Get awards
        context['awards'] = resume.awards.all()
        
        # Get publications
        context['publications'] = resume.publications.all()
        
        # Get languages
        context['languages'] = resume.languages.all()
        
        # Get custom sections
        context['custom_sections'] = resume.custom_sections.all()
        
        return context


def resume_json_view(request, slug):
    """Return resume data as JSON for API consumption"""
    resume = get_object_or_404(Resume, slug=slug, is_active=True)
    
    # Build the JSON structure
    data = {
        'title': resume.title,
        'personal_info': {},
        'work_experiences': [],
        'education': [],
        'skills': [],
        'projects': [],
        'certifications': [],
        'awards': [],
        'publications': [],
        'languages': [],
        'custom_sections': []
    }
    
    # Personal Info
    if hasattr(resume, 'personal_info'):
        pi = resume.personal_info
        data['personal_info'] = {
            'full_name': pi.full_name,
            'title': pi.title,
            'email': pi.email,
            'phone': pi.phone,
            'location': pi.location,
            'linkedin': pi.linkedin,
            'github': pi.github,
            'website': pi.website,
            'summary': pi.summary
        }
    
    # Work Experiences
    for exp in resume.work_experiences.all():
        exp_data = {
            'company': exp.company,
            'position': exp.position,
            'location': exp.location,
            'start_date': exp.start_date.strftime('%B %Y') if exp.start_date else '',
            'end_date': exp.end_date.strftime('%B %Y') if exp.end_date else 'Present',
            'is_current': exp.is_current,
            'description': exp.description,
            'achievements': [ach.description for ach in exp.achievements.all()]
        }
        data['work_experiences'].append(exp_data)
    
    # Education
    for edu in resume.education.all():
        edu_data = {
            'institution': edu.institution,
            'degree': edu.get_degree_type_display(),
            'field_of_study': edu.field_of_study,
            'location': edu.location,
            'start_date': edu.start_date.strftime('%Y') if edu.start_date else '',
            'end_date': edu.end_date.strftime('%Y') if edu.end_date else '',
            'gpa': str(edu.gpa) if edu.gpa else '',
            'honors': edu.honors,
            'relevant_coursework': edu.relevant_coursework.split(',') if edu.relevant_coursework else []
        }
        data['education'].append(edu_data)
    
    # Skills by category
    skills_by_category = {}
    for skill in resume.skills.all():
        category = skill.get_category_display()
        if category not in skills_by_category:
            skills_by_category[category] = []
        skills_by_category[category].append({
            'name': skill.name,
            'proficiency': skill.get_proficiency_display(),
            'years_of_experience': skill.years_of_experience
        })
    data['skills'] = skills_by_category
    
    # Projects
    for project in resume.projects.all():
        proj_data = {
            'title': project.title,
            'description': project.description,
            'technologies': project.technologies.split(',') if project.technologies else [],
            'url': project.url,
            'start_date': project.start_date.strftime('%B %Y') if project.start_date else '',
            'end_date': project.end_date.strftime('%B %Y') if project.end_date else '',
            'is_ongoing': project.is_ongoing
        }
        data['projects'].append(proj_data)
    
    # Certifications
    for cert in resume.certifications.all():
        cert_data = {
            'name': cert.name,
            'issuing_organization': cert.issuing_organization,
            'issue_date': cert.issue_date.strftime('%B %Y') if cert.issue_date else '',
            'expiry_date': cert.expiry_date.strftime('%B %Y') if cert.expiry_date else '',
            'is_valid': cert.is_valid,
            'credential_url': cert.credential_url
        }
        data['certifications'].append(cert_data)
    
    # Awards
    for award in resume.awards.all():
        award_data = {
            'title': award.title,
            'issuer': award.issuer,
            'date': award.date.strftime('%B %Y') if award.date else '',
            'description': award.description
        }
        data['awards'].append(award_data)
    
    # Publications
    for pub in resume.publications.all():
        pub_data = {
            'title': pub.title,
            'authors': pub.authors,
            'publication_name': pub.publication_name,
            'date': pub.date.strftime('%B %Y') if pub.date else '',
            'url': pub.url,
            'doi': pub.doi,
            'description': pub.description
        }
        data['publications'].append(pub_data)
    
    # Languages
    for lang in resume.languages.all():
        lang_data = {
            'name': lang.name,
            'proficiency': lang.get_proficiency_display()
        }
        data['languages'].append(lang_data)
    
    # Custom Sections
    for section in resume.custom_sections.all():
        section_data = {
            'title': section.title,
            'content': section.content
        }
        data['custom_sections'].append(section_data)
    
    return JsonResponse(data, json_dumps_params={'indent': 2})


def resume_pdf_view(request, slug):
    """Generate PDF version of resume (placeholder for future implementation)"""
    resume = get_object_or_404(Resume, slug=slug, is_active=True)
    
    # For now, just return a message
    # In the future, you can use libraries like weasyprint or reportlab to generate PDFs
    return HttpResponse(
        f"PDF generation for '{resume.title}' is not yet implemented. "
        "This will be available in a future update.",
        content_type='text/plain'
    )


def resume_default_view(request):
    """Redirect to the most recently updated active resume"""
    resume = Resume.objects.filter(is_active=True).first()
    if resume:
        return ResumeDetailView.as_view()(request, slug=resume.slug)
    else:
        return render(request, 'resume/no_resume.html')