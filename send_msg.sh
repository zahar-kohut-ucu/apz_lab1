#!/bin/bash
BASE_URL="http://localhost:8001"

echo "Sending messages..."
for i in {1..10}; do
    MESSAGE="msg$i"
    RESPONSE=$(curl -s -X 'POST' "$BASE_URL/send" \
        -H 'Content-Type: application/json' \
        -d "{\"msg\": \"$MESSAGE\"}")
    echo "Message $i sent: $RESPONSE"
done

