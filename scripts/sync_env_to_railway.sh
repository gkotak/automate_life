#!/bin/bash
#
# Sync environment variables from .env.production to Railway via GraphQL API
# Uses variableCollectionUpsert for batch updates (avoids rate limits)
#
# Usage:
#   ./scripts/sync_env_to_railway.sh [project_id] [environment_id] [service_id]
#
# Arguments:
#   project_id     - Railway project ID (optional, will auto-detect if not provided)
#   environment_id - Railway environment ID (optional, defaults to production)
#   service_id     - Railway service ID (optional, creates shared variables if omitted)
#
# Prerequisites:
#   - curl and python3 commands available
#   - .env.production file with RAILWAY_TOKEN set
#   - RAILWAY_PROJECT_ID and RAILWAY_ENVIRONMENT_ID in .env.production (or passed as args)

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
ENV_FILE="$PROJECT_ROOT/programs/article_summarizer_backend/.env.production"
RAILWAY_API_URL="https://backboard.railway.com/graphql/v2"

# Functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Check if .env.production exists
if [ ! -f "$ENV_FILE" ]; then
    log_error "Backend .env.production not found!"
    log_info "Expected location: programs/article_summarizer_backend/.env.production"
    log_info "Create it by copying the example:"
    echo "  cp programs/article_summarizer_backend/.env.production.example \\"
    echo "     programs/article_summarizer_backend/.env.production"
    echo "  # Then fill in your production values"
    exit 1
fi

# Load environment variables
log_info "Loading environment variables from .env.production..."
set -a  # Automatically export all variables
source "$ENV_FILE"
set +a

# Check if Railway token is set
if [ -z "$RAILWAY_TOKEN" ]; then
    log_error "RAILWAY_TOKEN not set in .env.production"
    log_info "Get your token from: https://railway.app/account/tokens"
    log_info "Then add it to .env.production"
    exit 1
fi

# Get IDs from arguments or environment
PROJECT_ID="${1:-$RAILWAY_PROJECT_ID}"
ENVIRONMENT_ID="${2:-$RAILWAY_ENVIRONMENT_ID}"
SERVICE_ID="${3:-$RAILWAY_SERVICE_ID}"

# If PROJECT_ID not provided, exit
if [ -z "$PROJECT_ID" ]; then
    log_error "RAILWAY_PROJECT_ID not set"
    log_info "Add it to .env.production or pass as first argument"
    log_info "Find it in Railway dashboard URL: railway.app/project/{PROJECT_ID}"
    exit 1
fi

# If ENVIRONMENT_ID not provided, exit
if [ -z "$ENVIRONMENT_ID" ]; then
    log_error "RAILWAY_ENVIRONMENT_ID not set"
    log_info "Add it to .env.production or pass as second argument"
    log_info "Find it in Railway dashboard or query via API"
    exit 1
fi

log_info "Syncing to Railway (Article Summarizer Backend)..."
log_info "Project ID: $PROJECT_ID"
log_info "Environment ID: $ENVIRONMENT_ID"
if [ -n "$SERVICE_ID" ]; then
    log_info "Service ID: $SERVICE_ID (service-specific variables)"
else
    log_info "No Service ID (creating shared variables)"
fi
log_warning "This will update ALL environment variables in Railway"
echo ""
read -p "Continue? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_info "Cancelled"
    exit 0
fi

# Create a Python script with the mutation
echo ""
log_info "Building variable collection and syncing..."

# Create temporary Python script
cat > /tmp/railway_sync_article.py << 'PYTHON'
import os
import json
import sys
import subprocess

# Build variables dictionary
variables = {}

def add_var(key, value):
    if value and value.strip():
        variables[key] = value
        print(f"\033[0;34mℹ️    ✓ {key}\033[0m")

