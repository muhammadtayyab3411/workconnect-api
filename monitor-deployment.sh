#!/bin/bash

# Monitor WorkConnect API Deployment
API_URL="https://workconnect-api.onrender.com"

echo "🔍 Monitoring WorkConnect API Deployment..."
echo "==========================================="
echo ""

# Function to test admin endpoint
test_admin() {
    echo "Testing admin interface..."
    response=$(curl -s -w "%{http_code}" "$API_URL/admin/" -o /tmp/admin_response.html 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        # Check if the response contains the login form (indicating migrations worked)
        if grep -q "django-admin" /tmp/admin_response.html 2>/dev/null; then
            echo "✅ Admin interface is working! Migrations completed successfully."
            return 0
        else
            echo "⚠️  Admin responded but may have issues."
            return 1
        fi
    else
        echo "❌ Admin interface failed (HTTP $response)"
        return 1
    fi
}

# Function to test health endpoint
test_health() {
    response=$(curl -s "$API_URL/api/health/" 2>/dev/null)
    if echo "$response" | grep -q "healthy"; then
        echo "✅ Health check passed"
        return 0
    else
        echo "❌ Health check failed"
        return 1
    fi
}

# Monitor deployment
echo "Waiting for deployment to complete..."
attempt=1
max_attempts=20

while [ $attempt -le $max_attempts ]; do
    echo ""
    echo "🔄 Attempt $attempt/$max_attempts ($(date))"
    
    # Test health first
    if test_health; then
        echo "API is responding, testing admin interface..."
        
        if test_admin; then
            echo ""
            echo "🎉 SUCCESS! Deployment completed successfully!"
            echo ""
            echo "📋 Working endpoints:"
            echo "- Health: $API_URL/api/health/"
            echo "- Admin: $API_URL/admin/"
            echo "- API: $API_URL/api/"
            echo ""
            echo "🔑 Admin credentials:"
            echo "- Username: admin"
            echo "- Email: admin@workconnect.com"
            echo "- Password: admin123"
            echo ""
            exit 0
        else
            echo "Admin interface still has issues, waiting..."
        fi
    else
        echo "API not ready yet, waiting..."
    fi
    
    attempt=$((attempt + 1))
    sleep 15
done

echo ""
echo "❌ Deployment monitoring timed out after $((max_attempts * 15)) seconds"
echo ""
echo "🔍 Manual checks:"
echo "1. Check Render dashboard for deployment status"
echo "2. Review deployment logs"
echo "3. Test endpoints manually:"
echo "   curl $API_URL/api/health/"
echo "   curl $API_URL/admin/"

# Cleanup
rm -f /tmp/admin_response.html 