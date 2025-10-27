#!/bin/bash
#
# Sync environment variables from .env.production to Vercel via REST API
# Uses batch API endpoint (avoids multiple deployments)
#
# Usage:
#   ./scripts/sync_env_to_vercel.sh [project_id] [environment]
#
# Arguments:
#   project_id  - Vercel project ID (optional, will auto-detect if not provided)
#   environment - Target environment: production, preview, development (default: production)
#
# Prerequisites:
#   - curl and python3 commands available
#   - .env.production file with VERCEL_TOKEN set
#   - VERCEL_PROJECT_ID in .env.production (or passed as argument)

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/web-apps/article-summarizer/.env.production"
VERCEL_API_URL="https://api.vercel.com"

# Functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check if .env.production exists
if [ ! -f "$ENV_FILE" ]; then
    log_error "Frontend .env.production not found!"
    log_info "Expected location: web-apps/article-summarizer/.env.production"
    log_info "Create it by copying .env.local and update with production values"
    exit 1
fi

# Load environment variables
log_info "Loading environment variables from .env.production..."
set -a  # Automatically export all variables
source "$ENV_FILE"
set +a

# Check if Vercel token is set
if [ -z "$VERCEL_TOKEN" ]; then
    log_error "VERCEL_TOKEN not set in .env.production"
    log_info "Get your token from: https://vercel.com/account/tokens"
    exit 1
fi

# Parse arguments (filter out flags)
SKIP_CONFIRM=false
POSITIONAL_ARGS=()
for arg in "$@"; do
    if [ "$arg" == "--yes" ] || [ "$arg" == "-y" ]; then
        SKIP_CONFIRM=true
    else
        POSITIONAL_ARGS+=("$arg")
    fi
done

# Get project ID and environment from positional arguments or environment
PROJECT_ID="${POSITIONAL_ARGS[0]:-$VERCEL_PROJECT_ID}"
TARGET_ENV="${POSITIONAL_ARGS[1]:-production}"

# If PROJECT_ID not provided, exit
if [ -z "$PROJECT_ID" ]; then
    log_error "VERCEL_PROJECT_ID not set"
    log_info "Add it to .env.production or pass as first argument"
    log_info "Find it in .vercel/project.json or Vercel dashboard"
    exit 1
fi

log_info "Syncing to Vercel..."
log_info "Project ID: $PROJECT_ID"
log_info "Target Environment: $TARGET_ENV"
if [ -n "$VERCEL_TEAM_ID" ]; then
    log_info "Team ID: $VERCEL_TEAM_ID"
fi

if [ "$SKIP_CONFIRM" == false ]; then
    log_warning "This will update ALL environment variables in Vercel $TARGET_ENV"
    echo ""
    read -p "Continue? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Cancelled"
        exit 0
    fi
fi

# Create a Python script to build and send the request
echo ""
log_info "Building variable collection and syncing..."

# Create temporary Python script
cat > /tmp/vercel_sync.py << 'PYTHON'
import os
import json
import sys
import subprocess

# Build environment variables array for Vercel API
variables = []

def add_var(key, value, env_target):
    if value and value.strip():
        variables.append({
            "key": key,
            "value": value,
            "type": "encrypted" if "KEY" in key or "SECRET" in key or "TOKEN" in key or "PASSWORD" in key else "plain",
            "target": [env_target]
        })
        print(f"\033[0;34mℹ️    ✓ {key}\033[0m")

# Get target environment
target_env = os.getenv("SYNC_TARGET_ENV", "production")

# Add all frontend environment variables
add_var("NEXT_PUBLIC_SUPABASE_URL", os.getenv("NEXT_PUBLIC_SUPABASE_URL", ""), target_env)
add_var("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", ""), target_env)
add_var("NEXT_PUBLIC_API_URL", os.getenv("NEXT_PUBLIC_API_URL", ""), target_env)
add_var("NEXT_PUBLIC_API_KEY", os.getenv("NEXT_PUBLIC_API_KEY", ""), target_env)
add_var("NEXT_PUBLIC_CONTENT_CHECKER_API_URL", os.getenv("NEXT_PUBLIC_CONTENT_CHECKER_API_URL", ""), target_env)
add_var("NEXT_PUBLIC_CONTENT_CHECKER_API_KEY", os.getenv("NEXT_PUBLIC_CONTENT_CHECKER_API_KEY", ""), target_env)
add_var("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""), target_env)
add_var("BRAINTRUST_API_KEY", os.getenv("BRAINTRUST_API_KEY", ""), target_env)

if not variables:
    print("\033[0;31m❌ No variables to sync\033[0m")
    sys.exit(1)

print(f"\033[0;34m\nℹ️  Syncing {len(variables)} variables to Vercel (batch update)...\033[0m")

# Write variables to temp file
with open("/tmp/vercel_vars.json", "w") as f:
    json.dump(variables, f)

# Build URL with query parameters
project_id = os.getenv("SYNC_PROJECT_ID")
team_id = os.getenv("SYNC_TEAM_ID")
api_url = f"{os.getenv('SYNC_API_URL')}/v10/projects/{project_id}/env?upsert=true"
if team_id:
    api_url += f"&teamId={team_id}"

# Use curl to send the request
curl_cmd = [
    "curl", "-s", "-X", "POST",
    api_url,
    "-H", f"Authorization: Bearer {os.getenv('SYNC_VERCEL_TOKEN')}",
    "-H", "Content-Type: application/json",
    "-d", "@/tmp/vercel_vars.json"
]

try:
    result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
    response = json.loads(result.stdout)

    if "error" in response:
        print(f"\n\033[0;31m❌ Failed to sync variables\033[0m")
        print(f"  Error: {response['error'].get('message', 'Unknown error')}")
        if "code" in response["error"]:
            print(f"  Code: {response['error']['code']}")
        sys.exit(1)
    elif "failed" in response and response["failed"]:
        print(f"\n\033[0;33m⚠️  Some variables failed to sync\033[0m")
        for failure in response["failed"]:
            print(f"  • {failure.get('key', 'unknown')}: {failure.get('error', {}).get('message', 'Unknown error')}")
        if response.get("created"):
            print(f"\n\033[0;32m✅ {len(response['created'])} variables synced successfully\033[0m")
        sys.exit(1)
    else:
        created_count = len(response.get("created", []))
        print(f"\n\033[0;32m✅ All {created_count} environment variables synced to Vercel!\033[0m")
        print(f"\033[0;34mℹ️  View at: https://vercel.com/dashboard\033[0m")
        print(f"\033[0;34mℹ️  Redeploy your project for changes to take effect\033[0m")
except subprocess.CalledProcessError as e:
    print(f"\033[0;31m❌ Curl command failed: {e}\033[0m")
    print(f"Output: {e.stdout}")
    print(f"Error: {e.stderr}")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"\033[0;31m❌ Invalid JSON response from Vercel\033[0m")
    print(f"Response: {result.stdout}")
    sys.exit(1)
except Exception as e:
    print(f"\033[0;31m❌ Error: {e}\033[0m")
    sys.exit(1)
PYTHON

# Export all variables with SYNC_ prefix to avoid conflicts
export SYNC_PROJECT_ID="$PROJECT_ID"
export SYNC_TEAM_ID="$VERCEL_TEAM_ID"
export SYNC_TARGET_ENV="$TARGET_ENV"
export SYNC_VERCEL_TOKEN="$VERCEL_TOKEN"
export SYNC_API_URL="$VERCEL_API_URL"

# Run the Python script with all environment variables
python3 /tmp/vercel_sync.py

# Cleanup
rm -f /tmp/vercel_sync.py /tmp/vercel_vars.json
