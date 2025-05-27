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


@api_view(['GET'])
def stripe_config(request):
    """Get Stripe publishable key"""
    return Response({
        'publishable_key': settings.STRIPE_PUBLISHABLE_KEY
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_plans(request):
    """List all active subscription plans"""
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
