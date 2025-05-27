import stripe
from django.core.management.base import BaseCommand
from django.conf import settings

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class Command(BaseCommand):
    help = 'Set up Stripe webhook endpoints for WorkConnect'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='Base URL for webhook endpoints (e.g., https://api.workconnect.com)',
            required=True
        )

    def handle(self, *args, **options):
        base_url = options['url'].rstrip('/')
        webhook_url = f"{base_url}/api/payments/stripe/webhook/"
        
        self.stdout.write(f'Setting up Stripe webhook for: {webhook_url}')
        
        # Events we want to listen to
        events = [
            'customer.subscription.created',
            'customer.subscription.updated',
            'customer.subscription.deleted',
            'invoice.payment_succeeded',
            'invoice.payment_failed',
            'payment_intent.succeeded',
            'payment_intent.payment_failed',
            'customer.created',
            'customer.updated',
        ]
        
        try:
            # Create webhook endpoint
            webhook = stripe.WebhookEndpoint.create(
                url=webhook_url,
                enabled_events=events,
                description='WorkConnect platform webhook'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Webhook endpoint created successfully!\n'
                    f'  - Webhook ID: {webhook.id}\n'
                    f'  - URL: {webhook.url}\n'
                    f'  - Secret: {webhook.secret}\n\n'
                    f'Add this to your .env file:\n'
                    f'STRIPE_WEBHOOK_SECRET={webhook.secret}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating webhook: {str(e)}')
            ) 