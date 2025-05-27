#!/bin/bash

# WorkConnect API Deployment Script
# This script helps with common deployment tasks

set -e

echo "🚀 WorkConnect API Deployment Helper"
echo "===================================="

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  local     - Start local development with Docker Compose"
    echo "  build     - Build production Docker image"
    echo "  test      - Test the application"
    echo "  migrate   - Run database migrations"
    echo "  collect   - Collect static files"
    echo "  help      - Show this help message"
    echo ""
}

# Function to start local development
start_local() {
    echo "🐳 Starting local development environment..."
    if command -v docker-compose &> /dev/null; then
        docker-compose up --build
    else
        echo "❌ Docker Compose not found. Please install Docker first."
        exit 1
    fi
}

# Function to build production image
build_production() {
    echo "🏗️  Building production Docker image..."
    if command -v docker &> /dev/null; then
        docker build -f Dockerfile.render -t workconnect-api:latest .
        echo "✅ Production image built successfully!"
    else
        echo "❌ Docker not found. Please install Docker first."
        exit 1
    fi
}

# Function to run tests
run_tests() {
    echo "🧪 Running tests..."
    if [ -f "manage.py" ]; then
        python manage.py test
    else
        echo "❌ manage.py not found. Make sure you're in the project directory."
        exit 1
    fi
}

# Function to run migrations
run_migrations() {
    echo "📊 Running database migrations..."
    if [ -f "manage.py" ]; then
        python manage.py migrate
    else
        echo "❌ manage.py not found. Make sure you're in the project directory."
        exit 1
    fi
}

# Function to collect static files
collect_static() {
    echo "📁 Collecting static files..."
    if [ -f "manage.py" ]; then
        python manage.py collectstatic --noinput
    else
        echo "❌ manage.py not found. Make sure you're in the project directory."
        exit 1
    fi
}

# Main script logic
case "${1:-help}" in
    "local")
        start_local
        ;;
    "build")
        build_production
        ;;
    "test")
        run_tests
        ;;
    "migrate")
        run_migrations
        ;;
    "collect")
        collect_static
        ;;
    "help"|*)
        show_usage
        ;;
esac 