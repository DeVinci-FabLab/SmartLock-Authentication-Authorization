#!/bin/bash

HOST="0.0.0.0"
PORT="8000"
TIMEOUT=5
URL="http://${HOST}:${PORT}/health"

echo "Performing health check on ${URL}..."

if command -v curl &> /dev/null; then
    if curl --output /dev/null --silent --fail --max-time $TIMEOUT $URL; then
        echo "Health check passed: Service is up!"
        exit 0
    else
        echo "Health check failed: Service is down!"
        exit 1
    fi
elif command -v wget &> /dev/null; then
    if wget --spider --quiet --timeout=$TIMEOUT $URL 2>/dev/null; then
        echo "Health check passed: Service is up!"
        exit 0
    else
        echo "Health check failed: Service is down!"
        exit 1
    fi
else
    echo "Health check failed: Neither curl nor wget is available!"
    exit 1
fi
