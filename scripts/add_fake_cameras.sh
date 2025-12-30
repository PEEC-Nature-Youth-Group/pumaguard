#!/bin/bash
# Script to add fake cameras for UI testing
# This sends POST requests to the PumaGuard API to simulate camera detection

# PumaGuard API endpoint
API_URL="${PUMAGUARD_API:-http://localhost:5000/api/dhcp/cameras}"

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to add a camera
add_camera() {
    local hostname="$1"
    local ip="$2"
    local mac="$3"
    local status="${4:-connected}"

    echo -e "${YELLOW}Adding camera: $hostname ($ip)...${NC}"

    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "{\"hostname\":\"$hostname\",\"ip_address\":\"$ip\",\"mac_address\":\"$mac\",\"status\":\"$status\"}" \
        "$API_URL")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" -eq 201 ]; then
        echo -e "${GREEN}✓ Successfully added camera: $hostname${NC}"
        echo "  Response: $body"
    else
        echo -e "${RED}✗ Failed to add camera: $hostname (HTTP $http_code)${NC}"
        echo "  Response: $body"
    fi
    echo ""
}

# Function to clear all cameras
clear_cameras() {
    echo -e "${YELLOW}Clearing all cameras...${NC}"

    response=$(curl -s -w "\n%{http_code}" -X DELETE "$API_URL")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✓ Successfully cleared all cameras${NC}"
        echo "  Response: $body"
    else
        echo -e "${RED}✗ Failed to clear cameras (HTTP $http_code)${NC}"
        echo "  Response: $body"
    fi
    echo ""
}

# Function to list cameras
list_cameras() {
    echo -e "${YELLOW}Listing cameras...${NC}"

    response=$(curl -s "$API_URL")

    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo ""
}

# Main script
echo "============================================"
echo "PumaGuard Fake Camera Management Script"
echo "============================================"
echo "API URL: $API_URL"
echo ""

# Parse command line arguments
case "$1" in
    clear)
        clear_cameras
        ;;
    list)
        list_cameras
        ;;
    add)
        if [ $# -lt 4 ]; then
            echo "Usage: $0 add <hostname> <ip> <mac> [status]"
            exit 1
        fi
        add_camera "$2" "$3" "$4" "${5:-connected}"
        ;;
    *)
        # Default: Add 3 fake cameras
        echo "Adding 3 fake cameras for testing..."
        echo ""

        add_camera "Microseven-Cam1" "192.168.52.101" "aa:bb:cc:dd:ee:01" "connected"
        add_camera "Microseven-Cam2" "192.168.52.102" "aa:bb:cc:dd:ee:02" "connected"
        add_camera "Microseven-Cam3" "192.168.52.103" "aa:bb:cc:dd:ee:03" "disconnected"

        echo "============================================"
        echo -e "${GREEN}Done! Check the PumaGuard UI to see the cameras.${NC}"
        echo ""
        echo "Commands:"
        echo "  $0          - Add 3 fake cameras (default)"
        echo "  $0 list     - List all cameras"
        echo "  $0 clear    - Clear all cameras"
        echo "  $0 add <hostname> <ip> <mac> [status]"
        echo ""
        echo "Example:"
        echo "  $0 add TestCamera 192.168.52.200 aa:bb:cc:dd:ee:ff connected"
        ;;
esac
