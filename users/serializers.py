from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, Document, Job, JobCategory, JobImage, Bid, BidDocument, WorkSample

class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    phone_number = serializers.CharField(source='phone', required=False, allow_blank=True)
    profile_picture = serializers.SerializerMethodField()
    rating_display = serializers.ReadOnlyField()
    experience_display = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 
            'role', 'phone_number', 'address', 'date_of_birth', 'profile_picture',
            'bio', 'skills', 'languages', 'years_of_experience', 'experience_description',
            'average_rating', 'total_reviews', 'total_completed_jobs', 'rating_display', 'experience_display',
            'is_verified', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_verified', 'email', 'average_rating', 'total_reviews', 'total_completed_jobs']
    
    def get_profile_picture(self, obj):
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            else:
                # Fallback if no request context
                return obj.profile_picture.url
        return None

class ProfileUpdateSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='phone', required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone_number', 'address', 'date_of_birth',
            'bio', 'skills', 'languages', 'years_of_experience', 'experience_description'
        ]
        # Exclude profile_picture as it has separate upload endpoint
        # Exclude rating fields as they are managed by the system
    
    def validate_first_name(self, value):
        # Only validate if the field is being updated and has a value
        if value is not None and (not value or not value.strip()):
            raise serializers.ValidationError("First name cannot be empty.")
        return value.strip() if value else value
    
    def validate_last_name(self, value):
        # Only validate if the field is being updated and has a value
        if value is not None and (not value or not value.strip()):
            raise serializers.ValidationError("Last name cannot be empty.")
        return value.strip() if value else value
    
    def validate_phone_number(self, value):
        # Phone is optional, but if provided should be valid
        if value and value.strip():
            import re
            # Remove all non-digit characters except + at the beginning
            phone_clean = re.sub(r'[^\d+]', '', value.strip())
            if len(phone_clean) < 10:
                raise serializers.ValidationError("Phone number must be at least 10 digits.")
            # Basic format validation
            if not re.match(r'^[+]?[\d\s\-\(\)]+$', value.strip()):
                raise serializers.ValidationError("Please enter a valid phone number.")
        return value.strip() if value else value
    
    def validate_date_of_birth(self, value):
        if value:
            from datetime import date
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            
            if value > today:
                raise serializers.ValidationError("Date of birth cannot be in the future.")
            if age < 16:
                raise serializers.ValidationError("You must be at least 16 years old.")
            if age > 120:
                raise serializers.ValidationError("Please enter a valid date of birth.")
        return value
    
    def validate_skills(self, value):
        """Validate skills array"""
        if value is not None:
            if not isinstance(value, list):
                raise serializers.ValidationError("Skills must be a list.")
            if len(value) > 20:
                raise serializers.ValidationError("Maximum 20 skills allowed.")
            # Clean up skills - remove empty strings and limit length
            cleaned_skills = []
            for skill in value:
                if isinstance(skill, str) and skill.strip():
                    if len(skill.strip()) > 50:
                        raise serializers.ValidationError("Each skill must be less than 50 characters.")
                    cleaned_skills.append(skill.strip())
            return cleaned_skills
        return value
    
    def validate_languages(self, value):
        """Validate languages array"""
        if value is not None:
            if not isinstance(value, list):
                raise serializers.ValidationError("Languages must be a list.")
            if len(value) > 10:
                raise serializers.ValidationError("Maximum 10 languages allowed.")
            # Clean up languages
            cleaned_languages = []
            for lang in value:
                if isinstance(lang, str) and lang.strip():
                    if len(lang.strip()) > 30:
                        raise serializers.ValidationError("Each language must be less than 30 characters.")
                    cleaned_languages.append(lang.strip())
            return cleaned_languages
        return value
    
    def validate_years_of_experience(self, value):
        """Validate years of experience"""
        if value is not None:
            if value < 0:
                raise serializers.ValidationError("Years of experience cannot be negative.")
            if value > 50:
                raise serializers.ValidationError("Years of experience cannot exceed 50.")
        return value
    
    def validate_bio(self, value):
        """Validate bio"""
        if value and len(value.strip()) > 1000:
            raise serializers.ValidationError("Bio must be less than 1000 characters.")
        return value.strip() if value else value
    
    def validate_experience_description(self, value):
        """Validate experience description"""
        if value and len(value.strip()) > 500:
            raise serializers.ValidationError("Experience description must be less than 500 characters.")
        return value.strip() if value else value

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(source='phone', required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'role', 'phone_number', 
            'password', 'confirm_password'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match.")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            username=validated_data['email'],  # Use email as username
            **validated_data
        )
        user.set_password(password)
        user.save()
        return user 

class DocumentSerializer(serializers.ModelSerializer):
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'document_type', 'document_type_display', 
            'status', 'status_display', 'document_url',
            'confidence_score', 'verification_notes', 
            'uploaded_at', 'verified_at', 'verification_data'
        ]
        read_only_fields = [
            'id', 'status', 'confidence_score', 'verification_notes',
            'uploaded_at', 'verified_at', 'verification_data'
        ]
    
    def get_document_url(self, obj):
        if obj.document_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document_file.url)
            return obj.document_file.url
        return None

