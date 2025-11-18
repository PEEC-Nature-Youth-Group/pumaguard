#!/bin/bash

set -e -u

declare -i SERVER_PID

cleanup() {
    if kill -TERM ${SERVER_PID} 2> /dev/null; then
        sleep 2
        kill -KILL ${SERVER_PID} 2> /dev/null || true
    fi
    rm -rf watchfolder
}

trap cleanup EXIT

rm -rf watchfolder
mkdir -p watchfolder
rm -f pumaguard.log

uv run pumaguard server --no-play-sound --no-download-progress watchfolder &

SERVER_PID=$!
server_started=0
echo -n "Waiting for server to start"
while true; do
    if [[ -f pumaguard.log ]]; then
        server_started=1
        break
    fi
    echo -n .
    sleep 1
done
echo
if (( server_started != 1 )); then
    echo "Server failed to start"
    exit 1
fi

observer_started=0
echo -n "Waiting for server to start observer"
for i in {1..60}; do
    if grep "New observer started" pumaguard.log; then
        observer_started=1
        break
    fi
    echo -n .
    sleep 1
done
echo
if (( observer_started != 1 )); then
    echo "Server failed to start observer"
    exit 1
fi

cp training-data/verification/lion/IMG_9177.JPG watchfolder/

image_found=0
echo -n "Check whether server identifies image"
for i in {1..60}; do
    if grep "Chance of puma in watchfolder/IMG_9177.JPG" pumaguard.log; then
        image_found=1
        break
    fi
    echo -n .
    sleep 1
done
echo

if (( image_found != 1 )); then
    echo "Server did not classify image"
    exit 1
fi

exit 0