# Add all backend environment variables
add_var("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
add_var("SUPABASE_SECRET_KEY", os.getenv("SUPABASE_SECRET_KEY", ""))
add_var("ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))
add_var("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
add_var("DEEPGRAM_API_KEY", os.getenv("DEEPGRAM_API_KEY", ""))
add_var("BRAINTRUST_API_KEY", os.getenv("BRAINTRUST_API_KEY", ""))
add_var("API_KEY", os.getenv("API_KEY", ""))
add_var("PLAYWRIGHT_HEADLESS", os.getenv("PLAYWRIGHT_HEADLESS", ""))
add_var("PLAYWRIGHT_TIMEOUT", os.getenv("PLAYWRIGHT_TIMEOUT", ""))
add_var("PLAYWRIGHT_SCREENSHOT_ON_ERROR", os.getenv("PLAYWRIGHT_SCREENSHOT_ON_ERROR", ""))
add_var("ENVIRONMENT", os.getenv("ENVIRONMENT", ""))
add_var("LOG_LEVEL", os.getenv("LOG_LEVEL", ""))
add_var("CORS_ORIGINS", os.getenv("CORS_ORIGINS", ""))
add_var("BROWSER_FETCH_DOMAINS", os.getenv("BROWSER_FETCH_DOMAINS", ""))

# Optional variables
add_var("SUBSTACK_EMAIL", os.getenv("SUBSTACK_EMAIL", ""))
add_var("SUBSTACK_PASSWORD", os.getenv("SUBSTACK_PASSWORD", ""))
add_var("POCKETCASTS_EMAIL", os.getenv("POCKETCASTS_EMAIL", ""))
add_var("POCKETCASTS_PASSWORD", os.getenv("POCKETCASTS_PASSWORD", ""))
add_var("SERPAPI_KEY", os.getenv("SERPAPI_KEY", ""))
add_var("SEARCH_PODCAST_URLS", os.getenv("SEARCH_PODCAST_URLS", ""))
add_var("SERPAPI_PODCAST_WHITELIST", os.getenv("SERPAPI_PODCAST_WHITELIST", ""))

if not variables:
    print("\033[0;31m❌ No variables to sync\033[0m")
    sys.exit(1)

# Build GraphQL mutation using variables (proper way)
mutation = {
    "query": """
    mutation VariableCollectionUpsert($input: VariableCollectionUpsertInput!) {
      variableCollectionUpsert(input: $input)
    }
    """,
    "variables": {
        "input": {
            "projectId": os.getenv("SYNC_PROJECT_ID"),
            "environmentId": os.getenv("SYNC_ENVIRONMENT_ID"),
            "serviceId": os.getenv("SYNC_SERVICE_ID"),
            "skipDeploys": False,
            "replace": True,
            "variables": variables
        }
    }
}

# Remove serviceId if empty
if not mutation["variables"]["input"]["serviceId"]:
    del mutation["variables"]["input"]["serviceId"]

print(f"\033[0;34m\nℹ️  Syncing {len(variables)} variables to Railway (batch update)...\033[0m")

# Write mutation to temp file
with open("/tmp/mutation_article.json", "w") as f:
    json.dump(mutation, f)

# Use curl to send the request (more reliable than urllib)
curl_cmd = [
    "curl", "-s", "-X", "POST",
    os.getenv("SYNC_API_URL"),
    "-H", f"Authorization: Bearer {os.getenv('SYNC_RAILWAY_TOKEN')}",
    "-H", "Content-Type: application/json",
    "-d", f"@/tmp/mutation_article.json"
]

try:
    result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
    response = json.loads(result.stdout)

    if "errors" in response:
        print(f"\n\033[0;31m❌ Failed to sync variables\033[0m")
        print("\033[0;31mErrors from Railway API:\033[0m")
        for error in response["errors"]:
            print(f"  • {error.get('message', 'Unknown error')}")
            if "extensions" in error:
                print(f"    Details: {json.dumps(error['extensions'], indent=2)}")
        sys.exit(1)
    else:
        print(f"\n\033[0;32m✅ All environment variables synced to Railway!\033[0m")
        print(f"\033[0;34mℹ️  View at: https://railway.app/project/{os.getenv('SYNC_PROJECT_ID')}\033[0m")
        print(f"\033[0;34mℹ️  Railway will deploy once with all new variables\033[0m")
except subprocess.CalledProcessError as e:
    print(f"\033[0;31m❌ Curl command failed: {e}\033[0m")
    print(f"Output: {e.stdout}")
    print(f"Error: {e.stderr}")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"\033[0;31m❌ Invalid JSON response from Railway\033[0m")
    print(f"Response: {result.stdout}")
    sys.exit(1)
except Exception as e:
    print(f"\033[0;31m❌ Error: {e}\033[0m")
    sys.exit(1)
PYTHON

# Export all variables with SYNC_ prefix to avoid conflicts
export SYNC_PROJECT_ID="$PROJECT_ID"
export SYNC_ENVIRONMENT_ID="$ENVIRONMENT_ID"
export SYNC_SERVICE_ID="$SERVICE_ID"
export SYNC_RAILWAY_TOKEN="$RAILWAY_TOKEN"
export SYNC_API_URL="$RAILWAY_API_URL"

# Run the Python script with all environment variables
python3 /tmp/railway_sync_article.py

# Cleanup
rm -f /tmp/railway_sync_article.py /tmp/mutation_article.json
