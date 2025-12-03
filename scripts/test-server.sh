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

set -x

LOGFILE=pumaguard.log

rm -rf watchfolder
mkdir -p watchfolder
rm -f ${LOGFILE}

uv run pumaguard server --debug --no-play-sound --no-download-progress --log-file ${LOGFILE} watchfolder &

SERVER_PID=$!

api_available=0
echo -n "Waiting for API to report status"
while true; do
    if [[ $(curl --silent http://localhost:5000/api/status | jq --raw-output .status) == running ]]; then
        break
    fi
    sleep 1
done
echo

observer_started=0
echo -n "Waiting for server to start observer"
for i in {1..60}; do
    if grep "New observer started" ${LOGFILE}; then
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
    if grep "Chance of puma in watchfolder/IMG_9177.JPG" ${LOGFILE}; then
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
