#!/bin/bash

# Test script for JWT authentication
# This will help verify that both backends are properly configured

echo "🧪 Testing Backend Authentication"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test Article Summarizer Backend
echo "📝 Testing Article Summarizer Backend (http://localhost:8000)"
echo ""

# Test without auth (should fail)
echo -n "  Testing without auth token... "
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health 2>/dev/null)
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓ Health endpoint works${NC}"
else
    echo -e "${RED}✗ Health endpoint failed (code: $response)${NC}"
fi

echo ""
echo "=================================="
echo ""

# Test Content Checker Backend
echo "📝 Testing Content Checker Backend (http://localhost:8001)"
echo ""

# Test without auth (should fail)
echo -n "  Testing without auth token... "
response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/health 2>/dev/null)
if [ "$response" = "200" ]; then
    echo -e "${GREEN}✓ Health endpoint works${NC}"
else
    echo -e "${RED}✗ Health endpoint failed (code: $response)${NC}"
fi

echo ""
echo "=================================="
echo ""
echo -e "${YELLOW}Note: To test authenticated endpoints, you'll need to:${NC}"
echo "  1. Sign in to the Next.js frontend"
echo "  2. Use the browser dev tools to get your JWT token"
echo "  3. Test with: curl -H 'Authorization: Bearer <token>' http://localhost:8000/..."
echo ""
echo "Or continue with frontend implementation to test through the UI!"
