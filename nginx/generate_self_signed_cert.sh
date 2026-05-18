#!/bin/sh
# Generate self-signed SSL certificate for development/testing
# For production, replace with Let's Encrypt or a real CA certificate.
#
# Usage:  sh nginx/generate_self_signed_cert.sh
# Output: nginx/ssl/cert.pem  nginx/ssl/key.pem

mkdir -p "$(dirname "$0")/ssl"

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout "$(dirname "$0")/ssl/key.pem" \
  -out    "$(dirname "$0")/ssl/cert.pem" \
  -subj   "/C=TH/ST=Bangkok/L=Bangkok/O=OmniSight/CN=omnisight.local"

echo "Self-signed certificate generated:"
echo "  cert: $(dirname "$0")/ssl/cert.pem"
echo "  key:  $(dirname "$0")/ssl/key.pem"