class DocumentUploadSerializer(serializers.ModelSerializer):
    document_file = serializers.FileField()
    
    class Meta:
        model = Document
        fields = ['document_type', 'document_file']
    
    def validate_document_file(self, value):
        # File size validation (max 5MB)
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size too large. Maximum size is 5MB.")
        
        # File type validation
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'application/pdf']
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Invalid file type. Please upload JPG, PNG, GIF, or PDF files only."
            )
        
        return value
    
    def validate_document_type(self, value):
        if value not in ['national_id', 'address_proof', 'license']:
            raise serializers.ValidationError(
                "Invalid document type. Must be one of: national_id, address_proof, license"
            )
        return value

class DocumentStatusSerializer(serializers.ModelSerializer):
    """Serializer for displaying document verification status"""
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    verification_issues = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'document_type', 'document_type_display',
            'status', 'status_display', 'confidence_score',
            'uploaded_at', 'verified_at', 'verification_notes',
            'verification_issues'
        ]
    
    def get_verification_issues(self, obj):
        """Extract issues from verification_data"""
        if obj.verification_data and 'issues' in obj.verification_data:
            return obj.verification_data['issues']
        return []


# Job-related serializers
class JobCategorySerializer(serializers.ModelSerializer):
    """Serializer for job categories"""
    class Meta:
        model = JobCategory
        fields = ['id', 'name', 'slug', 'description', 'icon', 'is_active']
        read_only_fields = ['id']


