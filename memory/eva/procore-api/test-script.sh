#!/bin/bash

# Procore API Testing Script
# Run after OAuth token is refreshed
# Usage: ./test-script.sh [access_token]

set -e

# Configuration
COMPANY_ID="4281379"
PROJECT_ID="316469"
BASE_URL="https://api.procore.com/rest/v1.0"
DELAY="0.5"  # Rate limiting delay

# Get token from parameter or file
if [ -n "$1" ]; then
    ACCESS_TOKEN="$1"
else
    ACCESS_TOKEN=$(jq -r '.access_token' /home/moby/.openclaw/workspace/.credentials/procore_token.json)
fi

# Create results directory
RESULTS_DIR="/home/moby/.openclaw/workspace/memory/eva/procore-api/test-results"
mkdir -p "$RESULTS_DIR"

echo "🚀 Starting Procore API Discovery - $(date)"
echo "📁 Results will be saved to: $RESULTS_DIR"

# Helper function for API calls
api_call() {
    local method="$1"
    local endpoint="$2" 
    local data="$3"
    local output_file="$4"
    
    echo "📡 Testing: $method $endpoint"
    
    if [ "$method" = "GET" ]; then
        curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
             "$BASE_URL$endpoint" \
             | jq '.' > "$RESULTS_DIR/$output_file" 2>/dev/null
    elif [ "$method" = "POST" ]; then
        curl -s -X POST \
             -H "Authorization: Bearer $ACCESS_TOKEN" \
             -H "Content-Type: application/json" \
             -d "$data" \
             "$BASE_URL$endpoint" \
             | jq '.' > "$RESULTS_DIR/$output_file" 2>/dev/null
    fi
    
    sleep $DELAY
    
    if [ -s "$RESULTS_DIR/$output_file" ]; then
        echo "✅ Success: saved to $output_file"
    else
        echo "❌ Failed: $endpoint"
    fi
}

echo ""
echo "🏗️ PHASE 1: DAILY LOGS DISCOVERY"
echo "================================"

# Daily Logs - List
api_call "GET" "/projects/$PROJECT_ID/daily_logs" "" "daily-logs-list.json"

# Daily Logs - Pagination test  
api_call "GET" "/projects/$PROJECT_ID/daily_logs?per_page=10&page=1" "" "daily-logs-paginated.json"

# Daily Logs - Filters
api_call "GET" "/projects/$PROJECT_ID/daily_logs?filters[created_at]=2026-02-01,2026-02-28" "" "daily-logs-filtered.json"

# Daily Logs - Create test (minimal)
DAILY_LOG_DATA='{
  "daily_log": {
    "date": "2026-02-19",
    "weather": "Testing - Sunny, 65°F",
    "work_performed": "API testing - minimal daily log creation"
  }
}'
api_call "POST" "/projects/$PROJECT_ID/daily_logs" "$DAILY_LOG_DATA" "daily-log-create-response.json"

echo ""
echo "🔔 PHASE 2: WEBHOOKS DISCOVERY" 
echo "============================="

# Webhooks - Company level
api_call "GET" "/companies/$COMPANY_ID/webhooks" "" "webhooks-company-list.json"

# Webhooks - Project level (might not exist)
api_call "GET" "/projects/$PROJECT_ID/webhooks" "" "webhooks-project-list.json"

# Webhook creation test
WEBHOOK_DATA='{
  "webhook": {
    "destination_url": "https://eva.ai/webhooks/test",
    "event_type": "Daily Log.Created",
    "active": true
  }
}'
api_call "POST" "/companies/$COMPANY_ID/webhooks" "$WEBHOOK_DATA" "webhook-create-response.json"

echo ""
echo "🔍 PHASE 3: INSPECTIONS DISCOVERY"
echo "================================"

# Inspections - List
api_call "GET" "/projects/$PROJECT_ID/inspections" "" "inspections-list.json"

# Inspection Templates
api_call "GET" "/projects/$PROJECT_ID/inspection_templates" "" "inspection-templates-list.json"

# Checklists (alternative naming)
api_call "GET" "/projects/$PROJECT_ID/checklists" "" "checklists-list.json"

# Quality Safety Observations  
api_call "GET" "/projects/$PROJECT_ID/observations" "" "observations-list.json"

echo ""
echo "🚧 PHASE 4: ADDITIONAL PRIORITY ENDPOINTS"
echo "========================================"

# Punch Lists
api_call "GET" "/projects/$PROJECT_ID/punch_list_items" "" "punch-lists.json"

# Budget & Cost Codes
api_call "GET" "/projects/$PROJECT_ID/budget_line_items" "" "budget-line-items.json"
api_call "GET" "/projects/$PROJECT_ID/cost_codes" "" "cost-codes.json"

# Change Orders
api_call "GET" "/projects/$PROJECT_ID/change_orders" "" "change-orders.json"
api_call "GET" "/projects/$PROJECT_ID/potential_change_orders" "" "potential-change-orders.json"

# Schedules & Tasks
api_call "GET" "/projects/$PROJECT_ID/schedules" "" "schedules.json"  
api_call "GET" "/projects/$PROJECT_ID/tasks" "" "tasks.json"

# Meetings
api_call "GET" "/projects/$PROJECT_ID/meetings" "" "meetings.json"

# Photos
api_call "GET" "/projects/$PROJECT_ID/photos" "" "photos.json"

# Timesheets
api_call "GET" "/projects/$PROJECT_ID/time_entries" "" "time-entries.json"

# Custom Fields
api_call "GET" "/projects/$PROJECT_ID/custom_fields" "" "custom-fields.json"

echo ""
echo "📊 PHASE 5: ENDPOINT PATTERN DISCOVERY"  
echo "====================================="

# Try common endpoint patterns that might exist
PATTERNS=(
    "daily_reports"
    "reports/daily"  
    "safety_observations"
    "quality_observations"
    "inspection_items"
    "inspection_checklists"
    "notification_templates"
    "event_types"
    "project_templates"
    "workflow_templates"
    "approval_workflows"
)

for pattern in "${PATTERNS[@]}"; do
    api_call "GET" "/projects/$PROJECT_ID/$pattern" "" "pattern-$pattern.json"
done

echo ""
echo "📈 RESULTS SUMMARY"
echo "=================="

echo "📁 Test results saved to: $RESULTS_DIR"
echo "📊 Files created:"
find "$RESULTS_DIR" -name "*.json" -type f | wc -l

echo ""
echo "🔍 Quick Analysis:"
echo "Files with data (>100 bytes):"
find "$RESULTS_DIR" -name "*.json" -size +100c -exec basename {} \;

echo ""
echo "Files with errors:"
grep -l "error\|Error\|ERROR" "$RESULTS_DIR"/*.json 2>/dev/null | xargs basename -s .json 2>/dev/null || echo "None found"

echo ""
echo "✅ API Discovery Complete!"
echo ""
echo "📋 NEXT STEPS:"
echo "1. Review all JSON files in $RESULTS_DIR"
echo "2. Document working endpoints and response structures"  
echo "3. Test CRUD operations on discovered endpoints"
echo "4. Update KNOWLEDGE.md with findings"
echo "5. Create detailed endpoint documentation"