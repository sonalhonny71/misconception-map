#!/bin/bash
# Smoke test script - run against live API
# Usage: BASE_URL=https://your-app.onrender.com ./scripts/smoke.sh

set -e

BASE_URL="${BASE_URL:-http://localhost:8000}"
echo "🔍 Running smoke tests against $BASE_URL"

# Test health endpoint
echo "Testing /api/health..."
HEALTH=$(curl -s -f "$BASE_URL/api/health")
echo "$HEALTH" | jq '.status'
if ! echo "$HEALTH" | jq -e '.status == "ok"' > /dev/null; then
  echo "❌ Health check failed"
  exit 1
fi
echo "✅ Health check passed"

# Create learner
echo "Creating learner..."
LEARNER=$(curl -s -f -X POST "$BASE_URL/api/learners")
TOKEN=$(echo "$LEARNER" | jq -r '.token')
TOKEN_HASH=$(echo "$LEARNER" | jq -r '.token_hash')
echo "Token: ${TOKEN:0:8}..."
echo "✅ Learner created"

AUTH_HEADER="Authorization: Bearer $TOKEN"

# Get summary
echo "Getting summary..."
SUMMARY=$(curl -s -f -H "$AUTH_HEADER" "$BASE_URL/api/me/summary")
echo "$SUMMARY" | jq '.'
echo "✅ Summary retrieved"

# Get levels
echo "Getting levels..."
LEVELS=$(curl -s -f -H "$AUTH_HEADER" "$BASE_URL/api/levels")
echo "$LEVELS" | jq '.levels | length'
echo "✅ Levels retrieved"

# Start session (Level 3)
echo "Starting Level 3 session..."
SESSION=$(curl -s -f -H "$AUTH_HEADER" -X POST "$BASE_URL/api/sessions" -H "Content-Type: application/json" -d '{"level": 3}')
SESSION_ID=$(echo "$SESSION" | jq -r '.id')
echo "Session: $SESSION_ID"
echo "✅ Session started"

# Get first question
echo "Getting first question..."
QUESTION=$(curl -s -f -H "$AUTH_HEADER" "$BASE_URL/api/sessions/$SESSION_ID")
SERVED_ITEM_ID=$(echo "$QUESTION" | jq -r '.served_item_id')
PROMPT=$(echo "$QUESTION" | jq -r '.prompt')
echo "Question: $PROMPT"
echo "✅ Question retrieved"

# Answer first question (option 0 - likely correct)
OPTION_ID=$(echo "$QUESTION" | jq -r '.options[0].id')
echo "Answering with option: $OPTION_ID"
ANSWER=$(curl -s -f -H "$AUTH_HEADER" -X POST "$BASE_URL/api/sessions/$SESSION_ID/answer" \
  -H "Content-Type: application/json" \
  -d "{\"served_item_id\": \"$SERVED_ITEM_ID\", \"option_id\": \"$OPTION_ID\"}")
echo "$ANSWER" | jq '.feedback'
echo "✅ Answer submitted"

# Get insights
echo "Getting insights..."
INSIGHTS=$(curl -s -f -H "$AUTH_HEADER" "$BASE_URL/api/insights")
echo "$INSIGHTS" | jq '.'
echo "✅ Insights retrieved"

# Get progress
echo "Getting progress..."
PROGRESS=$(curl -s -f -H "$AUTH_HEADER" "$BASE_URL/api/progress")
echo "$PROGRESS" | jq '.'
echo "✅ Progress retrieved"

# Delete learner (cleanup)
echo "Deleting learner..."
curl -s -f -H "$AUTH_HEADER" -X DELETE "$BASE_URL/api/learners/me"
echo "✅ Learner deleted"

echo ""
echo "🎉 All smoke tests passed!"