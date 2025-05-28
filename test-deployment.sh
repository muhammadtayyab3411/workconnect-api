#!/bin/bash

# WorkConnect API Deployment Test Script
# This script helps test the deployed API on Render

API_URL="https://workconnect-api.onrender.com"
HEALTH_ENDPOINT="/api/health/"
ADMIN_ENDPOINT="/admin/"

echo "🚀 Testing WorkConnect API Deployment"
echo "======================================"
echo "API URL: $API_URL"
echo ""

# Function to test endpoint
test_endpoint() {
    local endpoint=$1
    local description=$2
    local expected_status=${3:-200}
    
    echo "Testing $description..."
    echo "URL: $API_URL$endpoint"
    
    response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "$expected_status" ]; then
        echo "✅ SUCCESS: HTTP $http_code"
        if [ "$endpoint" = "$HEALTH_ENDPOINT" ]; then
            echo "Response: $body"
        fi
    else
        echo "❌ FAILED: HTTP $http_code (expected $expected_status)"
        if [ ! -z "$body" ]; then
            echo "Response: $body"
        fi
    fi
    echo ""
}

# Function to wait for deployment
wait_for_deployment() {
    echo "⏳ Waiting for deployment to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt/$max_attempts..."
        
        response=$(curl -s -w "%{http_code}" "$API_URL$HEALTH_ENDPOINT" -o /dev/null 2>/dev/null)
        
        if [ "$response" = "200" ]; then
            echo "✅ Deployment is ready!"
            return 0
        else
            echo "⏳ Still deploying... (HTTP $response)"
            sleep 10
        fi
        
        attempt=$((attempt + 1))
    done
    
    echo "❌ Deployment timeout after $((max_attempts * 10)) seconds"
    return 1
}

# Main testing sequence
echo "1. Checking if deployment is ready..."
wait_for_deployment

if [ $? -eq 0 ]; then
    echo ""
    echo "2. Running API tests..."
    echo "====================="
    
    # Test health endpoint
    test_endpoint "$HEALTH_ENDPOINT" "Health Check" 200
    
    # Test admin endpoint (should redirect or show login)
    test_endpoint "$ADMIN_ENDPOINT" "Admin Interface" 200
    
    # Test API root
    test_endpoint "/api/" "API Root" 404
    
    # Test auth endpoints (should require authentication)
    test_endpoint "/api/auth/profile/" "Profile Endpoint (should require auth)" 401
    
    # Test job categories (public endpoint)
    test_endpoint "/api/job-categories/" "Job Categories" 200
    
    echo "🎉 Deployment testing completed!"
    echo ""
    echo "📋 Summary:"
    echo "- Health check: $API_URL$HEALTH_ENDPOINT"
    echo "- Admin panel: $API_URL$ADMIN_ENDPOINT"
    echo "- API documentation: Check your API endpoints"
    echo ""
    echo "🔗 Useful URLs:"
    echo "- API Base: $API_URL/api/"
    echo "- Admin: $API_URL/admin/"
    echo "- Health: $API_URL/api/health/"
else
    echo ""
    echo "❌ Deployment is not ready. Please check Render logs."
    echo ""
    echo "🔍 Troubleshooting:"
    echo "1. Check Render dashboard for deployment status"
    echo "2. Review build and runtime logs"
    echo "3. Verify environment variables are set"
    echo "4. Check database connection"
fi 