from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Stripe configuration
    path('stripe/config/', views.stripe_config, name='stripe_config'),
    
    # Subscription management
    path('subscription/plans/', views.subscription_plans, name='subscription_plans'),
    path('subscription/current/', views.current_subscription, name='current_subscription'),
    path('subscription/create/', views.create_subscription, name='create_subscription'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    
    # Payment methods
    path('payment-methods/', views.payment_methods, name='payment_methods'),
    path('payment-methods/add/', views.add_payment_method, name='add_payment_method'),
    path('payment-methods/<int:payment_method_id>/remove/', views.remove_payment_method, name='remove_payment_method'),
    
    # Invoices
    path('invoices/', views.invoices, name='invoices'),
    path('invoices/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:invoice_id>/pay/', views.pay_invoice, name='pay_invoice'),
    
    # Stripe webhooks
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
] 