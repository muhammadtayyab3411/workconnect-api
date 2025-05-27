from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, JobInvoice, PaymentMethod, StripeWebhookEvent


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_monthly', 'price_yearly', 'max_jobs_per_month', 'platform_fee_percentage', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'billing_cycle', 'current_period_end', 'cancel_at_period_end']
    list_filter = ['status', 'billing_cycle', 'plan', 'cancel_at_period_end']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'stripe_customer_id']
    readonly_fields = ['stripe_customer_id', 'stripe_subscription_id', 'created_at', 'updated_at']
    raw_id_fields = ['user']


@admin.register(JobInvoice)
class JobInvoiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'client', 'worker', 'total_amount', 'status', 'due_date', 'paid_at']
    list_filter = ['status', 'created_at', 'due_date', 'paid_at']
    search_fields = ['job__title', 'client__email', 'worker__email', 'stripe_invoice_id']
    readonly_fields = ['stripe_invoice_id', 'stripe_payment_intent_id', 'created_at', 'updated_at']
    raw_id_fields = ['job', 'client', 'worker']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'brand', 'last_four', 'is_default', 'created_at']
    list_filter = ['type', 'brand', 'is_default']
    search_fields = ['user__email', 'stripe_payment_method_id', 'last_four']
    readonly_fields = ['stripe_payment_method_id', 'created_at']
    raw_id_fields = ['user']


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ['stripe_event_id', 'event_type', 'processed', 'created_at']
    list_filter = ['event_type', 'processed', 'created_at']
    search_fields = ['stripe_event_id', 'event_type']
    readonly_fields = ['created_at']
