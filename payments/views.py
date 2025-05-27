from django.shortcuts import render
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.shortcuts import get_object_or_404
from .models import SubscriptionPlan, UserSubscription, JobInvoice, PaymentMethod
from .serializers import (
    SubscriptionPlanSerializer, UserSubscriptionSerializer, CreateSubscriptionSerializer,
    JobInvoiceSerializer, PaymentMethodSerializer, AddPaymentMethodSerializer,
    PayInvoiceSerializer, StripeConfigSerializer, CreatePaymentIntentSerializer
)
from .stripe_service import StripeService
import stripe
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from django.utils import timezone
import json
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
def stripe_config(request):
    """Get Stripe publishable key - Public endpoint"""
    return Response({
        'publishable_key': settings.STRIPE_PUBLISHABLE_KEY
    })


@api_view(['GET'])
def subscription_plans(request):
    """List all active subscription plans - Public endpoint"""
    plans = SubscriptionPlan.objects.filter(is_active=True)
    serializer = SubscriptionPlanSerializer(plans, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_subscription(request):
    """Get user's current subscription"""
    try:
        subscription = UserSubscription.objects.get(user=request.user)
        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data)
    except UserSubscription.DoesNotExist:
        return Response({'detail': 'No active subscription found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    """Create a new subscription"""
    serializer = CreateSubscriptionSerializer(data=request.data)
    if serializer.is_valid():
        try:
            plan = SubscriptionPlan.objects.get(id=serializer.validated_data['plan_id'])
            payment_method_id = serializer.validated_data['payment_method_id']
            billing_cycle = serializer.validated_data['billing_cycle']
            
            # Create Stripe subscription
            stripe_subscription = StripeService.create_subscription(
                user=request.user,
                plan=plan,
                payment_method_id=payment_method_id,
                billing_cycle=billing_cycle
            )
            
            # Create or update local subscription record
            subscription, created = UserSubscription.objects.update_or_create(
                user=request.user,
                defaults={
                    'stripe_customer_id': stripe_subscription.customer,
                    'stripe_subscription_id': stripe_subscription.id,
                    'plan': plan,
                    'status': stripe_subscription.status,
                    'billing_cycle': billing_cycle,
                    'current_period_start': stripe_subscription.current_period_start,
                    'current_period_end': stripe_subscription.current_period_end,
                }
            )
            
            return Response({
                'subscription': UserSubscriptionSerializer(subscription).data,
                'client_secret': stripe_subscription.latest_invoice.payment_intent.client_secret
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """Cancel user's subscription"""
    try:
        subscription = UserSubscription.objects.get(user=request.user)
        
        # Cancel in Stripe
        StripeService.cancel_subscription(subscription.stripe_subscription_id)
        
        # Update local record
        subscription.cancel_at_period_end = True
        subscription.save()
        
        return Response({'message': 'Subscription cancelled successfully'})
        
    except UserSubscription.DoesNotExist:
        return Response({'error': 'No subscription found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payment_methods(request):
    """List user's payment methods"""
    methods = PaymentMethod.objects.filter(user=request.user)
    serializer = PaymentMethodSerializer(methods, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_payment_method(request):
    """Add a new payment method"""
    serializer = AddPaymentMethodSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Get or create Stripe customer
            customer = StripeService.get_or_create_customer(request.user)
            
            # Attach payment method to customer
            payment_method_id = serializer.validated_data['payment_method_id']
            stripe_pm = stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id,
            )
            
            # Create local payment method record
            payment_method = PaymentMethod.objects.create(
                user=request.user,
                stripe_payment_method_id=payment_method_id,
                type=stripe_pm.type,
                last_four=stripe_pm.card.last4 if stripe_pm.type == 'card' else '',
                brand=stripe_pm.card.brand if stripe_pm.type == 'card' else '',
                exp_month=stripe_pm.card.exp_month if stripe_pm.type == 'card' else None,
                exp_year=stripe_pm.card.exp_year if stripe_pm.type == 'card' else None,
                is_default=serializer.validated_data['is_default']
            )
            
            return Response(PaymentMethodSerializer(payment_method).data)
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_payment_method(request, payment_method_id):
    """Remove a payment method"""
    try:
        payment_method = PaymentMethod.objects.get(id=payment_method_id, user=request.user)
        
        # Detach from Stripe
        StripeService.detach_payment_method(payment_method.stripe_payment_method_id)
        
        # Delete local record
        payment_method.delete()
        
        return Response({'message': 'Payment method removed successfully'})
        
    except PaymentMethod.DoesNotExist:
        return Response({'error': 'Payment method not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoices(request):
    """List user's invoices"""
    user_invoices = JobInvoice.objects.filter(client=request.user).order_by('-created_at')
    serializer = JobInvoiceSerializer(user_invoices, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_detail(request, invoice_id):
    """Get specific invoice details"""
    invoice = get_object_or_404(JobInvoice, id=invoice_id, client=request.user)
    serializer = JobInvoiceSerializer(invoice)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_invoice(request, invoice_id):
    """Pay an invoice"""
    invoice = get_object_or_404(JobInvoice, id=invoice_id, client=request.user)
    
    if invoice.status != 'pending':
        return Response({'error': 'Invoice is not payable'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = PayInvoiceSerializer(data=request.data)
    if serializer.is_valid():
        try:
            # Get customer
            customer = StripeService.get_or_create_customer(request.user)
            
            # Create payment intent
            payment_intent = StripeService.create_payment_intent(
                amount=invoice.total_amount,
                customer_id=customer.id,
                description=f"Payment for job: {invoice.job.title}",
                metadata={
                    'invoice_id': invoice.id,
                    'job_id': invoice.job.id
                }
            )
            
            # Update invoice with payment intent ID
            invoice.stripe_payment_intent_id = payment_intent.id
            invoice.save()
            
            return Response({
                'client_secret': payment_intent.client_secret,
                'invoice': JobInvoiceSerializer(invoice).data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        logger.error("Invalid payload in Stripe webhook")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature in Stripe webhook")
        return HttpResponse(status=400)

    # Check if we've already processed this event
    from .models import StripeWebhookEvent
    webhook_event, created = StripeWebhookEvent.objects.get_or_create(
        stripe_event_id=event['id'],
        defaults={
            'event_type': event['type'],
            'processed': False
        }
    )
    
    if not created and webhook_event.processed:
        logger.info(f"Webhook event {event['id']} already processed")
        return HttpResponse(status=200)

    try:
        # Handle the event
        if event['type'] == 'customer.subscription.created':
            _handle_subscription_created(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            _handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            _handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            _handle_invoice_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            _handle_invoice_payment_failed(event['data']['object'])
        elif event['type'] == 'payment_intent.succeeded':
            _handle_payment_intent_succeeded(event['data']['object'])
        elif event['type'] == 'payment_intent.payment_failed':
            _handle_payment_intent_failed(event['data']['object'])
        else:
            logger.info(f"Unhandled event type: {event['type']}")

        # Mark as processed
        webhook_event.processed = True
        webhook_event.save()
        
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Error processing webhook {event['id']}: {str(e)}")
        return HttpResponse(status=500)


def _handle_subscription_created(subscription):
    """Handle subscription created event"""
    try:
        user_subscription = UserSubscription.objects.get(
            stripe_subscription_id=subscription['id']
        )
        user_subscription.status = subscription['status']
        user_subscription.save()
        logger.info(f"Updated subscription {subscription['id']} status to {subscription['status']}")
    except UserSubscription.DoesNotExist:
        logger.warning(f"Subscription {subscription['id']} not found in database")


def _handle_subscription_updated(subscription):
    """Handle subscription updated event"""
    try:
        user_subscription = UserSubscription.objects.get(
            stripe_subscription_id=subscription['id']
        )
        user_subscription.status = subscription['status']
        user_subscription.current_period_start = subscription['current_period_start']
        user_subscription.current_period_end = subscription['current_period_end']
        user_subscription.cancel_at_period_end = subscription.get('cancel_at_period_end', False)
        user_subscription.save()
        logger.info(f"Updated subscription {subscription['id']}")
    except UserSubscription.DoesNotExist:
        logger.warning(f"Subscription {subscription['id']} not found in database")


def _handle_subscription_deleted(subscription):
    """Handle subscription deleted event"""
    try:
        user_subscription = UserSubscription.objects.get(
            stripe_subscription_id=subscription['id']
        )
        user_subscription.status = 'canceled'
        user_subscription.save()
        logger.info(f"Canceled subscription {subscription['id']}")
    except UserSubscription.DoesNotExist:
        logger.warning(f"Subscription {subscription['id']} not found in database")


def _handle_invoice_payment_succeeded(invoice):
    """Handle successful invoice payment"""
    # This is for subscription invoices
    logger.info(f"Invoice {invoice['id']} payment succeeded")


def _handle_invoice_payment_failed(invoice):
    """Handle failed invoice payment"""
    logger.warning(f"Invoice {invoice['id']} payment failed")


def _handle_payment_intent_succeeded(payment_intent):
    """Handle successful payment intent (for job payments)"""
    try:
        # Find job invoice by payment intent ID
        job_invoice = JobInvoice.objects.get(
            stripe_payment_intent_id=payment_intent['id']
        )
        job_invoice.status = 'paid'
        job_invoice.paid_at = timezone.now()
        job_invoice.save()
        
        # Update job status to completed
        job_invoice.job.status = 'completed'
        job_invoice.job.save()
        
        logger.info(f"Job invoice {job_invoice.id} marked as paid")
        
    except JobInvoice.DoesNotExist:
        logger.warning(f"Job invoice with payment intent {payment_intent['id']} not found")


def _handle_payment_intent_failed(payment_intent):
    """Handle failed payment intent"""
    try:
        job_invoice = JobInvoice.objects.get(
            stripe_payment_intent_id=payment_intent['id']
        )
        job_invoice.status = 'failed'
        job_invoice.save()
        logger.warning(f"Job invoice {job_invoice.id} payment failed")
    except JobInvoice.DoesNotExist:
        logger.warning(f"Job invoice with payment intent {payment_intent['id']} not found")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """Create a Stripe checkout session for subscription"""
    try:
        plan_id = request.data.get('plan_id')
        billing_cycle = request.data.get('billing_cycle', 'monthly')
        
        if not plan_id:
            return Response({'error': 'Plan ID is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the subscription plan
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({'error': 'Invalid plan'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user already has an active subscription
        existing_subscription = UserSubscription.objects.filter(
            user=request.user,
            status__in=['active', 'trialing']
        ).first()
        
        if existing_subscription:
            return Response({'error': 'User already has an active subscription'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create Stripe checkout session
        stripe_service = StripeService()
        
        # Get or create Stripe customer
        customer = stripe_service.get_or_create_customer(request.user)
        
        # Determine price based on billing cycle
        price = plan.price_monthly if billing_cycle == 'monthly' else plan.price_yearly
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'{plan.name} Plan',
                        'description': f'WorkConnect {plan.name} subscription - {billing_cycle} billing',
                    },
                    'unit_amount': int(price * 100),  # Convert to cents
                    'recurring': {
                        'interval': 'month' if billing_cycle == 'monthly' else 'year',
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{settings.FRONTEND_URL}/checkout/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.FRONTEND_URL}/checkout?cancelled=true",
            metadata={
                'user_id': request.user.id,
                'plan_id': plan.id,
                'billing_cycle': billing_cycle,
            }
        )
        
        return Response({
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        })
        
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return Response({'error': 'Failed to create checkout session'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
