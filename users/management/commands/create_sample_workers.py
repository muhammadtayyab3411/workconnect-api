from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decimal import Decimal
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample worker users for testing the find-workers page'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of workers to create (default: 20)',
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Sample worker data
        worker_profiles = [
            {
                'first_name': 'Michael',
                'last_name': 'Anderson',
                'email': 'michael.anderson@example.com',
                'skills': ['Electrical', 'Wiring', 'Installation', 'Maintenance'],
                'bio': 'Certified electrician with 8+ years of experience in residential and commercial installations.',
                'years_of_experience': 8,
                'address': 'San Francisco, CA',
                'average_rating': Decimal('4.8'),
                'total_reviews': 35,
                'total_completed_jobs': 42
            },
            {
                'first_name': 'Sarah',
                'last_name': 'Johnson',
                'email': 'sarah.johnson@example.com',
                'skills': ['Plumbing', 'Emergency Repair', 'Installation', 'Renovation'],
                'bio': 'Master plumber specializing in emergency repairs and bathroom renovations.',
                'years_of_experience': 12,
                'address': 'Los Angeles, CA',
                'average_rating': Decimal('4.9'),
                'total_reviews': 42,
                'total_completed_jobs': 58
            },
            {
                'first_name': 'David',
                'last_name': 'Wilson',
                'email': 'david.wilson@example.com',
                'skills': ['Construction', 'Carpentry', 'Framing', 'Renovation'],
                'bio': 'Experienced in residential construction with focus on sustainable building practices.',
                'years_of_experience': 6,
                'address': 'Chicago, IL',
                'average_rating': Decimal('4.7'),
                'total_reviews': 28,
                'total_completed_jobs': 34
            },
            {
                'first_name': 'Emily',
                'last_name': 'Brown',
                'email': 'emily.brown@example.com',
                'skills': ['Painting', 'Interior', 'Exterior', 'Decorative'],
                'bio': 'Professional painter with expertise in interior and exterior painting.',
                'years_of_experience': 5,
                'address': 'Seattle, WA',
                'average_rating': Decimal('4.6'),
                'total_reviews': 31,
                'total_completed_jobs': 38
            },
            {
                'first_name': 'James',
                'last_name': 'Martinez',
                'email': 'james.martinez@example.com',
                'skills': ['Driving', 'Commercial', 'Delivery', 'Transport'],
                'bio': 'Professional driver with clean record and experience in various vehicle types.',
                'years_of_experience': 10,
                'address': 'Miami, FL',
                'average_rating': Decimal('4.9'),
                'total_reviews': 56,
                'total_completed_jobs': 78
            },
            {
                'first_name': 'Lisa',
                'last_name': 'Thompson',
                'email': 'lisa.thompson@example.com',
                'skills': ['Electrical', 'Smart Home', 'Repairs', 'Upgrades'],
                'bio': 'Specialized in smart home installations and electrical system upgrades.',
                'years_of_experience': 7,
                'address': 'Austin, TX',
                'average_rating': Decimal('4.7'),
                'total_reviews': 39,
                'total_completed_jobs': 45
            },
            {
                'first_name': 'Robert',
                'last_name': 'Garcia',
                'email': 'robert.garcia@example.com',
                'skills': ['Plumbing', 'Water Systems', 'Pipe Installation', 'Leak Repair'],
                'bio': 'Expert in water system installations and emergency leak repairs.',
                'years_of_experience': 9,
                'address': 'Phoenix, AZ',
                'average_rating': Decimal('4.8'),
                'total_reviews': 44,
                'total_completed_jobs': 52
            },
            {
                'first_name': 'Jennifer',
                'last_name': 'Lee',
                'email': 'jennifer.lee@example.com',
                'skills': ['Construction', 'Project Management', 'Renovation', 'Design'],
                'bio': 'Construction project manager with expertise in home renovations.',
                'years_of_experience': 11,
                'address': 'Denver, CO',
                'average_rating': Decimal('4.9'),
                'total_reviews': 33,
                'total_completed_jobs': 29
            },
            {
                'first_name': 'Carlos',
                'last_name': 'Rodriguez',
                'email': 'carlos.rodriguez@example.com',
                'skills': ['Painting', 'Commercial', 'Residential', 'Texture Work'],
                'bio': 'Commercial and residential painter specializing in texture and finish work.',
                'years_of_experience': 8,
                'address': 'San Diego, CA',
                'average_rating': Decimal('4.6'),
                'total_reviews': 37,
                'total_completed_jobs': 41
            },
            {
                'first_name': 'Amanda',
                'last_name': 'Taylor',
                'email': 'amanda.taylor@example.com',
                'skills': ['Driving', 'Logistics', 'Moving', 'Heavy Equipment'],
                'bio': 'Experienced driver specializing in logistics and heavy equipment transport.',
                'years_of_experience': 6,
                'address': 'Portland, OR',
                'average_rating': Decimal('4.7'),
                'total_reviews': 29,
                'total_completed_jobs': 35
            }
        ]
        
        # Additional skill sets for generating more workers
        skill_sets = [
            ['Electrical', 'Solar Installation', 'Panel Upgrades'],
            ['Plumbing', 'Bathroom Renovation', 'Kitchen Plumbing'],
            ['Construction', 'Roofing', 'Siding', 'Windows'],
            ['Painting', 'Wallpaper', 'Drywall Repair'],
            ['Driving', 'Uber', 'Lyft', 'Food Delivery'],
            ['Electrical', 'Home Automation', 'Security Systems'],
            ['Plumbing', 'Septic Systems', 'Well Pumps'],
            ['Construction', 'Concrete', 'Masonry', 'Stonework'],
            ['Painting', 'Spray Painting', 'Industrial Coating'],
            ['Driving', 'Truck Driving', 'CDL', 'Long Distance']
        ]
        
        cities = [
            'New York, NY', 'Los Angeles, CA', 'Chicago, IL', 'Houston, TX',
            'Phoenix, AZ', 'Philadelphia, PA', 'San Antonio, TX', 'San Diego, CA',
            'Dallas, TX', 'San Jose, CA', 'Austin, TX', 'Jacksonville, FL',
            'Fort Worth, TX', 'Columbus, OH', 'Charlotte, NC', 'San Francisco, CA',
            'Indianapolis, IN', 'Seattle, WA', 'Denver, CO', 'Washington, DC'
        ]
        
        first_names = [
            'John', 'Jane', 'Mike', 'Sarah', 'David', 'Lisa', 'Chris', 'Amy',
            'Tom', 'Maria', 'Steve', 'Anna', 'Paul', 'Emma', 'Mark', 'Jessica',
            'Brian', 'Ashley', 'Kevin', 'Nicole', 'Ryan', 'Michelle', 'Jason', 'Laura'
        ]
        
        last_names = [
            'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
            'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
            'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson', 'White'
        ]
        
        created_count = 0
        
        # Create predefined workers first
        for i, profile in enumerate(worker_profiles[:min(count, len(worker_profiles))]):
            email = profile['email']
            
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(f"Worker {email} already exists, skipping...")
                continue
            
            try:
                user = User.objects.create_user(
                    email=email,
                    password='testpass123',
                    first_name=profile['first_name'],
                    last_name=profile['last_name'],
                    role='worker',
                    skills=profile['skills'],
                    bio=profile['bio'],
                    years_of_experience=profile['years_of_experience'],
                    address=profile['address'],
                    average_rating=profile['average_rating'],
                    total_reviews=profile['total_reviews'],
                    total_completed_jobs=profile['total_completed_jobs'],
                    is_verified=random.choice([True, False])  # Random verification status
                )
                created_count += 1
                self.stdout.write(f"Created worker: {user.full_name} ({email})")
                
            except Exception as e:
                self.stdout.write(f"Error creating worker {email}: {str(e)}")
        
        # Create additional random workers if needed
        remaining_count = count - created_count
        for i in range(remaining_count):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            email = f"{first_name.lower()}.{last_name.lower()}{i+100}@example.com"
            
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                continue
            
            try:
                skills = random.choice(skill_sets)
                experience = random.randint(1, 15)
                rating = round(random.uniform(3.5, 5.0), 1)
                reviews = random.randint(5, 80)
                jobs = random.randint(reviews, reviews + 20)
                
                # Generate bio based on skills
                skill_desc = ', '.join(skills[:2])
                bio = f"Professional {skills[0].lower()} specialist with expertise in {skill_desc.lower()}."
                
                user = User.objects.create_user(
                    email=email,
                    password='testpass123',
                    first_name=first_name,
                    last_name=last_name,
                    role='worker',
                    skills=skills,
                    bio=bio,
                    years_of_experience=experience,
                    address=random.choice(cities),
                    average_rating=Decimal(str(rating)),
                    total_reviews=reviews,
                    total_completed_jobs=jobs,
                    is_verified=random.choice([True, False])
                )
                created_count += 1
                self.stdout.write(f"Created worker: {user.full_name} ({email})")
                
            except Exception as e:
                self.stdout.write(f"Error creating worker {email}: {str(e)}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} worker users')
        ) 