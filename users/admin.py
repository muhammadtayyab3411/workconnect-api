from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Document, Job, JobCategory, JobImage

class CustomUserAdmin(BaseUserAdmin):
    # Add custom fields to the admin interface
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone', 'address', 'date_of_birth', 'profile_picture', 'is_verified',
                      'bio', 'skills', 'languages', 'years_of_experience', 'experience_description',
                      'average_rating', 'total_reviews', 'total_completed_jobs')
        }),
    )
    
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_verified', 'is_active', 'date_joined')
    list_filter = ('role', 'is_verified', 'is_active', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)


class DocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'confidence_score', 'uploaded_at', 'verified_at')
    list_filter = ('document_type', 'status', 'uploaded_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('id', 'uploaded_at', 'verified_at', 'verification_data')
    ordering = ('-uploaded_at',)


class JobImageInline(admin.TabularInline):
    model = JobImage
    extra = 0


class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'category', 'city', 'status', 'urgent', 'budget_display', 'created_at')
    list_filter = ('status', 'job_type', 'urgent', 'category', 'payment_type', 'created_at')
    search_fields = ('title', 'description', 'client__email', 'client__first_name', 'client__last_name', 'city')
    readonly_fields = ('id', 'views_count', 'applications_count', 'created_at', 'updated_at', 'published_at')
    ordering = ('-created_at',)
    inlines = [JobImageInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'client', 'category', 'description', 'job_type', 'urgent', 'status')
        }),
        ('Location', {
            'fields': ('address', 'city', 'latitude', 'longitude')
        }),
        ('Schedule & Duration', {
            'fields': ('start_date', 'duration', 'flexible_schedule')
        }),
        ('Budget & Payment', {
            'fields': ('payment_type', 'budget', 'budget_currency')
        }),
        ('Requirements', {
            'fields': ('experience_level', 'special_requirements')
        }),
        ('Metadata', {
            'fields': ('views_count', 'applications_count', 'created_at', 'updated_at', 'published_at', 'expires_at')
        }),
    )


class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


class JobImageAdmin(admin.ModelAdmin):
    list_display = ('job', 'caption', 'order')
    list_filter = ('job__category', 'job__status')
    search_fields = ('job__title', 'caption')
    ordering = ('job', 'order')


# Register models
admin.site.register(User, CustomUserAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(JobCategory, JobCategoryAdmin)
admin.site.register(JobImage, JobImageAdmin)
