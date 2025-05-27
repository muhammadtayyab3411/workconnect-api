import stripe
from django.conf import settings
from django.contrib.auth import get_user_model
from decimal import Decimal
from .models import UserSubscription, SubscriptionPlan, JobInvoice, PaymentMethod

User = get_user_model()

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service class for handling Stripe operations"""

    @staticmethod
    def create_customer(user):
        """Create a Stripe customer for a user"""
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip(),
                metadata={
                    'user_id': user.id,
                    'platform': 'workconnect'
                }
            )
            return customer
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create Stripe customer: {str(e)}")

    @staticmethod
    def get_or_create_customer(user):
        """Get existing customer or create new one"""
        try:
            # Check if user already has a subscription with customer ID
            subscription = UserSubscription.objects.filter(user=user).first()
            if subscription and subscription.stripe_customer_id:
                try:
                    customer = stripe.Customer.retrieve(subscription.stripe_customer_id)
                    return customer
                except stripe.error.InvalidRequestError:
                    # Customer doesn't exist in Stripe, create new one
                    pass
            
            # Create new customer
            return StripeService.create_customer(user)
        except Exception as e:
            raise Exception(f"Failed to get or create customer: {str(e)}")

    @staticmethod
    def create_subscription(user, plan, payment_method_id, billing_cycle='monthly'):
        """Create a Stripe subscription"""
        try:
            customer = StripeService.get_or_create_customer(user)
            
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                customer.id,
                invoice_settings={'default_payment_method': payment_method_id},
            )
            
            # Get the correct price ID based on billing cycle
            price_id = plan.stripe_price_id_monthly if billing_cycle == 'monthly' else plan.stripe_price_id_yearly
            
            # Create subscription
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{'price': price_id}],
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent'],
            )
            
            return subscription
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create subscription: {str(e)}")

    @staticmethod
    def cancel_subscription(subscription_id, at_period_end=True):
        """Cancel a Stripe subscription"""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=at_period_end,
            )
            return subscription
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to cancel subscription: {str(e)}")

    @staticmethod
    def create_payment_intent(amount, customer_id, description="", metadata=None):
        """Create a payment intent for one-time payments"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Convert to cents
                currency='usd',
                customer=customer_id,
                description=description,
                metadata=metadata or {},
                automatic_payment_methods={'enabled': True},
            )
            return intent
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create payment intent: {str(e)}")

    @staticmethod
    def create_invoice_for_job(job_invoice):
        """Create a Stripe invoice for a completed job"""
        try:
            # Get or create customer
            customer = StripeService.get_or_create_customer(job_invoice.client)
            
            # Create invoice
            invoice = stripe.Invoice.create(
                customer=customer.id,
                description=f"Payment for job: {job_invoice.job.title}",
                metadata={
                    'job_id': job_invoice.job.id,
                    'job_invoice_id': job_invoice.id,
                    'worker_id': job_invoice.worker.id,
                },
                auto_advance=False,  # Don't auto-finalize
            )
            
            # Add invoice item
            stripe.InvoiceItem.create(
                customer=customer.id,
                invoice=invoice.id,
                amount=int(job_invoice.total_amount * 100),  # Convert to cents
                currency='usd',
                description=f"Job: {job_invoice.job.title}",
            )
            
            # Finalize the invoice
            invoice = stripe.Invoice.finalize_invoice(invoice.id)
            
            return invoice
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to create invoice: {str(e)}")

    @staticmethod
    def get_payment_methods(customer_id):
        """Get all payment methods for a customer"""
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=customer_id,
                type="card",
            )
            return payment_methods
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to get payment methods: {str(e)}")

    @staticmethod
    def detach_payment_method(payment_method_id):
        """Detach a payment method from customer"""
        try:
            payment_method = stripe.PaymentMethod.detach(payment_method_id)
            return payment_method
        except stripe.error.StripeError as e:
            raise Exception(f"Failed to detach payment method: {str(e)}")

    @staticmethod
    def calculate_job_fees(job_amount, platform_fee_percentage):
        """Calculate fees for a job"""
        job_amount = Decimal(str(job_amount))
        platform_fee_percentage = Decimal(str(platform_fee_percentage))
        
        # Calculate platform fee
        platform_fee = (job_amount * platform_fee_percentage / 100).quantize(Decimal('0.01'))
        
        # Calculate Stripe fee (2.9% + $0.30)
        stripe_fee = ((job_amount + platform_fee) * Decimal('0.029') + Decimal('0.30')).quantize(Decimal('0.01'))
        
        # Total amount client pays
        total_amount = job_amount + platform_fee + stripe_fee
        
        # Amount worker receives
        worker_payout = job_amount - platform_fee
        
        return {
            'job_amount': job_amount,
            'platform_fee': platform_fee,
            'stripe_fee': stripe_fee,
            'total_amount': total_amount,
            'worker_payout': worker_payout
        } 