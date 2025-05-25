from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from jwt import decode as jwt_decode
from django.conf import settings
import urllib.parse

User = get_user_model()


@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware to authenticate WebSocket connections using JWT tokens.
    """
    
    def __init__(self, inner):
        super().__init__(inner)
    
    async def __call__(self, scope, receive, send):
        # Parse query string to get token
        query_string = scope.get('query_string', b'').decode()
        query_params = urllib.parse.parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if token:
            try:
                # Validate the token
                UntypedToken(token)
                
                # Decode the token to get user information
                decoded_data = jwt_decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=["HS256"]
                )
                
                # Get the user
                user = await get_user(decoded_data['user_id'])
                scope['user'] = user
                
            except (InvalidToken, TokenError, KeyError):
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    """
    Middleware stack that includes JWT authentication for WebSocket connections.
    """
    return JWTAuthMiddleware(inner) 