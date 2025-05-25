from django.shortcuts import render
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from rest_framework import status, generics, permissions, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.helpers import complete_social_login
from django.utils.translation import gettext_lazy as _
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import requests
import jwt
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.files.storage import default_storage
from django.http import HttpResponse, Http404
import os
import uuid
import mimetypes
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.viewsets import ModelViewSet
from django.utils import timezone

from .models import User, PasswordResetToken, EmailVerificationToken, Document, Job, JobCategory, JobImage, Bid, BidDocument, WorkSample
from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer, 
    ProfileUpdateSerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentStatusSerializer,
    JobSerializer,
    JobCreateUpdateSerializer,
    JobListSerializer,
    JobCategorySerializer,
    JobImageSerializer,
    ClientJobListSerializer,
    ClientJobDetailSerializer,
    BidSerializer,
    BidCreateSerializer,
    BidListSerializer,
    BidDocumentSerializer,
    WorkSampleSerializer,
    WorkerSerializer,
    WorkerCategorySerializer,
    WorkerDetailSerializer,
    JobBidsSerializer,
    BidDetailSerializer
)
from .gemini_service import GeminiDocumentVerifier

# Create your views here.

class AuthViewSet(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        action = kwargs.get('action')
        
        if action == 'register':
            return self.register(request)
        elif action == 'login':
            return self.login(request)
        elif action == 'refresh':
            return self.refresh_token(request)
        elif action == 'logout':
            return self.logout(request)
        else:
            return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

    def register(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Serialize user data
            user_serializer = UserSerializer(user)
            
            return Response({
                'message': 'User registered successfully',
                'user': user_serializer.data,
                'tokens': {
                    'access': access_token,
                    'refresh': refresh_token
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def login(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'error': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user = authenticate(request, username=email, password=password)
        if user:
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # Serialize user data
            user_serializer = UserSerializer(user)
            
            return Response({
                'message': 'Login successful',
                'user': user_serializer.data,
                'tokens': {
                    'access': access_token,
                    'refresh': refresh_token
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Invalid email or password'
            }, status=status.HTTP_401_UNAUTHORIZED)

    def refresh_token(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({
                    'error': 'Refresh token is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            
            return Response({
                'access': access_token
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Invalid refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)

    def logout(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            # Return updated user data
            user_serializer = UserSerializer(request.user, context={'request': request})
            return Response({
                'message': 'Profile updated successfully',
                'user': user_serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfilePictureUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if 'profile_picture' not in request.FILES:
            return Response({
                'error': 'No profile picture provided'
            }, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['profile_picture']
        
        # File size validation (max 5MB)
        if file.size > 5 * 1024 * 1024:
            return Response({
                'error': 'File size too large. Maximum size is 5MB.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # File type validation
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
        if file.content_type not in allowed_types:
            return Response({
                'error': 'Invalid file type. Please upload JPG, PNG, or GIF files only.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Save the file
        user = request.user
        
        # Delete old profile picture if exists
        if user.profile_picture:
            old_path = user.profile_picture.path
            if default_storage.exists(old_path):
                default_storage.delete(old_path)

        user.profile_picture = file
        user.save()

        # Get the URL
        profile_picture_url = None
        if user.profile_picture:
            profile_picture_url = request.build_absolute_uri(user.profile_picture.url)

        return Response({
            'message': 'Profile picture uploaded successfully',
            'profile_picture_url': profile_picture_url
        })

class DocumentViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer
    
    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        if self.action in ['create', 'upload']:
            return DocumentUploadSerializer
        elif self.action == 'status':
            return DocumentStatusSerializer
        return DocumentSerializer
    
    def list(self, request):
        """List all documents for the authenticated user"""
        documents = self.get_queryset()
        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)
    
    def create(self, request):
        """Upload a new document"""
        serializer = DocumentUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            document_type = serializer.validated_data['document_type']
            document_file = serializer.validated_data['document_file']
            
            # Check if user already has a document of this type
            existing_doc = Document.objects.filter(
                user=request.user, 
                document_type=document_type
            ).first()
            
            if existing_doc:
                # Delete the existing document file
                if existing_doc.document_file:
                    try:
                        default_storage.delete(existing_doc.document_file.path)
                    except:
                        pass  # File might not exist
                # Delete the database record
                existing_doc.delete()
            
            # Create new document
            document = Document.objects.create(
                user=request.user,
                document_type=document_type,
                document_file=document_file,
                status='pending'
            )
            
            # Verify document with Gemini
            try:
                verifier = GeminiDocumentVerifier()
                verification_result = verifier.verify_document(
                    document.document_file.path,
                    document_type
                )
                
                # Update document with verification results
                document.verification_data = verification_result
                document.confidence_score = verification_result.get('confidence', 0)
                document.status = verification_result.get('status', 'manual_review')
                document.verification_notes = verification_result.get('reasoning', '')
                document.save()
                
                # Serialize the updated document
                response_serializer = DocumentSerializer(document, context={'request': request})
                
                return Response({
                    'message': 'Document uploaded and verified successfully',
                    'document': response_serializer.data,
                    'verification_result': verification_result
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                print(f"Gemini verification failed: {e}")
                # If Gemini fails, still save the document but mark for manual review
                document.status = 'manual_review'
                document.verification_notes = 'Automatic verification failed, requires manual review'
                document.save()
                
                response_serializer = DocumentSerializer(document, context={'request': request})
                
                return Response({
                    'message': 'Document uploaded successfully, verification pending',
                    'document': response_serializer.data,
                    'verification_result': None
                }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        """Delete a document"""
        try:
            document = Document.objects.get(id=pk, user=request.user)
            
            # Delete the file
            if document.document_file:
                try:
                    default_storage.delete(document.document_file.path)
                except:
                    pass  # File might not exist
            
            # Delete the database record
            document.delete()
            
            return Response({
                'message': 'Document deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except Document.DoesNotExist:
            return Response({
                'error': 'Document not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def reverify(self, request, pk=None):
        """Re-verify an existing document"""
        try:
            document = Document.objects.get(id=pk, user=request.user)
            
            # Verify document with Gemini
            try:
                verifier = GeminiDocumentVerifier()
                verification_result = verifier.verify_document(
                    document.document_file.path,
                    document.document_type
                )
                
                # Update document with verification results
                document.verification_data = verification_result
                document.confidence_score = verification_result.get('confidence', 0)
                document.status = verification_result.get('status', 'manual_review')
                document.verification_notes = verification_result.get('reasoning', '')
                document.save()
                
                # Serialize the updated document
                response_serializer = DocumentSerializer(document, context={'request': request})
                
                return Response({
                    'message': 'Document re-verified successfully',
                    'document': response_serializer.data,
                    'verification_result': verification_result
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                print(f"Gemini re-verification failed: {e}")
                return Response({
                    'error': 'Verification service temporarily unavailable'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
        except Document.DoesNotExist:
            return Response({
                'error': 'Document not found'
            }, status=status.HTTP_404_NOT_FOUND)

# Job Management Views
class JobCategoryViewSet(ModelViewSet):
    """ViewSet for job categories"""
    queryset = JobCategory.objects.filter(is_active=True)
    serializer_class = JobCategorySerializer
    permission_classes = [permissions.AllowAny]  # Categories are public
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'description']
    
    def get_permissions(self):
        """Only allow read operations for non-admin users"""
        if self.action in ['list', 'retrieve']:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

class JobViewSet(ModelViewSet):
    """ViewSet for job management with CRUD operations"""
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'city', 'category__name']
    ordering_fields = ['created_at', 'budget', 'urgent']
    ordering = ['-created_at']  # Default ordering
    
    def get_queryset(self):
        """Return jobs based on user role and filters"""
        user = self.request.user
        
        if user.role == 'client':
            # Clients see their own jobs
            queryset = Job.objects.filter(client=user)
        else:
            # Workers see published jobs from other users
            queryset = Job.objects.filter(status='open').exclude(client=user)
        
        # Apply filters
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
        
        city = self.request.query_params.get('city')
        if city:
            queryset = queryset.filter(city__icontains=city)
        
        job_type = self.request.query_params.get('job_type')
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        
        urgent = self.request.query_params.get('urgent')
        if urgent and urgent.lower() in ['true', '1']:
            queryset = queryset.filter(urgent=True)
        
        min_budget = self.request.query_params.get('min_budget')
        if min_budget:
            try:
                queryset = queryset.filter(budget__gte=float(min_budget))
            except ValueError:
                pass
        
        max_budget = self.request.query_params.get('max_budget')
        if max_budget:
            try:
                queryset = queryset.filter(budget__lte=float(max_budget))
            except ValueError:
                pass
        
        return queryset.select_related('client', 'category').prefetch_related('images')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['create', 'update', 'partial_update']:
            return JobCreateUpdateSerializer
        elif self.action == 'list':
            return JobListSerializer
        return JobSerializer
    
    def list(self, request):
        """List jobs with optional filters"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Create a new job (clients only)"""
        if request.user.role != 'client':
            return Response({
                'error': 'Only clients can post jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            job = serializer.save()
            
            # Return full job data
            response_serializer = JobSerializer(job, context={'request': request})
            return Response({
                'message': 'Job created successfully',
                'job': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        """Get job details and increment view count"""
        job = self.get_object()
        
        # Increment view count (only for workers viewing client jobs)
        if request.user.role == 'worker' and job.client != request.user:
            job.views_count += 1
            job.save(update_fields=['views_count'])
        
        serializer = JobSerializer(job, context={'request': request})
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """Update a job (owner only)"""
        job = self.get_object()
        
        if job.client != request.user:
            return Response({
                'error': 'You can only edit your own jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(job, data=request.data, context={'request': request})
        if serializer.is_valid():
            job = serializer.save()
            
            # Return updated job data
            response_serializer = JobSerializer(job, context={'request': request})
            return Response({
                'message': 'Job updated successfully',
                'job': response_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None):
        """Partially update a job (owner only)"""
        job = self.get_object()
        
        if job.client != request.user:
            return Response({
                'error': 'You can only edit your own jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(job, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            job = serializer.save()
            
            # Return updated job data
            response_serializer = JobSerializer(job, context={'request': request})
            return Response({
                'message': 'Job updated successfully',
                'job': response_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        """Delete a job (owner only)"""
        job = self.get_object()
        
        if job.client != request.user:
            return Response({
                'error': 'You can only delete your own jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Delete associated images
        for image in job.images.all():
            if image.image:
                try:
                    default_storage.delete(image.image.path)
                except:
                    pass
        
        job.delete()
        
        return Response({
            'message': 'Job deleted successfully'
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a draft job"""
        job = self.get_object()
        
        if job.client != request.user:
            return Response({
                'error': 'You can only publish your own jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if job.status != 'draft':
            return Response({
                'error': 'Only draft jobs can be published'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        job.status = 'open'
        job.save()
        
        serializer = JobSerializer(job, context={'request': request})
        return Response({
            'message': 'Job published successfully',
            'job': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an open job"""
        job = self.get_object()
        
        if job.client != request.user:
            return Response({
                'error': 'You can only close your own jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if job.status not in ['open', 'in_progress']:
            return Response({
                'error': 'Only open or in-progress jobs can be closed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        job.status = 'completed'
        job.save()
        
        serializer = JobSerializer(job, context={'request': request})
        return Response({
            'message': 'Job closed successfully',
            'job': serializer.data
        })

    @action(detail=False, methods=['get'], url_path='my-jobs')
    def my_jobs(self, request):
        """Get client's jobs formatted for my-jobs page"""
        if request.user.role != 'client':
            return Response({
                'error': 'Only clients can access this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get all jobs for the client
        queryset = Job.objects.filter(client=request.user).select_related('category').order_by('-created_at')
        
        # Apply search filter if provided
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(category__name__icontains=search) |
                Q(city__icontains=search)
            )
        
        # Apply status filter if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            # Map frontend status to backend statuses
            status_mapping = {
                'active': ['open', 'in_progress'],
                'under-review': ['draft'],
                'completed': ['completed', 'cancelled']
            }
            backend_statuses = status_mapping.get(status_filter, [])
            if backend_statuses:
                queryset = queryset.filter(status__in=backend_statuses)
        
        serializer = ClientJobListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='detail')
    def job_detail(self, request, pk=None):
        """Get detailed job information for client job detail page"""
        job = self.get_object()
        
        if job.client != request.user:
            return Response({
                'error': 'You can only view your own jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ClientJobDetailSerializer(job, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='mark-completed')
    def mark_completed(self, request, pk=None):
        """Mark a job as completed"""
        job = self.get_object()
        
        if job.client != request.user:
            return Response({
                'error': 'You can only complete your own jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if job.status not in ['open', 'in_progress']:
            return Response({
                'error': 'Only open or in-progress jobs can be marked as completed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        job.status = 'completed'
        job.save()
        
        # Reject all pending bids
        job.bids.filter(status='pending').update(
            status='rejected',
            response_at=timezone.now()
        )
        
        serializer = ClientJobDetailSerializer(job, context={'request': request})
        return Response({
            'message': 'Job marked as completed successfully',
            'job': serializer.data
        })
    
    @action(detail=True, methods=['post'], url_path='duplicate')
    def duplicate_job(self, request, pk=None):
        """Duplicate a job for editing"""
        original_job = self.get_object()
        
        if original_job.client != request.user:
            return Response({
                'error': 'You can only duplicate your own jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Create a copy of the job
        job_data = {
            'title': f"Copy of {original_job.title}",
            'description': original_job.description,
            'category': original_job.category.id,
            'job_type': original_job.job_type,
            'urgent': original_job.urgent,
            'address': original_job.address,
            'city': original_job.city,
            'latitude': original_job.latitude,
            'longitude': original_job.longitude,
            'start_date': original_job.start_date,
            'duration': original_job.duration,
            'flexible_schedule': original_job.flexible_schedule,
            'payment_type': original_job.payment_type,
            'budget': original_job.budget,
            'budget_currency': original_job.budget_currency,
            'experience_level': original_job.experience_level,
            'special_requirements': original_job.special_requirements,
        }
        
        serializer = JobCreateUpdateSerializer(data=job_data, context={'request': request})
        if serializer.is_valid():
            new_job = serializer.save()
            
            # Copy images if any
            for image in original_job.images.all():
                JobImage.objects.create(
                    job=new_job,
                    image=image.image,
                    caption=image.caption,
                    order=image.order
                )
            
            response_serializer = JobSerializer(new_job, context={'request': request})
            return Response({
                'message': 'Job duplicated successfully',
                'job': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='download-report')
    def download_report(self, request, pk=None):
        """Generate and download job report"""
        job = self.get_object()
        
        if job.client != request.user:
            return Response({
                'error': 'You can only download reports for your own jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Generate report data
        report_data = {
            'job_id': str(job.id),
            'title': job.title,
            'category': job.category.name,
            'status': job.get_status_display(),
            'budget': job.budget_display,
            'location': f"{job.address}, {job.city}",
            'posted_date': job.created_at.strftime('%B %d, %Y'),
            'description': job.description,
            'applications_count': job.bids.count(),
            'views_count': job.views_count,
            'bids': []
        }
        
        # Add bid information
        for bid in job.bids.all().select_related('worker'):
            report_data['bids'].append({
                'worker_name': bid.worker.full_name,
                'worker_email': bid.worker.email,
                'bid_amount': str(bid.price),
                'status': bid.get_status_display(),
                'submitted_at': bid.submitted_at.strftime('%B %d, %Y %H:%M'),
                'proposal_excerpt': bid.proposal[:200] + '...' if len(bid.proposal) > 200 else bid.proposal
            })
        
        return Response({
            'message': 'Report generated successfully',
            'report': report_data,
            'download_url': f'/api/jobs/{job.id}/download-report/'
        })

    @action(detail=True, methods=['get'], url_path='bids')
    def job_bids(self, request, pk=None):
        """Get bids for a specific job (job owner only)"""
        job = self.get_object()
        
        if job.client != request.user:
            return Response({
                'error': 'You can only view bids for your own jobs'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = JobBidsSerializer(job, context={'request': request})
        return Response(serializer.data)

class BidViewSet(ModelViewSet):
    """ViewSet for bid management with CRUD operations"""
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['proposal', 'job__title', 'worker__first_name', 'worker__last_name']
    ordering_fields = ['submitted_at', 'price', 'status']
    ordering = ['-submitted_at']  # Default ordering
    
    def get_queryset(self):
        """Filter bids based on user role and ownership"""
        if self.request.user.role == 'worker':
            # Workers see only their own bids
            return Bid.objects.filter(worker=self.request.user).select_related('job', 'worker', 'job__client')
        elif self.request.user.role == 'client':
            # Clients see bids for their jobs
            return Bid.objects.filter(job__client=self.request.user).select_related('job', 'worker', 'job__client')
        else:
            # Admins see all bids
            return Bid.objects.all().select_related('job', 'worker', 'job__client')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return BidCreateSerializer
        elif self.action == 'list':
            return BidListSerializer
        return BidSerializer
    
    def list(self, request):
        """List bids with optional filters"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Additional filters
        job_id = self.request.query_params.get('job')
        if job_id:
            queryset = queryset.filter(job__id=job_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        """Create a new bid (workers only)"""
        if request.user.role != 'worker':
            return Response({
                'error': 'Only workers can submit bids'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get job from URL parameter (if routed through jobs/<job_id>/bids/) or request data
        job_id = self.kwargs.get('job_id') or request.data.get('job')
        if not job_id:
            return Response({
                'error': 'Job ID is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            job = Job.objects.get(id=job_id, status='open')
        except Job.DoesNotExist:
            return Response({
                'error': 'Job not found or not open for bidding'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if worker already has a bid for this job
        if Bid.objects.filter(job=job, worker=request.user).exists():
            return Response({
                'error': 'You have already submitted a bid for this job'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Prevent clients from bidding on their own jobs
        if job.client == request.user:
            return Response({
                'error': 'You cannot bid on your own job'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            bid = serializer.save(job=job)
            
            # Increment job applications count
            job.applications_count += 1
            job.save(update_fields=['applications_count'])
            
            # Return full bid data
            response_serializer = BidSerializer(bid, context={'request': request})
            return Response({
                'message': f'Your bid has been submitted successfully for "{job.title}"!',
                'bid': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, pk=None):
        """Get bid details"""
        bid = self.get_object()
        
        # Check permissions - only bid owner, job owner, or admin can view
        if (request.user != bid.worker and 
            request.user != bid.job.client and 
            request.user.role != 'admin'):
            return Response({
                'error': 'You do not have permission to view this bid'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = BidSerializer(bid, context={'request': request})
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """Update a bid (owner only, pending bids only)"""
        bid = self.get_object()
        
        if bid.worker != request.user:
            return Response({
                'error': 'You can only edit your own bids'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if bid.status != 'pending':
            return Response({
                'error': 'You can only edit pending bids'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Don't allow changing the job
        request_data = request.data.copy()
        if 'job' in request_data:
            del request_data['job']
        
        serializer = BidCreateSerializer(bid, data=request_data, partial=True, context={'request': request})
        if serializer.is_valid():
            bid = serializer.save()
            
            # Return updated bid data
            response_serializer = BidSerializer(bid, context={'request': request})
            return Response({
                'message': 'Bid updated successfully',
                'bid': response_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, pk=None):
        """Withdraw a bid (owner only, pending bids only)"""
        bid = self.get_object()
        
        if bid.worker != request.user:
            return Response({
                'error': 'You can only withdraw your own bids'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if bid.status != 'pending':
            return Response({
                'error': 'You can only withdraw pending bids'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update status instead of deleting
        bid.status = 'withdrawn'
        bid.save()
        
        # Decrement job applications count
        bid.job.applications_count -= 1
        bid.job.save(update_fields=['applications_count'])
        
        return Response({
            'message': 'Bid withdrawn successfully'
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accept a bid (job owner only)"""
        bid = self.get_object()
        
        if bid.job.client != request.user:
            return Response({
                'error': 'Only the job owner can accept bids'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if bid.status != 'pending':
            return Response({
                'error': 'Only pending bids can be accepted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if bid.job.status != 'open':
            return Response({
                'error': 'Only open jobs can have bids accepted'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Accept the bid
        bid.status = 'accepted'
        bid.save()
        
        # Update job status to in_progress
        bid.job.status = 'in_progress'
        bid.job.save()
        
        # Reject all other pending bids for this job
        Bid.objects.filter(job=bid.job, status='pending').exclude(id=bid.id).update(
            status='rejected',
            response_at=timezone.now()
        )
        
        serializer = BidSerializer(bid, context={'request': request})
        return Response({
            'message': f'Bid accepted! You have hired {bid.worker.full_name} for this job.',
            'bid': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a bid (job owner only)"""
        bid = self.get_object()
        
        if bid.job.client != request.user:
            return Response({
                'error': 'Only the job owner can reject bids'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if bid.status != 'pending':
            return Response({
                'error': 'Only pending bids can be rejected'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        bid.status = 'rejected'
        bid.save()
        
        serializer = BidSerializer(bid, context={'request': request})
        return Response({
            'message': 'Bid rejected successfully',
            'bid': serializer.data
        })

class WorkersListView(APIView):
    """API view for finding workers with filtering and search"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Get all workers (users with role='worker')
            workers = User.objects.filter(role='worker')
            
            # Apply filters
            search = request.query_params.get('search', '')
            category = request.query_params.get('category', '')
            location = request.query_params.get('location', '')
            verified_only = request.query_params.get('verified_only', '').lower() == 'true'
            min_rating = request.query_params.get('min_rating', '')
            available_only = request.query_params.get('available_only', '').lower() == 'true'
            sort_by = request.query_params.get('sort_by', '')
            
            # Search filter
            if search:
                workers = workers.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(bio__icontains=search) |
                    Q(skills__icontains=search)
                )
            
            # Category filter (based on skills)
            if category:
                category_skills_map = {
                    'Electrician': ['electrical', 'electrician', 'wiring', 'installation'],
                    'Plumber': ['plumbing', 'plumber', 'pipes', 'water'],
                    'Construction': ['construction', 'carpentry', 'building', 'framing'],
                    'Painter': ['painting', 'painter', 'interior', 'exterior'],
                    'Driver': ['driving', 'driver', 'delivery', 'transport']
                }
                
                if category in category_skills_map:
                    skills_filter = Q()
                    for skill in category_skills_map[category]:
                        skills_filter |= Q(skills__icontains=skill)
                    workers = workers.filter(skills_filter)
            
            # Location filter
            if location:
                workers = workers.filter(address__icontains=location)
            
            # Verified only filter
            if verified_only:
                workers = workers.filter(is_verified=True)
            
            # Rating filter
            if min_rating:
                try:
                    min_rating_value = float(min_rating)
                    workers = workers.filter(average_rating__gte=min_rating_value)
                except ValueError:
                    pass
            
            # Availability filter (simplified - in real system would check actual availability)
            if available_only:
                # For demo purposes, filter based on user ID pattern
                workers = workers.extra(where=["id::text::int % 3 != 0"])
            
            # Sorting
            if sort_by == 'rating':
                workers = workers.order_by('-average_rating', '-total_reviews')
            elif sort_by == 'price_low':
                workers = workers.order_by('years_of_experience')  # Lower experience = lower price
            elif sort_by == 'price_high':
                workers = workers.order_by('-years_of_experience')  # Higher experience = higher price
            elif sort_by == 'reviews':
                workers = workers.order_by('-total_reviews', '-average_rating')
            else:
                workers = workers.order_by('-average_rating', '-total_reviews')  # Default sort
            
            # Serialize workers
            serializer = WorkerSerializer(workers, many=True, context={'request': request})
            
            # Get category counts
            categories = self.get_category_counts()
            
            return Response({
                'workers': serializer.data,
                'categories': categories,
                'total_count': workers.count()
            })
            
        except Exception as e:
            return Response({
                'error': f'Failed to fetch workers: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_category_counts(self):
        """Get worker counts by category"""
        try:
            # Define category mappings
            categories = [
                {
                    'name': 'Plumbing',
                    'icon': 'Wrench',
                    'skills': ['plumbing', 'plumber', 'pipes', 'water']
                },
                {
                    'name': 'Driving', 
                    'icon': 'Truck',
                    'skills': ['driving', 'driver', 'delivery', 'transport']
                },
                {
                    'name': 'Construction',
                    'icon': 'HardHat', 
                    'skills': ['construction', 'carpentry', 'building', 'framing']
                },
                {
                    'name': 'Painting',
                    'icon': 'Paintbrush',
                    'skills': ['painting', 'painter', 'interior', 'exterior']
                },
                {
                    'name': 'Electrical',
                    'icon': 'Cable',
                    'skills': ['electrical', 'electrician', 'wiring', 'installation']
                }
            ]
            
            category_data = []
            for category in categories:
                # Count workers with skills matching this category
                skills_filter = Q()
                for skill in category['skills']:
                    skills_filter |= Q(skills__icontains=skill)
                
                count = User.objects.filter(role='worker').filter(skills_filter).count()
                
                category_data.append({
                    'name': category['name'],
                    'count': count,
                    'icon': category['icon']
                })
            
            return category_data
            
        except Exception as e:
            # Return default categories if error
            return [
                {'name': 'Plumbing', 'count': 0, 'icon': 'Wrench'},
                {'name': 'Driving', 'count': 0, 'icon': 'Truck'},
                {'name': 'Construction', 'count': 0, 'icon': 'HardHat'},
                {'name': 'Painting', 'count': 0, 'icon': 'Paintbrush'},
                {'name': 'Electrical', 'count': 0, 'icon': 'Cable'}
            ]

class WorkerDetailView(APIView):
    """API view for getting individual worker details"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, worker_id):
        try:
            # Get the worker by ID
            worker = get_object_or_404(User, id=worker_id, role='worker')
            
            # Serialize worker data
            serializer = WorkerDetailSerializer(worker, context={'request': request})
            
            return Response(serializer.data)
            
        except User.DoesNotExist:
            return Response({
                'error': 'Worker not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to fetch worker details: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
