from rest_framework import serializers
from .models import SubscriptionPlan, UserSubscription, JobInvoice, PaymentMethod


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'price_monthly', 'price_yearly', 'features',
            'max_jobs_per_month', 'platform_fee_percentage', 'is_active'
        ]


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscriptions"""
    plan = SubscriptionPlanSerializer(read_only=True)
    jobs_used_this_month = serializers.ReadOnlyField()
    can_create_job = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan', 'status', 'billing_cycle', 'current_period_start',
            'current_period_end', 'cancel_at_period_end', 'jobs_used_this_month',
            'can_create_job', 'is_active', 'created_at', 'updated_at'
        ]


class CreateSubscriptionSerializer(serializers.Serializer):
    """Serializer for creating a new subscription"""
    plan_id = serializers.IntegerField()
    payment_method_id = serializers.CharField(max_length=100)
    billing_cycle = serializers.ChoiceField(choices=['monthly', 'yearly'], default='monthly')
    
    def validate_plan_id(self, value):
        try:
            plan = SubscriptionPlan.objects.get(id=value, is_active=True)
            return value
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive subscription plan.")


class JobInvoiceSerializer(serializers.ModelSerializer):
    """Serializer for job invoices"""
    job_title = serializers.CharField(source='job.title', read_only=True)
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    worker_name = serializers.CharField(source='worker.get_full_name', read_only=True)
    
    class Meta:
        model = JobInvoice
        fields = [
            'id', 'job', 'job_title', 'client', 'client_name', 'worker', 'worker_name',
            'job_amount', 'platform_fee', 'stripe_fee', 'worker_payout', 'total_amount',
            'status', 'due_date', 'paid_at', 'created_at', 'updated_at'
        ]


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Serializer for payment methods"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'type', 'last_four', 'brand', 'exp_month', 'exp_year',
            'bank_name', 'account_holder_type', 'is_default', 'display_name',
            'created_at'
        ]
    
    def get_display_name(self, obj):
        if obj.type == 'card':
            return f"{obj.brand.title()} ending in {obj.last_four}"
        return f"{obj.bank_name} - {obj.account_holder_type}"


class AddPaymentMethodSerializer(serializers.Serializer):
    """Serializer for adding a new payment method"""
    payment_method_id = serializers.CharField(max_length=100)
    is_default = serializers.BooleanField(default=False)


class PayInvoiceSerializer(serializers.Serializer):
    """Serializer for paying an invoice"""
    payment_method_id = serializers.CharField(max_length=100, required=False)
    
    def validate(self, data):
        # If no payment method provided, we'll use the customer's default
        return data


class StripeConfigSerializer(serializers.Serializer):
    """Serializer for Stripe configuration"""
    publishable_key = serializers.CharField()


class CreatePaymentIntentSerializer(serializers.Serializer):
    """Serializer for creating payment intents"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    description = serializers.CharField(max_length=255, required=False)
    metadata = serializers.DictField(required=False) 