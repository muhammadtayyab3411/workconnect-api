from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta

class CustomUserManager(BaseUserManager):
    """Custom user manager that uses email instead of username"""
    
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        # Set username to email to avoid constraint issues
        extra_fields.setdefault('username', email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        # Set default values for required fields if not provided
        extra_fields.setdefault('first_name', 'Admin')
        extra_fields.setdefault('last_name', 'User')
        extra_fields.setdefault('role', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    ROLE_CHOICES = [
        ('client', 'Client'),
        ('worker', 'Worker'),
        ('admin', 'Admin'),
    ]
    
    # Override username to allow null/blank since we use email for authentication
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='client')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    
    # New fields for profile enhancement
    bio = models.TextField(blank=True, null=True, help_text="About/Bio section")
    skills = models.JSONField(default=list, blank=True, help_text="Array of skills")
    languages = models.JSONField(default=list, blank=True, help_text="Array of languages spoken")
    years_of_experience = models.PositiveIntegerField(null=True, blank=True, help_text="Years of professional experience")
    experience_description = models.TextField(blank=True, null=True, help_text="Detailed experience description")
    
    # Rating system
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)
    total_completed_jobs = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Use custom manager
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    def save(self, *args, **kwargs):
        # Set username to email if not provided to avoid constraint issues
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def rating_display(self):
        """Return formatted rating display like '4.9 / 5.0'"""
        if self.total_reviews > 0:
            return f"{self.average_rating} / 5.0"
        return "No reviews yet"
    
    @property 
    def experience_display(self):
        """Return formatted experience display"""
        if self.years_of_experience:
            years = f"{self.years_of_experience}+ years of professional experience"
            if self.experience_description:
                return f"{years} - {self.experience_description}"
            return years
        elif self.experience_description:
            return self.experience_description
        return "Experience not specified"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    
    def is_expired(self):
        """Check if token is expired (24 hours)"""
        return timezone.now() > self.created_at + timedelta(hours=24)
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        return not self.used and not self.is_expired()
    
    def __str__(self):
        return f"Password reset token for {self.user.email}"
    
    class Meta:
        ordering = ['-created_at']


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)
    
    def is_expired(self):
        """Check if token is expired (24 hours)"""
        return timezone.now() > self.created_at + timedelta(hours=24)
    
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        return not self.used and not self.is_expired()
    
    def __str__(self):
        return f"Email verification token for {self.user.email}"
    
    class Meta:
        ordering = ['-created_at']