class JobImageSerializer(serializers.ModelSerializer):
    """Serializer for job images"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = JobImage
        fields = ['id', 'image_url', 'caption', 'order']
        read_only_fields = ['id']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class JobSerializer(serializers.ModelSerializer):
    """Serializer for job listings"""
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    client_email = serializers.CharField(source='client.email', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    job_type_display = serializers.CharField(source='get_job_type_display', read_only=True)
    payment_type_display = serializers.CharField(source='get_payment_type_display', read_only=True)
    duration_display = serializers.CharField(source='get_duration_display', read_only=True)
    experience_level_display = serializers.CharField(source='get_experience_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    budget_display = serializers.ReadOnlyField()
    posted_time_ago = serializers.ReadOnlyField()
    images = JobImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'description', 'category', 'category_name', 'category_slug',
            'job_type', 'job_type_display', 'urgent', 'status', 'status_display',
            'address', 'city', 'latitude', 'longitude',
            'start_date', 'duration', 'duration_display', 'flexible_schedule',
            'payment_type', 'payment_type_display', 'budget', 'budget_currency', 'budget_display',
            'experience_level', 'experience_level_display', 'special_requirements',
            'views_count', 'applications_count', 'images',
            'client_name', 'client_email', 'posted_time_ago',
            'created_at', 'updated_at', 'published_at', 'expires_at'
        ]
        read_only_fields = [
            'id', 'client_name', 'client_email', 'category_name', 'category_slug',
            'views_count', 'applications_count', 'posted_time_ago',
            'created_at', 'updated_at', 'published_at'
        ]


class JobCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating jobs"""
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Job
        fields = [
            'title', 'description', 'category', 'job_type', 'urgent',
            'address', 'city', 'latitude', 'longitude',
            'start_date', 'duration', 'flexible_schedule',
            'payment_type', 'budget', 'budget_currency',
            'experience_level', 'special_requirements', 'images'
        ]
    
    def validate_title(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Job title is required.")
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Job title must be at least 10 characters.")
        if len(value.strip()) > 200:
            raise serializers.ValidationError("Job title must be less than 200 characters.")
        return value.strip()
    
    def validate_description(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Job description is required.")
        if len(value.strip()) < 50:
            raise serializers.ValidationError("Job description must be at least 50 characters.")
        return value.strip()
    
    def validate_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget must be greater than 0.")
        if value > 1000000:
            raise serializers.ValidationError("Budget cannot exceed $1,000,000.")
        return value
    
    def validate_images(self, value):
        if value and len(value) > 5:
            raise serializers.ValidationError("Maximum 5 images allowed.")
        
        for image in value:
            # File size validation (max 5MB per image)
            if image.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Each image must be less than 5MB.")
            
            # File type validation
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if image.content_type not in allowed_types:
                raise serializers.ValidationError("Only JPG, PNG, and GIF images are allowed.")
        
        return value
    
    def create(self, validated_data):
        images_data = validated_data.pop('images', [])
        
        # Set client from the authenticated user
        validated_data['client'] = self.context['request'].user
        
        job = Job.objects.create(**validated_data)
        
        # Create job images
        for i, image_data in enumerate(images_data):
            JobImage.objects.create(
                job=job,
                image=image_data,
                order=i
            )
        
        return job
    
    def update(self, instance, validated_data):
        images_data = validated_data.pop('images', None)
        
        # Update job fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update images if provided
        if images_data is not None:
            # Delete existing images
            instance.images.all().delete()
            
            # Create new images
            for i, image_data in enumerate(images_data):
                JobImage.objects.create(
                    job=instance,
                    image=image_data,
                    order=i
                )
        
        return instance


class JobListSerializer(serializers.ModelSerializer):
    """Simplified serializer for job listings"""
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    budget_display = serializers.ReadOnlyField()
    posted_time_ago = serializers.ReadOnlyField()
    description = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'description', 'category_name', 'city', 'job_type', 'urgent',
            'budget_display', 'posted_time_ago', 'client_name', 'status'
        ]
    
    def get_description(self, obj):
        """Return truncated description for list view"""
        if obj.description:
            # Truncate to 150 characters for the list view
            return obj.description[:150] + "..." if len(obj.description) > 150 else obj.description
        return ""


# Bid-related serializers
class BidDocumentSerializer(serializers.ModelSerializer):
    """Serializer for bid documents"""
    document_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BidDocument
        fields = ['id', 'document_url', 'name', 'description', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']
    
    def get_document_url(self, obj):
        if obj.document:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.document.url)
            return obj.document.url
        return None


class WorkSampleSerializer(serializers.ModelSerializer):
    """Serializer for work samples"""
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkSample
        fields = ['id', 'image_url', 'title', 'description', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']
    
    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class BidSerializer(serializers.ModelSerializer):
    """Serializer for bid listings"""
    job_title = serializers.ReadOnlyField()
    worker_name = serializers.ReadOnlyField()
    worker_email = serializers.ReadOnlyField()
    price_display = serializers.ReadOnlyField()
    status_display = serializers.ReadOnlyField()
    documents = BidDocumentSerializer(many=True, read_only=True)
    work_samples = WorkSampleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Bid
        fields = [
            'id', 'job', 'job_title', 'worker', 'worker_name', 'worker_email',
            'price', 'price_display', 'availability', 'proposal', 'status', 'status_display',
            'documents', 'work_samples', 'submitted_at', 'response_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'job_title', 'worker_name', 'worker_email', 'price_display', 'status_display',
            'submitted_at', 'response_at', 'created_at', 'updated_at'
        ]


class BidCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating bids"""
    documents = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    work_samples = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Bid
        fields = ['price', 'availability', 'proposal', 'documents', 'work_samples']
    
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0.")
        if value > 1000000:
            raise serializers.ValidationError("Price cannot exceed $1,000,000.")
        return value
    
    def validate_availability(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Availability is required.")
        if len(value.strip()) > 200:
            raise serializers.ValidationError("Availability must be less than 200 characters.")
        return value.strip()
    
    def validate_proposal(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Proposal is required.")
        if len(value.strip()) < 50:
            raise serializers.ValidationError("Proposal must be at least 50 characters.")
        if len(value.strip()) > 2000:
            raise serializers.ValidationError("Proposal must be less than 2000 characters.")
        return value.strip()
    
    def validate_documents(self, value):
        if value and len(value) > 5:
            raise serializers.ValidationError("Maximum 5 documents allowed.")
        
        for doc in value:
            # File size validation (max 10MB per document)
            if doc.size > 10 * 1024 * 1024:
                raise serializers.ValidationError("Each document must be less than 10MB.")
            
            # File type validation
            allowed_types = [
                'application/pdf', 'application/msword', 
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'image/jpeg', 'image/jpg', 'image/png'
            ]
            if doc.content_type not in allowed_types:
                raise serializers.ValidationError("Only PDF, DOC, DOCX, JPG, and PNG files are allowed for documents.")
        
        return value
    
    def validate_work_samples(self, value):
        if value and len(value) > 5:
            raise serializers.ValidationError("Maximum 5 work samples allowed.")
        
        for sample in value:
            # File size validation (max 5MB per sample)
            if sample.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("Each work sample must be less than 5MB.")
            
            # File type validation
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if sample.content_type not in allowed_types:
                raise serializers.ValidationError("Only JPG, PNG, and GIF images are allowed for work samples.")
        
        return value
    
    def create(self, validated_data):
        documents_data = validated_data.pop('documents', [])
        work_samples_data = validated_data.pop('work_samples', [])
        
        # Set worker from the authenticated user
        validated_data['worker'] = self.context['request'].user
        
        bid = Bid.objects.create(**validated_data)
        
        # Create bid documents
        for doc_data in documents_data:
            BidDocument.objects.create(
                bid=bid,
                document=doc_data,
                name=doc_data.name or "Document"
            )
        
        # Create work samples
        for sample_data in work_samples_data:
            WorkSample.objects.create(
                bid=bid,
                image=sample_data,
                title=sample_data.name or "Work Sample"
            )
        
        return bid


class BidListSerializer(serializers.ModelSerializer):
    """Simplified serializer for bid listings"""
    job_title = serializers.ReadOnlyField()
    worker_name = serializers.ReadOnlyField()
    price_display = serializers.ReadOnlyField()
    status_display = serializers.ReadOnlyField()
    proposal = serializers.SerializerMethodField()
    
    class Meta:
        model = Bid
        fields = [
            'id', 'job', 'job_title', 'worker_name', 'price_display', 'availability',
            'proposal', 'status_display', 'submitted_at'
        ]
    
    def get_proposal(self, obj):
        """Return truncated proposal for list view"""
        if obj.proposal:
            # Truncate to 100 characters for the list view
            return obj.proposal[:100] + "..." if len(obj.proposal) > 100 else obj.proposal
        return ""


class ClientJobListSerializer(serializers.ModelSerializer):
    """Serializer for client's my-jobs page"""
    category = serializers.CharField(source='category.name', read_only=True)
    location = serializers.CharField(source='city', read_only=True)
    budget = serializers.ReadOnlyField(source='budget_display')
    postedDate = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'category', 'status', 'location', 'budget', 'postedDate'
        ]
    
    def get_postedDate(self, obj):
        """Return formatted posted date"""
        if obj.published_at:
            return f"Posted {obj.published_at.strftime('%b %d, %Y')}"
        return f"Posted {obj.created_at.strftime('%b %d, %Y')}"
    
    def get_status(self, obj):
        """Map backend status to frontend expected status"""
        status_mapping = {
            'draft': 'under-review',
            'open': 'active',
            'in_progress': 'active',
            'completed': 'completed',
            'cancelled': 'completed'
        }
        return status_mapping.get(obj.status, 'active')


class ClientJobDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for client's job detail page"""
    category = serializers.CharField(source='category.name', read_only=True)
    location = serializers.CharField(source='city', read_only=True)
    budget = serializers.ReadOnlyField(source='budget_display')
    postedDate = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    requiredSkills = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()
    attachments = JobImageSerializer(source='images', many=True, read_only=True)
    applications = serializers.SerializerMethodField()
    topApplicants = serializers.SerializerMethodField()
    activityTimeline = serializers.SerializerMethodField()
    timeRemaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'category', 'status', 'location', 'budget', 'postedDate',
            'description', 'requiredSkills', 'timeline', 'attachments', 'applications',
            'topApplicants', 'activityTimeline', 'timeRemaining', 'special_requirements',
            'job_type', 'urgent', 'payment_type', 'experience_level', 'start_date',
            'duration', 'flexible_schedule', 'views_count', 'applications_count'
        ]
    
    def get_postedDate(self, obj):
        """Return formatted posted date"""
        if obj.published_at:
            return obj.published_at.strftime('%B %d, %Y')
        return obj.created_at.strftime('%B %d, %Y')
    
    def get_status(self, obj):
        """Map backend status to frontend expected status"""
        status_mapping = {
            'draft': 'under-review',
            'open': 'active',
            'in_progress': 'active',
            'completed': 'completed',
            'cancelled': 'completed'
        }
        return status_mapping.get(obj.status, 'active')
    
    def get_requiredSkills(self, obj):
        """Extract skills from special_requirements or return default"""
        # For now, we'll parse from special_requirements or return a default list
        # In the future, you might want to add a dedicated skills field
        if obj.special_requirements:
            # Try to extract skills from requirements
            lines = obj.special_requirements.split('\n')
            skills = []
            for line in lines:
                if line.strip() and not line.startswith('-'):
                    skills.append(line.strip())
            if skills:
                return skills[:4]  # Limit to 4 skills
        
        # Default skills based on category
        default_skills = {
            'Plumbing': ['Licensed Plumber', 'Pipe Installation', 'Leak Repair', 'Code Compliance'],
            'Electrical': ['Licensed Electrician', 'Wiring Installation', 'Safety Standards', 'Code Knowledge'],
            'Carpentry': ['Wood Working', 'Tool Proficiency', 'Measurement Skills', 'Safety Practices'],
            'Painting': ['Surface Preparation', 'Paint Application', 'Color Matching', 'Clean Finish'],
            'Cleaning': ['Attention to Detail', 'Time Management', 'Cleaning Supplies', 'Reliability'],
            'Moving': ['Heavy Lifting', 'Packing Skills', 'Time Efficiency', 'Care Handling'],
            'HVAC': ['HVAC Systems', 'Installation', 'Maintenance', 'Troubleshooting'],
            'Landscaping': ['Plant Knowledge', 'Design Skills', 'Tool Operation', 'Seasonal Care']
        }
        return default_skills.get(obj.category.name, ['Professional Experience', 'Reliability', 'Quality Work', 'Communication'])
    
    def get_timeline(self, obj):
        """Return project timeline"""
        if obj.duration:
            duration_map = {
                'under-1-hour': 'Under 1 hour',
                '1-2-hours': '1-2 hours',
                '2-4-hours': '2-4 hours',
                '4-8-hours': '4-8 hours',
                'full-day': '1 day',
                'multi-day': '2-3 days',
                '1-week': '1 week',
                'ongoing': 'Ongoing project'
            }
            return duration_map.get(obj.duration, obj.duration)
        return '1-2 weeks'
    
    def get_applications(self, obj):
        """Return application statistics"""
        total_bids = obj.bids.count()
        reviewed_bids = obj.bids.filter(status__in=['accepted', 'rejected']).count()
        return {
            'total': total_bids,
            'reviewed': reviewed_bids
        }
    
    def get_topApplicants(self, obj):
        """Return top 3 applicants with their bids"""
        top_bids = obj.bids.filter(status='pending').select_related('worker').order_by('-submitted_at')[:3]
        applicants = []
        
        for bid in top_bids:
            worker = bid.worker
            applicants.append({
                'id': str(bid.id),
                'name': worker.full_name,
                'avatar': self.context['request'].build_absolute_uri(worker.profile_picture.url) if worker.profile_picture else None,
                'rating': float(worker.average_rating) if worker.average_rating else 4.5,
                'bid': bid.price_display,
                'description': bid.proposal[:100] + '...' if len(bid.proposal) > 100 else bid.proposal
            })
        
        return applicants
    
    def get_activityTimeline(self, obj):
        """Return activity timeline"""
        timeline = []
        
        # Job posted
        timeline.append({
            'id': 't1',
            'title': 'Job Posted',
            'date': obj.created_at.strftime('%b %d, %Y'),
            'description': 'Job listing went live on the platform'
        })
        
        # First application
        first_bid = obj.bids.order_by('submitted_at').first()
        if first_bid:
            timeline.append({
                'id': 't2',
                'title': 'First Application',
                'date': first_bid.submitted_at.strftime('%b %d, %Y'),
                'description': f'Received first application from {first_bid.worker.full_name}'
            })
        
        # Multiple applications milestone
        if obj.bids.count() >= 3:
            third_bid = obj.bids.order_by('submitted_at')[2]
            timeline.append({
                'id': 't3',
                'title': 'Multiple Applications',
                'date': third_bid.submitted_at.strftime('%b %d, %Y'),
                'description': f'{obj.bids.count()} qualified professionals applied'
            })
        
        # Accepted bid
        accepted_bid = obj.bids.filter(status='accepted').first()
        if accepted_bid:
            timeline.append({
                'id': 't4',
                'title': 'Worker Hired',
                'date': accepted_bid.response_at.strftime('%b %d, %Y') if accepted_bid.response_at else 'Recently',
                'description': f'Hired {accepted_bid.worker.full_name} for this project'
            })
        
        return timeline
    
    def get_timeRemaining(self, obj):
        """Calculate time remaining for the job"""
        from django.utils import timezone
        from datetime import timedelta
        
        if obj.status in ['completed', 'cancelled']:
            return 'Completed'
        
        # If job has a start date, calculate from that
        if obj.start_date:
            today = timezone.now().date()
            if obj.start_date > today:
                days_left = (obj.start_date - today).days
                if days_left == 0:
                    return 'Starting today'
                elif days_left == 1:
                    return '1 day left'
                else:
                    return f'{days_left} days left'
            else:
                return 'In progress'
        
        # Default: 30 days from creation
        created_date = obj.created_at.date()
        deadline = created_date + timedelta(days=30)
        today = timezone.now().date()
        days_left = (deadline - today).days
        
        if days_left <= 0:
            return 'Expired'
        elif days_left == 1:
            return '1 day left'
        else:
            return f'{days_left} days left'

