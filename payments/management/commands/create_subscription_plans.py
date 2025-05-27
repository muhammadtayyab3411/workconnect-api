from django.core.management.base import BaseCommand
from payments.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Create initial subscription plans'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Starter',
                'price_monthly': 29.00,
                'price_yearly': 290.00,  # 2 months free
                'features': [
                    'Up to 5 jobs per month',
                    'Basic support',
                    'Standard platform fees (10%)',
                    'Basic job matching'
                ],
                'max_jobs_per_month': 5,
                'platform_fee_percentage': 10.00,
            },
            {
                'name': 'Professional',
                'price_monthly': 79.00,
                'price_yearly': 790.00,  # 2 months free
                'features': [
                    'Up to 20 jobs per month',
                    'Priority support',
                    'Reduced platform fees (7%)',
                    'Advanced job matching',
                    'Analytics dashboard'
                ],
                'max_jobs_per_month': 20,
                'platform_fee_percentage': 7.00,
            },
            {
                'name': 'Enterprise',
                'price_monthly': 199.00,
                'price_yearly': 1990.00,  # 2 months free
                'features': [
                    'Unlimited jobs',
                    '24/7 priority support',
                    'Lowest platform fees (5%)',
                    'Premium job matching',
                    'Advanced analytics',
                    'Custom integrations',
                    'Dedicated account manager'
                ],
                'max_jobs_per_month': None,  # Unlimited
                'platform_fee_percentage': 5.00,
            }
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults=plan_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created subscription plan: {plan.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Subscription plan already exists: {plan.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Successfully created/updated subscription plans')
        ) 