class Document(models.Model):
    DOCUMENT_TYPES = [
        ('national_id', 'National ID'),
        ('address_proof', 'Address Proof'),
        ('license', 'Professional License'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('manual_review', 'Manual Review'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    document_file = models.FileField(upload_to='documents/%Y/%m/%d/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Verification details from Gemini
    verification_data = models.JSONField(null=True, blank=True)  # Store Gemini response
    confidence_score = models.FloatField(null=True, blank=True)
    verification_notes = models.TextField(blank=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['user', 'document_type']  # One document per type per user
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_document_type_display()} - {self.status}"
    
    def save(self, *args, **kwargs):
        if self.status in ['verified', 'rejected'] and not self.verified_at:
            self.verified_at = timezone.now()
        super().save(*args, **kwargs)


class JobCategory(models.Model):
    """Job categories for organizing jobs"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name for UI")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Job Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Job(models.Model):
    """Job postings model"""
    
    JOB_TYPE_CHOICES = [
        ('one-time', 'One-time'),
        ('recurring', 'Recurring'),
        ('urgent', 'Urgent'),
    ]
    
    PAYMENT_TYPE_CHOICES = [
        ('fixed', 'Fixed Price'),
        ('hourly', 'Hourly Rate'),
    ]
    
    DURATION_CHOICES = [
        ('under-1-hour', 'Under 1 hour'),
        ('1-2-hours', '1-2 hours'),
        ('2-4-hours', '2-4 hours'),
        ('4-8-hours', '4-8 hours'),
        ('full-day', 'Full day (8+ hours)'),
        ('multi-day', 'Multi-day project'),
        ('1-week', 'About 1 week'),
        ('ongoing', 'Ongoing'),
    ]
    
    EXPERIENCE_LEVEL_CHOICES = [
        ('any', 'Any Level'),
        ('beginner', 'Beginner'),
        ('experienced', 'Experienced'),
        ('expert', 'Expert'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    title = models.CharField(max_length=200)
    category = models.ForeignKey(JobCategory, on_delete=models.CASCADE, related_name='jobs')
    description = models.TextField()
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES, default='one-time')
    urgent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Location
    address = models.TextField()
    city = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Schedule & Duration
    start_date = models.DateField(null=True, blank=True)
    duration = models.CharField(max_length=20, choices=DURATION_CHOICES, null=True, blank=True)
    flexible_schedule = models.BooleanField(default=False)
    
    # Budget & Payment
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPE_CHOICES, default='fixed')
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    budget_currency = models.CharField(max_length=3, default='USD')
    
    # Requirements
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVEL_CHOICES, default='any')
    special_requirements = models.TextField(blank=True)
    
    # Metadata
    views_count = models.PositiveIntegerField(default=0)
    applications_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['city', 'status']),
            models.Index(fields=['urgent', 'status']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.client.full_name}"
    
    @property
    def is_published(self):
        return self.status in ['open', 'in_progress', 'completed']
    
    @property
    def budget_display(self):
        if self.payment_type == 'hourly':
            return f"{self.budget_currency} {self.budget}/hr"
        return f"{self.budget_currency} {self.budget}"
    
    @property
    def posted_time_ago(self):
        """Return human-readable time since posting"""
        from django.utils.timesince import timesince
        if self.published_at:
            return f"{timesince(self.published_at)} ago"
        return f"{timesince(self.created_at)} ago"
    
    def save(self, *args, **kwargs):
        # Set published_at when status changes to open
        if self.status == 'open' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class JobImage(models.Model):
    """Images for job postings"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='job_images/%Y/%m/%d/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'id']
    
    def __str__(self):
        return f"Image for {self.job.title}"


class Bid(models.Model):
    """Bid/Application model for workers to apply to jobs"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    # Basic Information
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='bids')
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids')
    
    # Bid Details
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Proposed price for the job")
    availability = models.CharField(max_length=200, help_text="When can you start/your availability")
    proposal = models.TextField(help_text="Your proposal/cover letter")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    response_at = models.DateTimeField(null=True, blank=True, help_text="When client responded")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-submitted_at']
        unique_together = ['job', 'worker']  # One bid per worker per job
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['worker', 'status']),
            models.Index(fields=['status', 'submitted_at']),
        ]
    
    def __str__(self):
        return f"Bid by {self.worker.full_name} for {self.job.title}"
    
    @property
    def price_display(self):
        """Return formatted price display"""
        return f"{self.job.budget_currency} {self.price}"
    
    @property
    def status_display(self):
        """Return formatted status display"""
        return self.get_status_display()
    
    @property
    def job_title(self):
        """Return job title for easy access"""
        return self.job.title
    
    @property
    def worker_name(self):
        """Return worker name for easy access"""
        return self.worker.full_name
    
    @property
    def worker_email(self):
        """Return worker email for easy access"""
        return self.worker.email
    
    def save(self, *args, **kwargs):
        # Set response_at when status changes from pending
        if self.pk:  # Only for updates, not new creations
            try:
                old_bid = Bid.objects.get(pk=self.pk)
                if old_bid.status == 'pending' and self.status != 'pending':
                    self.response_at = timezone.now()
            except Bid.DoesNotExist:
                # This shouldn't happen, but handle gracefully
                pass
        super().save(*args, **kwargs)


class BidDocument(models.Model):
    """Documents attached to bids (portfolio, certificates, etc.)"""
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='bid_documents/%Y/%m/%d/')
    name = models.CharField(max_length=200, help_text="Document name/title")
    description = models.CharField(max_length=500, blank=True, help_text="Document description")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"Document: {self.name} for bid {self.bid.id}"


class WorkSample(models.Model):
    """Work samples/portfolio items attached to bids"""
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='work_samples')
    image = models.ImageField(upload_to='work_samples/%Y/%m/%d/')
    title = models.CharField(max_length=200, help_text="Sample title")
    description = models.CharField(max_length=500, blank=True, help_text="Sample description")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['uploaded_at']
    
    def __str__(self):
        return f"Work sample: {self.title} for bid {self.bid.id}"
