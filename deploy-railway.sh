#!/bin/bash
# Railway Deployment Script for Chama Wallet API
# This script helps with Railway-specific deployment tasks

set -e

echo "🚂 Chama Wallet Railway Deployment Script"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Railway CLI is installed
check_railway_cli() {
    if ! command -v railway &> /dev/null; then
        print_error "Railway CLI is not installed."
        print_status "Install it with: npm install -g @railway/cli"
        exit 1
    fi
}

# Generate SSL certificates for development/testing
generate_ssl_certs() {
    print_status "Generating SSL certificates..."
    if [ ! -d "ssl" ]; then
        mkdir -p ssl
    fi

    if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
        ./generate_ssl_cert.sh
        print_success "SSL certificates generated"
    else
        print_warning "SSL certificates already exist"
    fi
}

# Validate environment configuration
validate_config() {
    print_status "Validating configuration..."

    # Check if railway.toml exists
    if [ ! -f "railway.toml" ]; then
        print_error "railway.toml not found!"
        exit 1
    fi

    # Check if Dockerfile exists
    if [ ! -f "backend/Dockerfile" ]; then
        print_error "backend/Dockerfile not found!"
        exit 1
    fi

    print_success "Configuration validated"
}

# Deploy to Railway
deploy_to_railway() {
    print_status "Deploying to Railway..."

    # Check if logged in to Railway
    if ! railway status &> /dev/null; then
        print_error "Not logged in to Railway. Run: railway login"
        exit 1
    fi

    # Deploy the application
    railway up

    print_success "Deployment initiated"
    print_status "Monitor deployment with: railway logs"
}

# Setup Railway services
setup_services() {
    print_status "Setting up Railway services..."

    # Add PostgreSQL service
    print_status "Adding PostgreSQL service..."
    railway add postgres

    # Add Redis service
    print_status "Adding Redis service..."
    railway add redis

    print_success "Services added"
    print_warning "Remember to set environment variables in Railway dashboard"
}

# Run database migrations (for local testing)
run_migrations() {
    print_status "Running database migrations..."

    if [ -z "$DATABASE_URL" ]; then
        print_error "DATABASE_URL not set. Set it in Railway dashboard or locally."
        exit 1
    fi

    # Run migrations using Docker
    docker run --rm \
        -e DATABASE_URL="$DATABASE_URL" \
        -v "$(pwd):/app" \
        -w /app/backend \
        python:3.11-slim \
        bash -c "
            pip install -r requirements.txt &&
            alembic upgrade head
        "

    print_success "Migrations completed"
}

# Show deployment status
show_status() {
    print_status "Checking Railway deployment status..."
    railway status
}

# Main menu
show_menu() {
    echo
    echo "Available commands:"
    echo "  1) Check Railway CLI installation"
    echo "  2) Generate SSL certificates"
    echo "  3) Validate configuration"
    echo "  4) Setup Railway services (PostgreSQL + Redis)"
    echo "  5) Deploy to Railway"
    echo "  6) Run database migrations"
    echo "  7) Show deployment status"
    echo "  8) Full deployment (steps 2-5)"
    echo "  9) Exit"
    echo
}

# Full deployment process
full_deployment() {
    print_status "Starting full Railway deployment process..."

    check_railway_cli
    generate_ssl_certs
    validate_config
    setup_services
    deploy_to_railway

    print_success "Full deployment process completed!"
    print_warning "Don't forget to:"
    echo "  1. Set environment variables in Railway dashboard"
    echo "  2. Run database migrations after first deployment"
    echo "  3. Update CORS_ORIGINS with your Railway domain"
}

# Main script logic
case "${1:-}" in
    "check-cli")
        check_railway_cli
        ;;
    "ssl")
        generate_ssl_certs
        ;;
    "validate")
        validate_config
        ;;
    "services")
        setup_services
        ;;
    "deploy")
        deploy_to_railway
        ;;
    "migrate")
        run_migrations
        ;;
    "status")
        show_status
        ;;
    "full")
        full_deployment
        ;;
    "menu"|*)
        show_menu
        ;;
esac
