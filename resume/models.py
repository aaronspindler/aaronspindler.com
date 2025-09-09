from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone


class Resume(models.Model):
    """Main resume model that ties everything together"""
    title = models.CharField(max_length=200, help_text="Resume title/version (e.g., 'Software Engineer Resume')")
    slug = models.SlugField(unique=True, help_text="URL-friendly version of title")
    is_active = models.BooleanField(default=True, help_text="Whether this resume version is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.title


class PersonalInfo(models.Model):
    """Personal/Contact Information"""
    resume = models.OneToOneField(Resume, on_delete=models.CASCADE, related_name='personal_info')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    title = models.CharField(max_length=200, help_text="Professional title (e.g., 'Senior Software Engineer')")
    email = models.EmailField()
    phone_regex = RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    linkedin = models.URLField(blank=True, help_text="LinkedIn profile URL")
    github = models.URLField(blank=True, help_text="GitHub profile URL")
    website = models.URLField(blank=True, help_text="Personal website URL")
    location = models.CharField(max_length=200, blank=True, help_text="City, State/Country")
    summary = models.TextField(blank=True, help_text="Professional summary/objective")
    
    class Meta:
        verbose_name_plural = "Personal Information"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class WorkExperience(models.Model):
    """Professional work experience"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='work_experiences')
    company = models.CharField(max_length=200)
    position = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank if current position")
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True, help_text="Job description/responsibilities")
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    
    class Meta:
        ordering = ['-is_current', '-start_date']
        verbose_name_plural = "Work Experiences"
    
    def __str__(self):
        return f"{self.position} at {self.company}"
    
    def save(self, *args, **kwargs):
        # Automatically set is_current based on end_date
        if not self.end_date:
            self.is_current = True
        else:
            self.is_current = False
        super().save(*args, **kwargs)
    
    @property
    def duration(self):
        """Calculate duration of employment"""
        end = self.end_date if self.end_date else timezone.now().date()
        delta = end - self.start_date
        years = delta.days // 365
        months = (delta.days % 365) // 30
        if years > 0:
            return f"{years} year{'s' if years > 1 else ''}, {months} month{'s' if months > 1 else ''}"
        return f"{months} month{'s' if months > 1 else ''}"


class Achievement(models.Model):
    """Achievements/accomplishments for work experience"""
    work_experience = models.ForeignKey(WorkExperience, on_delete=models.CASCADE, related_name='achievements')
    description = models.TextField()
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return self.description[:100]


class Education(models.Model):
    """Educational background"""
    DEGREE_CHOICES = [
        ('HIGH_SCHOOL', 'High School Diploma'),
        ('ASSOCIATE', "Associate's Degree"),
        ('BACHELOR', "Bachelor's Degree"),
        ('MASTER', "Master's Degree"),
        ('PHD', 'Ph.D.'),
        ('CERTIFICATE', 'Certificate'),
        ('BOOTCAMP', 'Bootcamp'),
        ('OTHER', 'Other'),
    ]
    
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='education')
    institution = models.CharField(max_length=200)
    degree_type = models.CharField(max_length=20, choices=DEGREE_CHOICES)
    field_of_study = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, 
                              validators=[MinValueValidator(0.0), MaxValueValidator(4.0)],
                              help_text="GPA on a 4.0 scale")
    honors = models.CharField(max_length=200, blank=True, help_text="e.g., 'Magna Cum Laude', 'Dean's List'")
    relevant_coursework = models.TextField(blank=True, help_text="Comma-separated list of relevant courses")
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', '-end_date']
        verbose_name_plural = "Education"
    
    def __str__(self):
        return f"{self.degree_type} - {self.institution}"


class Skill(models.Model):
    """Individual skills"""
    SKILL_CATEGORIES = [
        ('PROGRAMMING', 'Programming Languages'),
        ('FRAMEWORK', 'Frameworks & Libraries'),
        ('DATABASE', 'Databases'),
        ('TOOL', 'Tools & Technologies'),
        ('CLOUD', 'Cloud & DevOps'),
        ('SOFT', 'Soft Skills'),
        ('LANGUAGE', 'Languages'),
        ('OTHER', 'Other'),
    ]
    
    PROFICIENCY_LEVELS = [
        ('BEGINNER', 'Beginner'),
        ('INTERMEDIATE', 'Intermediate'),
        ('ADVANCED', 'Advanced'),
        ('EXPERT', 'Expert'),
    ]
    
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=SKILL_CATEGORIES)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_LEVELS, default='INTERMEDIATE')
    years_of_experience = models.IntegerField(null=True, blank=True, 
                                             validators=[MinValueValidator(0), MaxValueValidator(50)])
    order = models.IntegerField(default=0, help_text="Display order within category")
    
    class Meta:
        ordering = ['category', 'order', 'name']
        unique_together = ['resume', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"


class Project(models.Model):
    """Personal or professional projects"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=200)
    description = models.TextField()
    technologies = models.CharField(max_length=500, blank=True, help_text="Comma-separated list of technologies used")
    url = models.URLField(blank=True, help_text="Project URL (GitHub, live demo, etc.)")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_ongoing = models.BooleanField(default=False)
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', '-start_date']
    
    def __str__(self):
        return self.title


class Certification(models.Model):
    """Professional certifications"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='certifications')
    name = models.CharField(max_length=200)
    issuing_organization = models.CharField(max_length=200)
    issue_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True, help_text="Leave blank if no expiry")
    credential_id = models.CharField(max_length=100, blank=True)
    credential_url = models.URLField(blank=True, help_text="URL to verify certification")
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', '-issue_date']
    
    def __str__(self):
        return f"{self.name} - {self.issuing_organization}"
    
    @property
    def is_valid(self):
        """Check if certification is still valid"""
        if not self.expiry_date:
            return True
        return self.expiry_date >= timezone.now().date()


class Award(models.Model):
    """Awards and honors"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='awards')
    title = models.CharField(max_length=200)
    issuer = models.CharField(max_length=200)
    date = models.DateField()
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', '-date']
    
    def __str__(self):
        return f"{self.title} - {self.issuer}"


class Publication(models.Model):
    """Publications, articles, papers"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='publications')
    title = models.CharField(max_length=300)
    authors = models.CharField(max_length=500, help_text="List of authors")
    publication_name = models.CharField(max_length=200, blank=True, help_text="Journal, conference, blog, etc.")
    date = models.DateField()
    url = models.URLField(blank=True)
    doi = models.CharField(max_length=100, blank=True, help_text="Digital Object Identifier")
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', '-date']
    
    def __str__(self):
        return self.title


class Language(models.Model):
    """Language proficiencies"""
    PROFICIENCY_LEVELS = [
        ('NATIVE', 'Native'),
        ('FLUENT', 'Fluent'),
        ('PROFESSIONAL', 'Professional Working'),
        ('LIMITED', 'Limited Working'),
        ('ELEMENTARY', 'Elementary'),
    ]
    
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='languages')
    name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY_LEVELS)
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', 'name']
        unique_together = ['resume', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_proficiency_display()})"


class Reference(models.Model):
    """Professional references"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='references')
    name = models.CharField(max_length=200)
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=17, blank=True)
    relationship = models.CharField(max_length=200, blank=True, help_text="e.g., 'Former Manager', 'Colleague'")
    notes = models.TextField(blank=True, help_text="Private notes about this reference")
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.title} at {self.company}"


class CustomSection(models.Model):
    """Custom sections for additional information"""
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='custom_sections')
    title = models.CharField(max_length=200)
    content = models.TextField()
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title

