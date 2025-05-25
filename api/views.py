from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import json

User = get_user_model()

# Create your views here.

@api_view(['GET'])
def health_check(request):
    return Response({'status': 'healthy', 'message': 'WorkConnect API is running'})

@api_view(['POST'])
def google_login(request):
    """
    Handle Google OAuth login from NextAuth.js
    """
    try:
        # Get the ID token from the request
        id_token_str = request.data.get('id_token')
        
        if not id_token_str:
            return Response(
                {'error': 'ID token is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify the ID token with Google
        try:
            # You should replace this with your actual Google Client ID
            CLIENT_ID = "your-google-client-id.apps.googleusercontent.com"
            idinfo = id_token.verify_oauth2_token(
                id_token_str, requests.Request(), CLIENT_ID
            )
            
            # Extract user information from the token
            email = idinfo.get('email')
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            google_id = idinfo.get('sub')
            
            if not email:
                return Response(
                    {'error': 'Email not found in Google token'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user exists, create if not
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': 'client',  # Default role, can be changed later
                    'is_verified': True,  # Google accounts are pre-verified
                }
            )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Return user data and tokens
            return Response({
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role,
                    'phone_number': user.phone_number or '',
                    'is_verified': user.is_verified,
                },
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            # Invalid token
            return Response(
                {'error': f'Invalid Google token: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
    except Exception as e:
        return Response(
            {'error': f'Authentication failed: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