class WorkerSerializer(serializers.ModelSerializer):
    """Serializer for worker listings in find-workers page"""
    name = serializers.CharField(source='full_name', read_only=True)
    occupation = serializers.SerializerMethodField()
    rating = serializers.DecimalField(source='average_rating', max_digits=3, decimal_places=2, read_only=True)
    reviews = serializers.IntegerField(source='total_reviews', read_only=True)
    location = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    availableNow = serializers.SerializerMethodField()
    verified = serializers.BooleanField(source='is_verified', read_only=True)
    backgroundCheck = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'name', 'occupation', 'rating', 'reviews', 'location', 'price',
            'availableNow', 'verified', 'backgroundCheck', 'skills', 'bio', 'image'
        ]
    
    def get_occupation(self, obj):
        """Get primary occupation from skills or default"""
        if obj.skills and len(obj.skills) > 0:
            # Map skills to occupations
            skill_to_occupation = {
                'plumbing': 'Plumber',
                'electrical': 'Electrician', 
                'electrician': 'Electrician',
                'construction': 'Construction Worker',
                'carpentry': 'Construction Worker',
                'painting': 'Painter',
                'driving': 'Driver',
                'delivery': 'Driver',
                'transport': 'Driver'
            }
            
            for skill in obj.skills:
                skill_lower = skill.lower()
                for key, occupation in skill_to_occupation.items():
                    if key in skill_lower:
                        return occupation
            
            # If no match found, use first skill as occupation
            return obj.skills[0].title()
        
        return 'General Worker'
    
    def get_location(self, obj):
        """Get formatted location"""
        if obj.address:
            # Extract city/state from address if possible
            return obj.address
        return 'Location not specified'
    
    def get_price(self, obj):
        """Calculate hourly rate based on experience"""
        if obj.years_of_experience:
            # Base rate calculation based on experience
            base_rate = 25 + (obj.years_of_experience * 2)
            # Cap at reasonable maximum
            rate = min(base_rate, 75)
            return f"${rate}/hr"
        return "$30/hr"  # Default rate
    
    def get_availableNow(self, obj):
        """Check if worker is available (simplified logic)"""
        # For now, randomly assign availability based on user ID
        # In a real system, this would be based on actual availability data
        return obj.id % 3 != 0  # Roughly 2/3 of workers available
    
    def get_backgroundCheck(self, obj):
        """Check if worker has background check"""
        # Check if user has verified documents
        return obj.documents.filter(status='verified').exists()
    
    def get_image(self, obj):
        """Get profile picture URL"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        
        # Return default avatar based on gender/name
        default_avatars = [
            '/images/pricing/profiles/sarah-profile.jpg',
            '/images/user2.jpg',
            '/images/user3.jpg',
            '/images/user4.jpg',
            '/images/avatars/sarah-wilson-large.jpg',
            '/images/testimonials/sarah-johnson.jpg'
        ]
        # Use user ID to consistently assign same avatar
        return default_avatars[obj.id % len(default_avatars)]


class WorkerCategorySerializer(serializers.Serializer):
    """Serializer for worker categories with counts"""
    name = serializers.CharField()
    count = serializers.IntegerField()
    icon = serializers.CharField()


class WorkerDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for worker profile page"""
    name = serializers.CharField(source='full_name', read_only=True)
    title = serializers.SerializerMethodField()
    occupation = serializers.SerializerMethodField()
    rating = serializers.DecimalField(source='average_rating', max_digits=3, decimal_places=2, read_only=True)
    reviews = serializers.IntegerField(source='total_reviews', read_only=True)
    location = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    availableNow = serializers.SerializerMethodField()
    verified = serializers.BooleanField(source='is_verified', read_only=True)
    completionRate = serializers.SerializerMethodField()
    joined = serializers.SerializerMethodField()
    about = serializers.CharField(source='bio', read_only=True)
    education = serializers.SerializerMethodField()
    certifications = serializers.SerializerMethodField()
    languages = serializers.SerializerMethodField()
    workHistory = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'name', 'title', 'occupation', 'rating', 'reviews', 'location', 'price',
            'availableNow', 'verified', 'skills', 'completionRate', 'joined', 'about',
            'education', 'certifications', 'languages', 'workHistory', 'image'
        ]
    
    def get_title(self, obj):
        """Get professional title based on occupation and experience"""
        occupation = self.get_occupation(obj)
        experience = obj.years_of_experience or 0
        
        if experience >= 10:
            return f"Expert {occupation}"
        elif experience >= 5:
            return f"Professional {occupation}"
        elif experience >= 2:
            return f"Experienced {occupation}"
        else:
            return f"Certified {occupation}"
    
    def get_occupation(self, obj):
        """Get primary occupation from skills or default"""
        if obj.skills and len(obj.skills) > 0:
            # Map skills to occupations
            skill_to_occupation = {
                'plumbing': 'Plumber',
                'electrical': 'Electrician', 
                'electrician': 'Electrician',
                'construction': 'Construction Worker',
                'carpentry': 'Construction Worker',
                'painting': 'Painter',
                'driving': 'Driver',
                'delivery': 'Driver',
                'transport': 'Driver'
            }
            
            for skill in obj.skills:
                skill_lower = skill.lower()
                for key, occupation in skill_to_occupation.items():
                    if key in skill_lower:
                        return occupation
            
            # If no match found, use first skill as occupation
            return obj.skills[0].title()
        
        return 'General Worker'
    
    def get_location(self, obj):
        """Get formatted location"""
        if obj.address:
            return obj.address
        return 'Location not specified'
    
    def get_price(self, obj):
        """Calculate hourly rate based on experience"""
        if obj.years_of_experience:
            # Base rate calculation based on experience
            base_rate = 25 + (obj.years_of_experience * 2)
            # Cap at reasonable maximum
            rate = min(base_rate, 75)
            return f"${rate}/hr"
        return "$30/hr"  # Default rate
    
    def get_availableNow(self, obj):
        """Check if worker is available (simplified logic)"""
        # For now, randomly assign availability based on user ID
        # In a real system, this would be based on actual availability data
        return obj.id % 3 != 0  # Roughly 2/3 of workers available
    
    def get_completionRate(self, obj):
        """Calculate job completion rate"""
        # For now, calculate based on total jobs and reviews
        # In a real system, this would be based on actual completion data
        if obj.total_completed_jobs > 0:
            # Simulate completion rate based on rating and experience
            base_rate = 85 + (obj.years_of_experience or 0) * 2
            rating_bonus = (float(obj.average_rating) - 3.0) * 5 if obj.average_rating else 0
            completion_rate = min(base_rate + rating_bonus, 100)
            return int(completion_rate)
        return 95  # Default for new workers
    
    def get_joined(self, obj):
        """Get formatted join date"""
        return obj.created_at.strftime('%b %Y')
    
    def get_education(self, obj):
        """Generate education data based on occupation and experience"""
        occupation = self.get_occupation(obj)
        
        education_map = {
            'Electrician': {
                'degree': 'Diploma in Electrical Engineering',
                'institution': 'Technical Training Institute',
                'year': '2015-2018'
            },
            'Plumber': {
                'degree': 'Diploma in Plumbing',
                'institution': 'Technical Training Institute',
                'year': '2015-2017'
            },
            'Construction Worker': {
                'degree': 'Certificate in Construction Technology',
                'institution': 'Vocational Training Center',
                'year': '2016-2018'
            },
            'Painter': {
                'degree': 'Certificate in Professional Painting',
                'institution': 'Vocational Training Institute',
                'year': '2017-2018'
            },
            'Driver': {
                'degree': 'Commercial Driving License',
                'institution': 'Driving Training Academy',
                'year': '2018-2019'
            }
        }
        
        default_education = {
            'degree': 'Professional Certification',
            'institution': 'Technical Training Institute',
            'year': '2016-2018'
        }
        
        education = education_map.get(occupation, default_education)
        return [education]
    
    def get_certifications(self, obj):
        """Generate certifications based on occupation"""
        occupation = self.get_occupation(obj)
        
        cert_map = {
            'Electrician': [
                {'name': 'Licensed Electrician - State Board', 'year': '2018'},
                {'name': 'Electrical Safety Certification', 'year': '2019'}
            ],
            'Plumber': [
                {'name': 'Licensed Plumber - Municipal Authority', 'year': '2017'},
                {'name': 'Advanced Water Heating Systems Certification', 'year': '2019'}
            ],
            'Construction Worker': [
                {'name': 'Construction Safety Certification', 'year': '2018'},
                {'name': 'Heavy Equipment Operation License', 'year': '2019'}
            ],
            'Painter': [
                {'name': 'Certified Professional Painter', 'year': '2018'},
                {'name': 'Eco-Friendly Painting Methods Certification', 'year': '2020'}
            ],
            'Driver': [
                {'name': 'Commercial Driver License (CDL)', 'year': '2018'},
                {'name': 'Defensive Driving Certification', 'year': '2020'}
            ]
        }
        
        default_certs = [
            {'name': 'Professional Certification', 'year': '2018'},
            {'name': 'Safety Training Certification', 'year': '2019'}
        ]
        
        return cert_map.get(occupation, default_certs)
    
    def get_languages(self, obj):
        """Get languages or default"""
        if obj.languages and len(obj.languages) > 0:
            return obj.languages
        return ['English']  # Default language
    
    def get_workHistory(self, obj):
        """Generate work history based on completed jobs and bids"""
        # Get recent completed bids for this worker
        completed_bids = obj.bids.filter(status='accepted').select_related('job').order_by('-response_at')[:3]
        
        work_history = []
        for bid in completed_bids:
            job = bid.job
            # Generate realistic review based on rating
            rating = float(obj.average_rating) if obj.average_rating else 4.5
            
            reviews = [
                f"{obj.first_name} did an excellent job with our {job.title.lower()}. Professional and completed on time. Highly recommend!",
                f"Very professional and knowledgeable. Completed the job within budget and with high quality.",
                f"{obj.first_name} was very thorough and explained everything clearly. Great service!",
                f"Outstanding work! {obj.first_name} went above and beyond expectations.",
                f"Reliable and skilled worker. Would definitely hire again."
            ]
            
            # Select review based on user ID for consistency
            review_index = (obj.id + len(work_history)) % len(reviews)
            
            work_history.append({
                'jobTitle': job.title,
                'clientName': 'Verified Client',  # Keep client privacy
                'rating': round(rating + (hash(str(obj.id) + str(job.id)) % 10 - 5) * 0.1, 1),
                'review': reviews[review_index],
                'date': bid.response_at.strftime('%B %Y') if bid.response_at else 'Recent'
            })
        
        # If no completed bids, generate sample work history
        if not work_history:
            occupation = self.get_occupation(obj)
            sample_jobs = {
                'Electrician': [
                    'Home Rewiring Project',
                    'Office Lighting Installation', 
                    'Electrical Troubleshooting'
                ],
                'Plumber': [
                    'Bathroom Renovation',
                    'Kitchen Sink Replacement',
                    'Water Heater Installation'
                ],
                'Construction Worker': [
                    'Home Addition Project',
                    'Deck Construction',
                    'Basement Renovation'
                ],
                'Painter': [
                    'Interior House Painting',
                    'Commercial Building Exterior',
                    'Decorative Wall Finishing'
                ],
                'Driver': [
                    'Furniture Delivery Service',
                    'Moving Assistance',
                    'Commercial Transport'
                ]
            }
            
            jobs = sample_jobs.get(occupation, ['Professional Service', 'Quality Work', 'Customer Project'])
            
            for i, job_title in enumerate(jobs):
                rating = float(obj.average_rating) if obj.average_rating else 4.5
                work_history.append({
                    'jobTitle': job_title,
                    'clientName': 'Verified Client',
                    'rating': round(rating + (hash(str(obj.id) + str(i)) % 10 - 5) * 0.1, 1),
                    'review': f"Excellent work on {job_title.lower()}. Professional and reliable service.",
                    'date': f"{['January', 'March', 'May'][i]} 2023"
                })
        
        return work_history
    
    def get_image(self, obj):
        """Get profile picture URL"""
        if obj.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_picture.url)
            return obj.profile_picture.url
        
        # Return default avatar based on gender/name
        default_avatars = [
            '/images/user1.jpg',
            '/images/user2.jpg',
            '/images/user3.jpg',
            '/images/user4.jpg',
            '/images/pricing/profiles/sarah-profile.jpg',
            '/images/avatars/sarah-wilson-large.jpg'
        ]
        # Use user ID to consistently assign same avatar
        return default_avatars[obj.id % len(default_avatars)] 

