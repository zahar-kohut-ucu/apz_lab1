#!/bin/bash

BASE_URL="http://localhost:8001"
RETRY1_URL="http://localhost:8004"
RETRY2_URL="http://localhost:8005"

echo "Sending messages..."
MESSAGE_1="Hello from message 1!"
RESPONSE_1=$(curl -s -X 'POST' "$BASE_URL/send" \
    -H 'Content-Type: application/json' \
    -d "{\"msg\": \"$MESSAGE_1\"}")
echo "Message 1 sent: $RESPONSE_1"

MESSAGE_2="Hello from message 2!"
RESPONSE_2=$(curl -s -X 'POST' "$BASE_URL/send" \
    -H 'Content-Type: application/json' \
    -d "{\"msg\": \"$MESSAGE_2\"}")
echo "Message 2 sent: $RESPONSE_2"

echo "Requesting messages..."
LOGGED_MESSAGES=$(curl -s "$BASE_URL/messages")
echo "Logged messages: $LOGGED_MESSAGES"

echo "Testing duplicate ID case..."
MESSAGE_3="Double id test first!"
RESPONSE_3=$(curl -s -X 'POST' "$RETRY1_URL/send" \
    -H 'Content-Type: application/json' \
    -d "{\"msg\": \"$MESSAGE_3\"}")
echo "Message 3 sent: $RESPONSE_3"

MESSAGE_4="Double id test second!"
RESPONSE_4=$(curl -s -X 'POST' "$RETRY1_URL/send" \
    -H 'Content-Type: application/json' \
    -d "{\"msg\": \"$MESSAGE_4\"}")
echo "Message 4 sent: $RESPONSE_4"

echo "Testing case with logging service being unavailable..."
MESSAGE_5="Logging service being unavailable test!"
RESPONSE_5=$(curl -X 'POST' "$RETRY2_URL/send" \
    -H 'Content-Type: application/json' \
    -d "{\"msg\": \"$MESSAGE_5\"}")
echo "Message 5 sent: $RESPONSE_5"