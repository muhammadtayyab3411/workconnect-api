from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Job, Bid
import random
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample bids for testing'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample bids...')
        
        # Get some workers and jobs
        workers = User.objects.filter(role='worker')[:10]
        jobs = Job.objects.filter(status='open')[:5]
        
        if not workers.exists():
            self.stdout.write(self.style.ERROR('No workers found. Please create workers first.'))
            return
        
        if not jobs.exists():
            self.stdout.write(self.style.ERROR('No open jobs found. Please create jobs first.'))
            return
        
        # Sample proposals
        proposals = [
            "I have extensive experience in this type of work and can deliver high-quality results within your timeline. My approach focuses on attention to detail and clear communication throughout the project.",
            "With over 5 years of experience in similar projects, I'm confident I can exceed your expectations. I pride myself on delivering work on time and within budget.",
            "I specialize in this exact type of work and have completed numerous similar projects. I would love to discuss your requirements in more detail.",
            "I'm very interested in this project and believe my skills are a perfect match. I can start immediately and deliver exceptional results.",
            "Having reviewed your project requirements, I'm excited to offer my services. My experience and dedication ensure quality work every time.",
            "I have the perfect skill set for this project and can guarantee professional results. Let's discuss how I can help bring your vision to life.",
            "This project aligns perfectly with my expertise. I'm committed to delivering outstanding work and maintaining excellent communication.",
            "I'm passionate about this type of work and would be thrilled to contribute to your project. My track record speaks for itself.",
            "With my background and experience, I can provide exactly what you're looking for. I'm available to start right away.",
            "I understand your requirements and have the skills to deliver exceptional results. Quality and timeliness are my top priorities."
        ]
        
        # Sample availability texts
        availabilities = [
            "Available to start immediately",
            "Can start within 1-2 days",
            "Available next week",
            "Can begin work within 3-5 days",
            "Ready to start ASAP",
            "Available starting Monday",
            "Can start within one week",
            "Immediate availability",
            "Available to begin within 2-3 days",
            "Can start this weekend"
        ]
        
        created_count = 0
        
        for job in jobs:
            # Create 3-8 bids per job
            num_bids = random.randint(3, 8)
            selected_workers = random.sample(list(workers), min(num_bids, len(workers)))
            
            for worker in selected_workers:
                # Check if bid already exists
                if Bid.objects.filter(job=job, worker=worker).exists():
                    continue
                
                # Calculate bid price (80% to 120% of job budget)
                base_price = float(job.budget)
                variation = random.uniform(0.8, 1.2)
                bid_price = Decimal(str(round(base_price * variation, 2)))
                
                # Random proposal and availability
                proposal = random.choice(proposals)
                availability = random.choice(availabilities)
                
                # Create the bid
                bid = Bid.objects.create(
                    job=job,
                    worker=worker,
                    price=bid_price,
                    availability=availability,
                    proposal=proposal,
                    status='pending'
                )
                
                created_count += 1
                self.stdout.write(f'Created bid: {worker.full_name} -> {job.title} (${bid_price})')
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} sample bids')
        ) 