class JobBidsSerializer(serializers.ModelSerializer):
    """Serializer for client's job bids page"""
    title = serializers.CharField(read_only=True)
    category = serializers.CharField(source='category.name', read_only=True)
    status = serializers.SerializerMethodField()
    bids = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = ['id', 'title', 'category', 'status', 'bids']
    
    def get_status(self, obj):
        """Map backend status to frontend expected status"""
        status_mapping = {
            'draft': 'under-review',
            'open': 'active',
            'in_progress': 'active',
            'completed': 'completed',
            'cancelled': 'completed'
        }
        return status_mapping.get(obj.status, 'active')
    
    def get_bids(self, obj):
        """Return bid statistics and details"""
        from django.db.models import Avg, Min, Max, Count, Q
        from decimal import Decimal
        
        # Get all bids for this job
        job_bids = obj.bids.select_related('worker').prefetch_related('documents', 'work_samples')
        
        # Calculate statistics
        bid_stats = job_bids.aggregate(
            total_bids=Count('id'),
            avg_bid=Avg('price'),
            min_bid=Min('price'),
            max_bid=Max('price'),
            top_rated_count=Count('id', filter=Q(worker__average_rating__gte=4.5))
        )
        
        # Calculate average timeline (simplified - in real system would parse availability field)
        avg_timeline = "14 days"  # Default
        
        # Format statistics
        total_bids = bid_stats['total_bids'] or 0
        avg_bid = bid_stats['avg_bid'] or Decimal('0')
        min_bid = bid_stats['min_bid'] or Decimal('0')
        max_bid = bid_stats['max_bid'] or Decimal('0')
        top_rated_count = bid_stats['top_rated_count'] or 0
        
        # Format posted time
        posted_time = obj.posted_time_ago
        
        # Get detailed bidder information
        bidders = []
        for bid in job_bids.order_by('-submitted_at'):
            worker = bid.worker
            
            # Calculate timeline from availability (simplified)
            timeline = self._extract_timeline(bid.availability)
            
            # Get worker location
            location = worker.address if worker.address else "Location not specified"
            
            # Get worker avatar
            avatar = self._get_worker_avatar(worker)
            
            # Count attachments
            attachments_count = bid.documents.count() + bid.work_samples.count()
            
            bidders.append({
                'id': str(bid.id),
                'name': worker.full_name,
                'avatar': avatar,
                'location': location,
                'rating': float(worker.average_rating) if worker.average_rating else 4.0,
                'bid': f"${bid.price}",
                'timeline': timeline,
                'proposal': bid.proposal,
                'skills': worker.skills[:4] if worker.skills else [],  # Limit to 4 skills
                'attachments': attachments_count,
                'status': bid.status,
                'submitted_at': bid.submitted_at.isoformat(),
                'worker_id': worker.id
            })
        
        return {
            'total': total_bids,
            'posted': posted_time,
            'stats': {
                'averageBid': f"${avg_bid:.0f}" if avg_bid > 0 else "$0",
                'bidRange': f"${min_bid:.0f} - ${max_bid:.0f}" if min_bid > 0 and max_bid > 0 else "$0 - $0",
                'averageTimeline': avg_timeline,
                'topRatedBidders': top_rated_count
            },
            'bidders': bidders
        }
    
    def _extract_timeline(self, availability):
        """Extract timeline from availability text"""
        if not availability:
            return "14 days"
        
        availability_lower = availability.lower()
        
        # Look for common timeline patterns
        if 'immediate' in availability_lower or 'asap' in availability_lower:
            return "Immediately"
        elif 'week' in availability_lower:
            if '1' in availability_lower or 'one' in availability_lower:
                return "1 week"
            elif '2' in availability_lower or 'two' in availability_lower:
                return "2 weeks"
            else:
                return "1-2 weeks"
        elif 'day' in availability_lower:
            if '3' in availability_lower:
                return "3 days"
            elif '5' in availability_lower:
                return "5 days"
            elif '7' in availability_lower:
                return "1 week"
            elif '10' in availability_lower:
                return "10 days"
            elif '14' in availability_lower:
                return "2 weeks"
            else:
                return "Few days"
        elif 'month' in availability_lower:
            return "1 month"
        else:
            return "14 days"  # Default
    
    def _get_worker_avatar(self, worker):
        """Get worker avatar URL"""
        if worker.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(worker.profile_picture.url)
            return worker.profile_picture.url
        
        # Return default avatar based on worker ID
        default_avatars = [
            '/images/bids-received/avatar-sarah.jpg',
            '/images/bids-received/avatar-michael.jpg',
            '/images/pricing/profiles/emily-profile.jpg',
            '/images/user1.jpg',
            '/images/user2.jpg',
            '/images/user3.jpg'
        ]
        return default_avatars[worker.id % len(default_avatars)]


class BidDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual bid information"""
    worker_name = serializers.CharField(source='worker.full_name', read_only=True)
    worker_email = serializers.CharField(source='worker.email', read_only=True)
    worker_avatar = serializers.SerializerMethodField()
    worker_location = serializers.SerializerMethodField()
    worker_rating = serializers.DecimalField(source='worker.average_rating', max_digits=3, decimal_places=2, read_only=True)
    worker_skills = serializers.ListField(source='worker.skills', read_only=True)
    price_display = serializers.ReadOnlyField()
    status_display = serializers.ReadOnlyField()
    attachments_count = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()
    
    class Meta:
        model = Bid
        fields = [
            'id', 'price', 'price_display', 'availability', 'proposal', 'status', 'status_display',
            'worker_name', 'worker_email', 'worker_avatar', 'worker_location', 'worker_rating', 'worker_skills',
            'attachments_count', 'timeline', 'submitted_at', 'response_at'
        ]
    
    def get_worker_avatar(self, obj):
        """Get worker avatar URL"""
        worker = obj.worker
        if worker.profile_picture:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(worker.profile_picture.url)
            return worker.profile_picture.url
        
        # Return default avatar
        default_avatars = [
            '/images/bids-received/avatar-sarah.jpg',
            '/images/bids-received/avatar-michael.jpg',
            '/images/pricing/profiles/emily-profile.jpg'
        ]
        return default_avatars[worker.id % len(default_avatars)]
    
    def get_worker_location(self, obj):
        """Get worker location"""
        return obj.worker.address if obj.worker.address else "Location not specified"
    
    def get_attachments_count(self, obj):
        """Get total attachments count"""
        return obj.documents.count() + obj.work_samples.count()
    
    def get_timeline(self, obj):
        """Extract timeline from availability"""
        if not obj.availability:
            return "14 days"
        
        availability_lower = obj.availability.lower()
        
        # Look for common timeline patterns
        if 'immediate' in availability_lower or 'asap' in availability_lower:
            return "Immediately"
        elif 'week' in availability_lower:
            if '1' in availability_lower or 'one' in availability_lower:
                return "1 week"
            elif '2' in availability_lower or 'two' in availability_lower:
                return "2 weeks"
            else:
                return "1-2 weeks"
        elif 'day' in availability_lower:
            if '3' in availability_lower:
                return "3 days"
            elif '5' in availability_lower:
                return "5 days"
            elif '7' in availability_lower:
                return "1 week"
            elif '10' in availability_lower:
                return "10 days"
            elif '14' in availability_lower:
                return "2 weeks"
            else:
                return "Few days"
        elif 'month' in availability_lower:
            return "1 month"
        else:
            return "14 days"  # Default 