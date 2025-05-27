import stripe
from django.core.management.base import BaseCommand
from django.conf import settings
from payments.models import SubscriptionPlan

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class Command(BaseCommand):
    help = 'Set up WorkConnect subscription plans in Stripe and Django'

    def handle(self, *args, **options):
        self.stdout.write('Setting up WorkConnect subscription plans...')
        
        # Plan configurations
        plans_config = [
            {
                'name': 'Starter',
                'description': 'Perfect for new clients getting started with hiring freelancers',
                'price_monthly': 29.00,
                'price_yearly': 290.00,  # 2 months free
                'max_jobs_per_month': 5,
                'platform_fee_percentage': 10.00,
                'features': [
                    'Up to 5 job postings per month',
                    'Basic messaging system',
                    'Standard support',
                    '10% platform fee',
                    'Basic analytics'
                ]
            },
            {
                'name': 'Professional',
                'description': 'For growing businesses that need more job postings and advanced features',
                'price_monthly': 79.00,
                'price_yearly': 790.00,  # 2 months free
                'max_jobs_per_month': 25,
                'platform_fee_percentage': 7.50,
                'features': [
                    'Up to 25 job postings per month',
                    'Advanced messaging system',
                    'Priority support',
                    '7.5% platform fee',
                    'Advanced analytics',
                    'Custom job templates',
                    'Bulk actions'
                ]
            },
            {
                'name': 'Enterprise',
                'description': 'For large organizations with unlimited job postings and dedicated support',
                'price_monthly': 199.00,
                'price_yearly': 1990.00,  # 2 months free
                'max_jobs_per_month': None,  # Unlimited
                'platform_fee_percentage': 5.00,
                'features': [
                    'Unlimited job postings',
                    'Advanced messaging system',
                    'Dedicated account manager',
                    '5% platform fee',
                    'Advanced analytics',
                    'Custom job templates',
                    'Bulk actions',
                    'API access',
                    'Custom integrations',
                    'White-label options'
                ]
            }
        ]

        for plan_config in plans_config:
            self.stdout.write(f'Creating {plan_config["name"]} plan...')
            
            try:
                # Create Stripe product
                product = stripe.Product.create(
                    name=f'WorkConnect {plan_config["name"]}',
                    description=plan_config['description'],
                    type='service',
                    metadata={
                        'plan_name': plan_config['name'],
                        'platform': 'workconnect'
                    }
                )
                
                # Create monthly price
                monthly_price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(plan_config['price_monthly'] * 100),  # Convert to cents
                    currency='usd',
                    recurring={'interval': 'month'},
                    nickname=f'{plan_config["name"]} Monthly',
                    metadata={
                        'plan_name': plan_config['name'],
                        'billing_cycle': 'monthly'
                    }
                )
                
                # Create yearly price
                yearly_price = stripe.Price.create(
                    product=product.id,
                    unit_amount=int(plan_config['price_yearly'] * 100),  # Convert to cents
                    currency='usd',
                    recurring={'interval': 'year'},
                    nickname=f'{plan_config["name"]} Yearly',
                    metadata={
                        'plan_name': plan_config['name'],
                        'billing_cycle': 'yearly'
                    }
                )
                
                # Create or update Django subscription plan
                subscription_plan, created = SubscriptionPlan.objects.update_or_create(
                    name=plan_config['name'],
                    defaults={
                        'stripe_price_id_monthly': monthly_price.id,
                        'stripe_price_id_yearly': yearly_price.id,
                        'price_monthly': plan_config['price_monthly'],
                        'price_yearly': plan_config['price_yearly'],
                        'features': plan_config['features'],
                        'max_jobs_per_month': plan_config['max_jobs_per_month'],
                        'platform_fee_percentage': plan_config['platform_fee_percentage'],
                        'is_active': True
                    }
                )
                
                action = 'Created' if created else 'Updated'
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{action} {plan_config["name"]} plan:\n'
                        f'  - Product ID: {product.id}\n'
                        f'  - Monthly Price ID: {monthly_price.id}\n'
                        f'  - Yearly Price ID: {yearly_price.id}\n'
                        f'  - Django Plan ID: {subscription_plan.id}'
                    )
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating {plan_config["name"]} plan: {str(e)}')
                )
        
        self.stdout.write(self.style.SUCCESS('Subscription plans setup completed!')) 