from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from users.models import User, Job, JobCategory
import random


class Command(BaseCommand):
    help = 'Create sample jobs for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Number of sample jobs to create',
        )
        parser.add_argument(
            '--client-email',
            type=str,
            help='Email of client to create jobs for (if not provided, will use existing clients)',
        )

    def handle(self, *args, **options):
        count = options['count']
        client_email = options.get('client_email')

        # Get or create client user
        if client_email:
            try:
                client = User.objects.get(email=client_email, role='client')
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Client with email {client_email} not found')
                )
                return
        else:
            # Get existing clients or create one
            clients = User.objects.filter(role='client')
            if not clients.exists():
                # Create a sample client
                client = User.objects.create_user(
                    username='sample.client@example.com',
                    email='sample.client@example.com',
                    first_name='John',
                    last_name='Doe',
                    role='client',
                    password='testpass123'
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created sample client: {client.email}')
                )
            else:
                client = random.choice(clients)

        # Get job categories
        categories = list(JobCategory.objects.filter(is_active=True))
        if not categories:
            self.stdout.write(
                self.style.ERROR('No job categories found. Run populate_job_categories first.')
            )
            return

        sample_jobs = [
            {
                'title': 'Experienced Plumber Needed for Bathroom Renovation',
                'description': 'Looking for a skilled plumber to help with bathroom renovation. Need to install new fixtures, repair existing plumbing, and ensure everything is up to code. Experience with modern bathroom installations preferred.',
                'category': 'plumbing',
                'city': 'New York',
                'address': '123 Main Street, Manhattan, NY 10001',
                'budget': 1500.00,
                'payment_type': 'fixed',
                'job_type': 'one-time',
                'urgent': True,
                'duration': '2-4-hours',
                'experience_level': 'experienced',
            },
            {
                'title': 'House Cleaning Service Needed Weekly',
                'description': 'Seeking reliable house cleaning service for weekly deep cleaning. 3-bedroom house, 2 bathrooms. Need thorough cleaning including kitchen, bathrooms, bedrooms, and living areas.',
                'category': 'cleaning',
                'city': 'Los Angeles',
                'address': '456 Oak Avenue, Beverly Hills, CA 90210',
                'budget': 25.00,
                'payment_type': 'hourly',
                'job_type': 'recurring',
                'urgent': False,
                'duration': '4-8-hours',
                'experience_level': 'any',
            },
            {
                'title': 'Electrician for Office Setup',
                'description': 'Need qualified electrician to set up electrical systems for new office space. Includes installing outlets, lighting fixtures, and ensuring proper electrical safety compliance.',
                'category': 'electrical',
                'city': 'Chicago',
                'address': '789 Business Park, Chicago, IL 60601',
                'budget': 2500.00,
                'payment_type': 'fixed',
                'job_type': 'one-time',
                'urgent': True,
                'duration': 'full-day',
                'experience_level': 'expert',
            },
            {
                'title': 'Garden Landscape Design and Maintenance',
                'description': 'Looking for landscaping expert to redesign backyard garden. Need consultation, design, planting, and ongoing maintenance setup. Experience with native plants preferred.',
                'category': 'landscaping',
                'city': 'Seattle',
                'address': '321 Garden Lane, Seattle, WA 98101',
                'budget': 35.00,
                'payment_type': 'hourly',
                'job_type': 'recurring',
                'urgent': False,
                'duration': 'multi-day',
                'experience_level': 'experienced',
            },
            {
                'title': 'Moving Help for Apartment Relocation',
                'description': 'Need professional movers to help relocate from 2-bedroom apartment to new location. Heavy furniture, careful handling of electronics and fragile items required.',
                'category': 'moving',
                'city': 'Houston',
                'address': '654 Moving Street, Houston, TX 77001',
                'budget': 800.00,
                'payment_type': 'fixed',
                'job_type': 'one-time',
                'urgent': False,
                'duration': 'full-day',
                'experience_level': 'any',
            },
            {
                'title': 'Interior Painting for Living Room',
                'description': 'Professional painter needed for interior painting project. Living room and dining room, high-quality finish required. Need color consultation and premium paint materials.',
                'category': 'painting',
                'city': 'Phoenix',
                'address': '987 Paint Avenue, Phoenix, AZ 85001',
                'budget': 1200.00,
                'payment_type': 'fixed',
                'job_type': 'one-time',
                'urgent': False,
                'duration': '2-4-hours',
                'experience_level': 'experienced',
            },
            {
                'title': 'AC Repair and Maintenance Service',
                'description': 'Air conditioning unit not cooling properly. Need HVAC technician for diagnosis, repair, and routine maintenance. Emergency service needed due to summer heat.',
                'category': 'hvac',
                'city': 'Miami',
                'address': '147 Cool Street, Miami, FL 33101',
                'budget': 45.00,
                'payment_type': 'hourly',
                'job_type': 'urgent',
                'urgent': True,
                'duration': '2-4-hours',
                'experience_level': 'experienced',
            },
            {
                'title': 'Custom Bookshelf Construction',
                'description': 'Need skilled carpenter to build custom bookshelf for home office. Specific dimensions and design provided. Quality woodworking and finishing required.',
                'category': 'carpentry',
                'city': 'Denver',
                'address': '258 Wood Lane, Denver, CO 80201',
                'budget': 900.00,
                'payment_type': 'fixed',
                'job_type': 'one-time',
                'urgent': False,
                'duration': '1-week',
                'experience_level': 'expert',
            },
        ]

        created_jobs = 0
        
        for i in range(min(count, len(sample_jobs))):
            job_data = sample_jobs[i % len(sample_jobs)]
            
            # Get the category
            try:
                category = JobCategory.objects.get(slug=job_data['category'])
            except JobCategory.DoesNotExist:
                category = random.choice(categories)

            # Create the job
            job = Job.objects.create(
                client=client,
                title=job_data['title'],
                description=job_data['description'],
                category=category,
                city=job_data['city'],
                address=job_data['address'],
                budget=job_data['budget'],
                payment_type=job_data['payment_type'],
                job_type=job_data['job_type'],
                urgent=job_data['urgent'],
                duration=job_data['duration'],
                experience_level=job_data['experience_level'],
                status='open',  # Make jobs immediately available
                start_date=date.today() + timedelta(days=random.randint(1, 14)),
                flexible_schedule=random.choice([True, False]),
            )
            
            created_jobs += 1
            self.stdout.write(
                self.style.SUCCESS(f'Created job: {job.title}')
            )

        # Create additional random jobs if requested
        if count > len(sample_jobs):
            remaining = count - len(sample_jobs)
            cities = ['Boston', 'Atlanta', 'Dallas', 'Portland', 'Nashville', 'Austin', 'San Diego']
            
            for i in range(remaining):
                category = random.choice(categories)
                city = random.choice(cities)
                
                job = Job.objects.create(
                    client=client,
                    title=f'{category.name} Service - {city}',
                    description=f'Professional {category.name.lower()} service needed in {city}. Quality work and reliability required.',
                    category=category,
                    city=city,
                    address=f'{random.randint(100, 999)} Random Street, {city}',
                    budget=random.uniform(100, 2000),
                    payment_type=random.choice(['fixed', 'hourly']),
                    job_type=random.choice(['one-time', 'recurring', 'urgent']),
                    urgent=random.choice([True, False]),
                    duration=random.choice(['under-1-hour', '1-2-hours', '2-4-hours', '4-8-hours', 'full-day']),
                    experience_level=random.choice(['any', 'beginner', 'experienced', 'expert']),
                    status='open',
                    start_date=date.today() + timedelta(days=random.randint(1, 30)),
                    flexible_schedule=random.choice([True, False]),
                )
                
                created_jobs += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created random job: {job.title}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_jobs} sample jobs for client: {client.email}')
        ) 