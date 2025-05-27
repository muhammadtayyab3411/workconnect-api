from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class SubscriptionPlan(models.Model):
    """Subscription plans available on the platform"""
    name = models.CharField(max_length=100)  # "Starter", "Professional", "Enterprise"
    stripe_price_id_monthly = models.CharField(max_length=100, blank=True)  # Stripe Price ID for monthly
    stripe_price_id_yearly = models.CharField(max_length=100, blank=True)  # Stripe Price ID for yearly
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.JSONField(default=list)  # List of features
    max_jobs_per_month = models.IntegerField(null=True, blank=True)  # null = unlimited
    platform_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)  # Platform fee %
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price_monthly']

    def __str__(self):
        return f"{self.name} - ${self.price_monthly}/month"


class UserSubscription(models.Model):
    """User's current subscription status"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('unpaid', 'Unpaid'),
        ('incomplete', 'Incomplete'),
        ('incomplete_expired', 'Incomplete Expired'),
        ('trialing', 'Trialing'),
    ]

    BILLING_CYCLE_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    stripe_customer_id = models.CharField(max_length=100)
    stripe_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='incomplete')
    billing_cycle = models.CharField(max_length=10, choices=BILLING_CYCLE_CHOICES, default='monthly')
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField()
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"

    @property
    def is_active(self):
        return self.status == 'active'

    @property
    def jobs_used_this_month(self):
        """Count jobs created by user this billing period"""
        from users.models import Job
        return Job.objects.filter(
            client=self.user,
            created_at__gte=self.current_period_start,
            created_at__lt=self.current_period_end
        ).count()

    @property
    def can_create_job(self):
        """Check if user can create more jobs based on their plan"""
        if not self.is_active:
            return False
        if self.plan.max_jobs_per_month is None:  # Unlimited
            return True
        return self.jobs_used_this_month < self.plan.max_jobs_per_month


class JobInvoice(models.Model):
    """Invoices for completed jobs"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('canceled', 'Canceled'),
    ]

    job = models.OneToOneField('users.Job', on_delete=models.CASCADE, related_name='invoice')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_invoices')
    worker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='worker_invoices')
    stripe_invoice_id = models.CharField(max_length=100, null=True, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Financial breakdown
    job_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Original job amount
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)  # Platform fee
    stripe_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Stripe processing fee
    worker_payout = models.DecimalField(max_digits=10, decimal_places=2)  # Amount worker receives
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Total client pays
    
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Invoice #{self.id} - {self.job.title} - ${self.total_amount}"

    def save(self, *args, **kwargs):
        if not self.due_date:
            self.due_date = timezone.now() + timezone.timedelta(days=7)  # 7 days to pay
        super().save(*args, **kwargs)


class PaymentMethod(models.Model):
    """User's saved payment methods"""
    TYPE_CHOICES = [
        ('card', 'Card'),
        ('bank_account', 'Bank Account'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    stripe_payment_method_id = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    
    # Card details (if type is card)
    last_four = models.CharField(max_length=4, blank=True)
    brand = models.CharField(max_length=50, blank=True)  # visa, mastercard, etc.
    exp_month = models.IntegerField(null=True, blank=True)
    exp_year = models.IntegerField(null=True, blank=True)
    
    # Bank account details (if type is bank_account)
    bank_name = models.CharField(max_length=100, blank=True)
    account_holder_type = models.CharField(max_length=50, blank=True)
    
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'stripe_payment_method_id']

    def __str__(self):
        if self.type == 'card':
            return f"{self.brand.title()} ending in {self.last_four}"
        return f"{self.bank_name} - {self.account_holder_type}"

    def save(self, *args, **kwargs):
        # If this is set as default, unset all other default payment methods for this user
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class StripeWebhookEvent(models.Model):
    """Track processed Stripe webhook events to prevent duplicates"""
    stripe_event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"
