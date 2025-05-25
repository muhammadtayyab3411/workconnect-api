from django.core.management.base import BaseCommand
from users.models import User


class Command(BaseCommand):
    help = 'Set up test user for API testing'

    def handle(self, *args, **options):
        email = 'tayyab1@example.com'
        password = 'testpass123'
        
        try:
            user = User.objects.get(email=email)
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f'Updated password for existing user: {email}')
            )
        except User.DoesNotExist:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name='Tayyab',
                last_name='Test',
                role='client'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created new user: {email}')
            )
        
        self.stdout.write(f'User role: {user.role}')
        self.stdout.write('Test user is ready for API testing!') 