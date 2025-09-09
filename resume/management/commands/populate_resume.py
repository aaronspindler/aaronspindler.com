from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from resume.models import (
    Resume, PersonalInfo, WorkExperience, Achievement, Education,
    Skill, Project, Certification, Award, Publication, Language,
    Reference, CustomSection
)


class Command(BaseCommand):
    help = 'Populate resume models with data'

    def handle(self, *args, **options):
        self.stdout.write('Starting resume population...')
        
        # Delete existing resume data (optional - comment out if you want to keep existing data)
        Resume.objects.filter(slug='aaron-spindler-2023').delete()
        
        # Create main resume
        resume = Resume.objects.create(
            title='Aaron Spindler - Software Engineer',
            slug='aaron-spindler-2023',
            is_active=True
        )
        self.stdout.write(self.style.SUCCESS(f'Created resume: {resume.title}'))
        
        # Personal Information
        personal_info = PersonalInfo.objects.create(
            resume=resume,
            first_name='Aaron',
            last_name='Spindler',
            title='Senior Software Engineer',
            email='aaron@example.com',  # Update with your actual email
            phone='+1234567890',  # Update with your actual phone
            linkedin='https://linkedin.com/in/aaronspindler',  # Update with your actual LinkedIn
            github='https://github.com/aaronspindler',  # Update with your actual GitHub
            website='https://aaronspindler.com',
            location='San Francisco, CA',  # Update with your actual location
            summary=(
                'Experienced Software Engineer with a strong background in full-stack development, '
                'cloud architecture, and team leadership. Passionate about building scalable '
                'applications and mentoring junior developers.'
            )
        )
        self.stdout.write(self.style.SUCCESS('Added personal information'))
        
        # Work Experience
        # Job 1 - Most Recent
        exp1 = WorkExperience.objects.create(
            resume=resume,
            company='Tech Company Inc.',
            position='Senior Software Engineer',
            location='San Francisco, CA',
            start_date=date(2021, 6, 1),
            end_date=None,  # Current position
            description=(
                'Lead development of cloud-native applications and mentor junior team members. '
                'Architect scalable solutions and implement best practices for CI/CD.'
            ),
            order=1
        )
        
        # Achievements for Job 1
        Achievement.objects.create(
            work_experience=exp1,
            description='Led migration of monolithic application to microservices architecture, improving scalability by 300%',
            order=1
        )
        Achievement.objects.create(
            work_experience=exp1,
            description='Implemented automated testing pipeline, reducing bug escape rate by 45%',
            order=2
        )
        Achievement.objects.create(
            work_experience=exp1,
            description='Mentored 5 junior developers, with 3 promoted to mid-level positions',
            order=3
        )
        
        # Job 2
        exp2 = WorkExperience.objects.create(
            resume=resume,
            company='StartupXYZ',
            position='Full Stack Developer',
            location='San Francisco, CA',
            start_date=date(2019, 3, 1),
            end_date=date(2021, 5, 31),
            description=(
                'Developed and maintained web applications using React and Django. '
                'Collaborated with product team to deliver features on tight deadlines.'
            ),
            order=2
        )
        
        Achievement.objects.create(
            work_experience=exp2,
            description='Built real-time collaboration features serving 10,000+ concurrent users',
            order=1
        )
        Achievement.objects.create(
            work_experience=exp2,
            description='Reduced API response time by 60% through database optimization',
            order=2
        )
        
        # Job 3
        exp3 = WorkExperience.objects.create(
            resume=resume,
            company='Software Solutions Ltd.',
            position='Junior Developer',
            location='New York, NY',
            start_date=date(2017, 7, 1),
            end_date=date(2019, 2, 28),
            description='Contributed to development of enterprise software solutions.',
            order=3
        )
        
        Achievement.objects.create(
            work_experience=exp3,
            description='Developed automated reporting system saving 20 hours per week',
            order=1
        )
        
        self.stdout.write(self.style.SUCCESS('Added work experience'))
        
        # Education
        Education.objects.create(
            resume=resume,
            institution='University of California, Berkeley',
            degree_type='BACHELOR',
            field_of_study='Computer Science',
            location='Berkeley, CA',
            start_date=date(2013, 9, 1),
            end_date=date(2017, 5, 31),
            gpa=3.8,
            honors='Magna Cum Laude',
            relevant_coursework='Data Structures, Algorithms, Machine Learning, Database Systems, Software Engineering',
            order=1
        )
        
        self.stdout.write(self.style.SUCCESS('Added education'))
        
        # Skills
        # Programming Languages
        programming_skills = [
            ('Python', 'EXPERT', 6),
            ('JavaScript', 'ADVANCED', 5),
            ('TypeScript', 'ADVANCED', 4),
            ('Java', 'INTERMEDIATE', 3),
            ('Go', 'INTERMEDIATE', 2),
            ('SQL', 'ADVANCED', 5),
        ]
        
        for i, (name, prof, years) in enumerate(programming_skills):
            Skill.objects.create(
                resume=resume,
                name=name,
                category='PROGRAMMING',
                proficiency=prof,
                years_of_experience=years,
                order=i
            )
        
        # Frameworks & Libraries
        framework_skills = [
            ('Django', 'EXPERT', 5),
            ('React', 'ADVANCED', 4),
            ('Next.js', 'ADVANCED', 3),
            ('FastAPI', 'ADVANCED', 3),
            ('Node.js', 'INTERMEDIATE', 3),
            ('Spring Boot', 'INTERMEDIATE', 2),
        ]
        
        for i, (name, prof, years) in enumerate(framework_skills):
            Skill.objects.create(
                resume=resume,
                name=name,
                category='FRAMEWORK',
                proficiency=prof,
                years_of_experience=years,
                order=i
            )
        
        # Databases
        database_skills = [
            ('PostgreSQL', 'ADVANCED', 5),
            ('MongoDB', 'INTERMEDIATE', 3),
            ('Redis', 'INTERMEDIATE', 3),
            ('Elasticsearch', 'INTERMEDIATE', 2),
        ]
        
        for i, (name, prof, years) in enumerate(database_skills):
            Skill.objects.create(
                resume=resume,
                name=name,
                category='DATABASE',
                proficiency=prof,
                years_of_experience=years,
                order=i
            )
        
        # Cloud & DevOps
        cloud_skills = [
            ('AWS', 'ADVANCED', 4),
            ('Docker', 'ADVANCED', 4),
            ('Kubernetes', 'INTERMEDIATE', 2),
            ('CI/CD', 'ADVANCED', 4),
            ('Terraform', 'INTERMEDIATE', 2),
        ]
        
        for i, (name, prof, years) in enumerate(cloud_skills):
            Skill.objects.create(
                resume=resume,
                name=name,
                category='CLOUD',
                proficiency=prof,
                years_of_experience=years,
                order=i
            )
        
        self.stdout.write(self.style.SUCCESS('Added skills'))
        
        # Projects
        Project.objects.create(
            resume=resume,
            title='Open Source Contribution - Django REST Framework',
            description=(
                'Regular contributor to Django REST Framework. Implemented new authentication '
                'features and fixed critical bugs affecting thousands of users.'
            ),
            technologies='Python, Django, REST APIs, Testing',
            url='https://github.com/encode/django-rest-framework',
            start_date=date(2020, 1, 1),
            is_ongoing=True,
            order=1
        )
        
        Project.objects.create(
            resume=resume,
            title='Personal Portfolio Website',
            description=(
                'Built a modern, responsive portfolio website with blog functionality, '
                'photo galleries, and dynamic resume generation.'
            ),
            technologies='Django, React, PostgreSQL, AWS S3, Tailwind CSS',
            url='https://aaronspindler.com',
            start_date=date(2022, 6, 1),
            end_date=date(2023, 1, 1),
            order=2
        )
        
        Project.objects.create(
            resume=resume,
            title='ML-Powered Code Review Tool',
            description=(
                'Developed a machine learning tool that automatically reviews code '
                'and suggests improvements based on best practices.'
            ),
            technologies='Python, TensorFlow, FastAPI, React, Docker',
            url='https://github.com/aaronspindler/code-reviewer',
            start_date=date(2021, 3, 1),
            end_date=date(2021, 9, 1),
            order=3
        )
        
        self.stdout.write(self.style.SUCCESS('Added projects'))
        
        # Certifications
        Certification.objects.create(
            resume=resume,
            name='AWS Certified Solutions Architect - Associate',
            issuing_organization='Amazon Web Services',
            issue_date=date(2022, 3, 15),
            expiry_date=date(2025, 3, 15),
            credential_id='AWS-123456',
            credential_url='https://aws.amazon.com/verification',
            order=1
        )
        
        Certification.objects.create(
            resume=resume,
            name='Google Cloud Professional Cloud Developer',
            issuing_organization='Google Cloud',
            issue_date=date(2021, 8, 1),
            expiry_date=date(2024, 8, 1),
            credential_id='GCP-789012',
            credential_url='https://cloud.google.com/certification',
            order=2
        )
        
        self.stdout.write(self.style.SUCCESS('Added certifications'))
        
        # Awards
        Award.objects.create(
            resume=resume,
            title='Employee of the Year',
            issuer='Tech Company Inc.',
            date=date(2022, 12, 1),
            description='Recognized for exceptional performance and leadership',
            order=1
        )
        
        Award.objects.create(
            resume=resume,
            title='Hackathon Winner - Best Innovation',
            issuer='TechCrunch Disrupt',
            date=date(2021, 9, 1),
            description='Won first place for developing an AI-powered accessibility tool',
            order=2
        )
        
        self.stdout.write(self.style.SUCCESS('Added awards'))
        
        # Publications (if any)
        Publication.objects.create(
            resume=resume,
            title='Scaling Microservices: Lessons Learned',
            authors='Aaron Spindler, Jane Doe',
            publication_name='Tech Blog',
            date=date(2022, 6, 1),
            url='https://techblog.com/scaling-microservices',
            description='Article on best practices for scaling microservices architecture',
            order=1
        )
        
        self.stdout.write(self.style.SUCCESS('Added publications'))
        
        # Languages
        Language.objects.create(
            resume=resume,
            name='English',
            proficiency='NATIVE',
            order=1
        )
        
        Language.objects.create(
            resume=resume,
            name='Spanish',
            proficiency='PROFESSIONAL',
            order=2
        )
        
        self.stdout.write(self.style.SUCCESS('Added languages'))
        
        # Custom Sections (optional)
        CustomSection.objects.create(
            resume=resume,
            title='Volunteer Experience',
            content=(
                'Code Mentor at CoderDojo (2020-Present): Teaching programming to youth aged 7-17\n'
                'Tech Lead at Habitat for Humanity (2019-2020): Led team building housing management software'
            ),
            order=1
        )
        
        CustomSection.objects.create(
            resume=resume,
            title='Interests',
            content='Photography, Hiking, Open Source Software, Machine Learning, Technical Writing',
            order=2
        )
        
        self.stdout.write(self.style.SUCCESS('Added custom sections'))
        
        # References (usually kept private)
        Reference.objects.create(
            resume=resume,
            name='John Smith',
            title='Engineering Manager',
            company='Tech Company Inc.',
            email='john.smith@techcompany.com',
            phone='+1234567890',
            relationship='Current Manager',
            notes='Excellent reference - worked together for 2+ years',
            order=1
        )
        
        Reference.objects.create(
            resume=resume,
            name='Sarah Johnson',
            title='CTO',
            company='StartupXYZ',
            email='sarah@startupxyz.com',
            relationship='Former Manager',
            notes='Worked together during rapid growth phase',
            order=2
        )
        
        self.stdout.write(self.style.SUCCESS('Added references'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully populated resume data!\n'
            f'View your resume at: /resume/{resume.slug}/\n'
            f'Edit in admin at: /admin/resume/resume/{resume.id}/change/'
        ))
