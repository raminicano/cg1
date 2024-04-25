#!/bin/bash

cd app
echo "Starting FastAPI server..."
uvicorn main:app --host 0.0.0.0 --port 3000 --reload &
sleep 2s

echo "Starting JSON server..."
json-server --watch ../../json-server/data.json --host 0.0.0.0 --port 5000 &

wait

