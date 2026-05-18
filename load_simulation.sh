#!/bin/bash

echo "Load Simulation"

echo "Sending repeated API requests"
for i in $(seq 1 50); do
    curl -s -X POST http://localhost:3003/orders \
        -H "Content-Type: application/json" \
        -d '{"user_id": 1, "product_id": 1, "quantity": 2}' > /dev/null
done

echo "Sending concurrent requests"
for i in $(seq 1 100); do
    curl -s http://localhost:3003/orders > /dev/null &
done
wait

echo "Starting CPU stress test for 30 seconds"

echo "Using bash CPU stress"
END=$((SECONDS + 30))
while [ $SECONDS -lt $END ]; do
    echo "stress" | md5sum > /dev/null
done