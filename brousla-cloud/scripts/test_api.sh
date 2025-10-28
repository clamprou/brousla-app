#!/bin/bash

# Test script for Brousla Cloud API
# Usage: ./scripts/test_api.sh

set -e

API_URL="${BROUSLA_CLOUD_URL:-http://localhost:8000}"
EMAIL="test_$(date +%s)@example.com"
PASSWORD="password123"

echo "🧪 Testing Brousla Cloud API at $API_URL"
echo ""

# Test 1: Health check
echo "1️⃣  Testing health endpoint..."
curl -s "$API_URL/health" | grep -q "healthy" && echo "✅ Health check passed" || echo "❌ Health check failed"
echo ""

# Test 2: Register user
echo "2️⃣  Registering user: $EMAIL"
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"pwd\":\"$PASSWORD\"}")

ACCESS_TOKEN=$(echo $REGISTER_RESPONSE | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -n "$ACCESS_TOKEN" ]; then
  echo "✅ Registration successful"
  echo "   Token: ${ACCESS_TOKEN:0:20}..."
else
  echo "❌ Registration failed"
  echo "   Response: $REGISTER_RESPONSE"
  exit 1
fi
echo ""

# Test 3: Login
echo "3️⃣  Testing login..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"pwd\":\"$PASSWORD\"}")

LOGIN_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | sed 's/"access_token":"//')

if [ -n "$LOGIN_TOKEN" ]; then
  echo "✅ Login successful"
else
  echo "❌ Login failed"
  exit 1
fi
echo ""

# Test 4: Register device
echo "4️⃣  Registering device..."
DEVICE_ID="test_device_$(date +%s)"
DEVICE_RESPONSE=$(curl -s -X POST "$API_URL/devices/register" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d "{\"device_id\":\"$DEVICE_ID\",\"app_version\":\"1.0.0\"}")

echo $DEVICE_RESPONSE | grep -q "successfully" && echo "✅ Device registered" || echo "❌ Device registration failed"
echo ""

# Test 5: Get entitlements
echo "5️⃣  Getting entitlements..."
ENTITLEMENTS_RESPONSE=$(curl -s -X GET "$API_URL/entitlements" \
  -H "Authorization: Bearer $ACCESS_TOKEN")

LICENSE_JWT=$(echo $ENTITLEMENTS_RESPONSE | grep -o '"license_jwt":"[^"]*' | sed 's/"license_jwt":"//')

if [ -n "$LICENSE_JWT" ]; then
  echo "✅ Entitlements retrieved"
  echo "   License: ${LICENSE_JWT:0:30}..."
else
  echo "❌ Failed to get entitlements"
  echo "   Response: $ENTITLEMENTS_RESPONSE"
  exit 1
fi
echo ""

# Test 6: Get public key
echo "6️⃣  Getting public key (JWK)..."
PUBKEY_RESPONSE=$(curl -s -X GET "$API_URL/pubkey")

echo $PUBKEY_RESPONSE | grep -q '"keys"' && echo "✅ Public key retrieved" || echo "❌ Failed to get public key"
echo ""

# Test 7: Report usage
echo "7️⃣  Reporting usage..."
USAGE_RESPONSE=$(curl -s -X POST "$API_URL/usage/report" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"type":"render","qty":1}')

echo $USAGE_RESPONSE | grep -q "recorded" && echo "✅ Usage reported" || echo "❌ Failed to report usage"
echo ""

echo "🎉 All tests passed!"
echo ""
echo "Summary:"
echo "  Email: $EMAIL"
echo "  Password: $PASSWORD"
echo "  Access Token: ${ACCESS_TOKEN:0:30}..."
echo "  License JWT: ${LICENSE_JWT:0:30}..."
