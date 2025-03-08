BASE_URL="http://localhost:8001"

echo "Requesting messages..."
LOGGED_MESSAGES=$(curl -s "$BASE_URL/messages")
echo "Logged messages: $LOGGED_MESSAGES"