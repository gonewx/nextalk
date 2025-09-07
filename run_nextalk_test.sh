#!/bin/bash

echo "=== Starting NexTalk Test ==="
echo "1. Starting NexTalk in background..."

# Start NexTalk and capture output
timeout 10s python nextalk_cli.py > test_output.log 2>&1 &
NEXTALK_PID=$!

echo "2. NexTalk started with PID: $NEXTALK_PID"
echo "3. Waiting 3 seconds for initialization..."
sleep 3

echo "4. Checking if NexTalk is running..."
if ps -p $NEXTALK_PID > /dev/null; then
    echo "✅ NexTalk is running"
    
    echo "5. Please test audio recognition by pressing Ctrl+Alt+Space and speaking"
    echo "   Say: '今天天气真好' (jīntiān tiānqì zhēn hǎo)"
    echo "6. Check the log output:"
    echo "----------------------------------------"
    tail -f test_output.log &
    TAIL_PID=$!
    
    # Wait for user to test
    sleep 10
    
    echo "----------------------------------------"
    echo "7. Stopping background processes..."
    kill $TAIL_PID 2>/dev/null
    kill $NEXTALK_PID 2>/dev/null
    
    echo "8. Final log output:"
    cat test_output.log | grep -E "(Recognition result|Received message|init message|audio chunks)"
    
else
    echo "❌ NexTalk failed to start"
    echo "Error output:"
    cat test_output.log
fi

echo "=== Test Complete ==="