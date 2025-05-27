#!/usr/bin/env python
"""
Test script to verify Stripe integration is working properly
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workconnect.settings')
django.setup()

from payments.models import SubscriptionPlan
from payments.stripe_service import StripeService
import stripe

def test_stripe_connection():
    """Test basic Stripe connection"""
    print("Testing Stripe connection...")
    try:
        # Test Stripe API key
        stripe.api_key = settings.STRIPE_SECRET_KEY
        balance = stripe.Balance.retrieve()
        print(f"✅ Stripe connection successful! Available balance: ${balance.available[0].amount / 100}")
        return True
    except Exception as e:
        print(f"❌ Stripe connection failed: {e}")
        return False

def test_subscription_plans():
    """Test subscription plans in database"""
    print("\nTesting subscription plans...")
    try:
        plans = SubscriptionPlan.objects.filter(is_active=True)
        print(f"✅ Found {plans.count()} active subscription plans:")
        for plan in plans:
            print(f"  - {plan.name}: ${plan.price_monthly}/month, ${plan.price_yearly}/year")
            print(f"    Max jobs: {plan.max_jobs_per_month or 'Unlimited'}")
            print(f"    Platform fee: {plan.platform_fee_percentage}%")
            print(f"    Stripe Monthly Price ID: {plan.stripe_price_id_monthly}")
            print(f"    Stripe Yearly Price ID: {plan.stripe_price_id_yearly}")
            print()
        return True
    except Exception as e:
        print(f"❌ Subscription plans test failed: {e}")
        return False

def test_stripe_products():
    """Test Stripe products and prices"""
    print("Testing Stripe products...")
    try:
        products = stripe.Product.list(limit=10)
        workconnect_products = [p for p in products.data if 'workconnect' in p.name.lower()]
        print(f"✅ Found {len(workconnect_products)} WorkConnect products in Stripe:")
        
        for product in workconnect_products:
            print(f"  - {product.name} ({product.id})")
            # Get prices for this product
            prices = stripe.Price.list(product=product.id)
            for price in prices.data:
                interval = price.recurring.interval if price.recurring else 'one-time'
                amount = price.unit_amount / 100 if price.unit_amount else 0
                print(f"    Price: ${amount} ({interval}) - {price.id}")
        return True
    except Exception as e:
        print(f"❌ Stripe products test failed: {e}")
        return False

def test_fee_calculation():
    """Test fee calculation"""
    print("\nTesting fee calculation...")
    try:
        test_amount = 100.00
        test_fee_percentage = 10.00
        
        fees = StripeService.calculate_job_fees(test_amount, test_fee_percentage)
        print(f"✅ Fee calculation for ${test_amount} job with {test_fee_percentage}% platform fee:")
        print(f"  - Job amount: ${fees['job_amount']}")
        print(f"  - Platform fee: ${fees['platform_fee']}")
        print(f"  - Stripe fee: ${fees['stripe_fee']}")
        print(f"  - Total client pays: ${fees['total_amount']}")
        print(f"  - Worker receives: ${fees['worker_payout']}")
        return True
    except Exception as e:
        print(f"❌ Fee calculation test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Stripe Integration Tests\n")
    
    tests = [
        test_stripe_connection,
        test_subscription_plans,
        test_stripe_products,
        test_fee_calculation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print("-" * 50)
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Stripe integration is ready.")
    else:
        print("⚠️  Some tests failed. Please check the configuration.")

if __name__ == "__main__":
    main() 