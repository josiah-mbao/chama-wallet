#!/bin/bash
# Script to generate self-signed SSL certificates for development/testing
# DO NOT USE THESE CERTIFICATES IN PRODUCTION!

set -e

SSL_DIR="./ssl"
CERT_FILE="$SSL_DIR/cert.pem"
KEY_FILE="$SSL_DIR/key.pem"

# Create SSL directory if it doesn't exist
mkdir -p "$SSL_DIR"

echo "Generating self-signed SSL certificate for development..."
echo "⚠️  WARNING: This certificate is for development/testing only!"
echo "   Do not use in production!"
echo ""

# Generate private key
openssl genrsa -out "$KEY_FILE" 2048

# Generate certificate signing request
openssl req -new -key "$KEY_FILE" -out "$SSL_DIR/cert.csr" -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate self-signed certificate
openssl x509 -req -days 365 -in "$SSL_DIR/cert.csr" -signkey "$KEY_FILE" -out "$CERT_FILE"

# Clean up CSR file
rm "$SSL_DIR/cert.csr"

# Set proper permissions
chmod 600 "$KEY_FILE"
chmod 644 "$CERT_FILE"

echo "✅ SSL certificate generated successfully!"
echo "   Certificate: $CERT_FILE"
echo "   Private Key: $KEY_FILE"
echo ""
echo "To use in production, replace these with certificates from a trusted CA."
echo "For Let's Encrypt certificates, you can use certbot:"
echo "  sudo certbot certonly --standalone -d yourdomain.com"
echo ""
echo "Then update docker-compose.prod.yml to mount your real certificates."
