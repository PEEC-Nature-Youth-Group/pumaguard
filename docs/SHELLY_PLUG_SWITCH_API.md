# Shelly Plug Switch Control API

This document describes the API endpoint for controlling Shelly plug switches on/off using the Shelly Gen2 Switch.Set API.

## Endpoint

```
PUT /api/dhcp/plugs/<mac_address>/switch
```

## Description

Turn a Shelly plug switch on or off remotely. This endpoint calls the Shelly Gen2 `Switch.Set` API to control the physical relay state of the plug.

## Parameters

### URL Parameters

- `mac_address` (string, required): The MAC address of the plug in format `aa:bb:cc:dd:ee:ff`

### Request Body (JSON)

```json
{
  "on": true
}
```

- `on` (boolean, required): Set to `true` to turn the switch ON, `false` to turn it OFF

## Response

### Success Response (200 OK)

```json
{
  "status": "success",
  "message": "Plug switch set to ON",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "hostname": "shellyplugus-example",
  "on": true,
  "was_on": false
}
```

**Response Fields:**
- `status`: Operation status ("success")
- `message`: Human-readable message
- `mac_address`: MAC address of the plug
- `hostname`: Hostname of the plug
- `on`: Current switch state after the operation
- `was_on`: Switch state before the operation

### Error Responses

#### 400 Bad Request
```json
{
  "error": "No JSON data provided"
}
```
or
```json
{
  "error": "Missing 'on' parameter"
}
```
or
```json
{
  "error": "'on' parameter must be a boolean"
}
```
or
```json
{
  "error": "Plug IP address not available",
  "mac_address": "aa:bb:cc:dd:ee:ff"
}
```

#### 404 Not Found
```json
{
  "error": "Plug not found",
  "mac_address": "aa:bb:cc:dd:ee:ff"
}
```

#### 503 Service Unavailable
```json
{
  "error": "Plug is not connected",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "status": "disconnected"
}
```

#### 504 Gateway Timeout
```json
{
  "error": "Timeout connecting to plug",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "ip_address": "192.168.1.100"
}
```

#### 500 Internal Server Error
```json
{
  "error": "Failed to set Shelly switch",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "ip_address": "192.168.1.100",
  "details": "Connection refused"
}
```

## Examples

### Example 1: Turn switch ON

**Request:**
```bash
curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/switch \
  -H "Content-Type: application/json" \
  -d '{"on": true}'
```

**Response:**
```json
{
  "status": "success",
  "message": "Plug switch set to ON",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "hostname": "shellyplugus-livingroom",
  "on": true,
  "was_on": false
}
```

### Example 2: Turn switch OFF

**Request:**
```bash
curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/switch \
  -H "Content-Type: application/json" \
  -d '{"on": false}'
```

**Response:**
```json
{
  "status": "success",
  "message": "Plug switch set to OFF",
  "mac_address": "aa:bb:cc:dd:ee:ff",
  "hostname": "shellyplugus-livingroom",
  "on": false,
  "was_on": true
}
```

### Example 3: Python Example

```python
import requests
import json

# Configuration
PUMAGUARD_HOST = "http://localhost:5000"
PLUG_MAC_ADDRESS = "aa:bb:cc:dd:ee:ff"

def set_plug_switch(mac_address: str, on: bool) -> dict:
    """
    Control a Shelly plug switch.
    
    Args:
        mac_address: MAC address of the plug
        on: True to turn on, False to turn off
    
    Returns:
        Response data from the API
    """
    url = f"{PUMAGUARD_HOST}/api/dhcp/plugs/{mac_address}/switch"
    payload = {"on": on}
    
    response = requests.put(url, json=payload)
    response.raise_for_status()
    
    return response.json()

# Turn the plug ON
result = set_plug_switch(PLUG_MAC_ADDRESS, True)
print(f"Switch is now: {'ON' if result['on'] else 'OFF'}")
print(f"Was previously: {'ON' if result['was_on'] else 'OFF'}")

# Turn the plug OFF
result = set_plug_switch(PLUG_MAC_ADDRESS, False)
print(f"Switch is now: {'ON' if result['on'] else 'OFF'}")
```

### Example 4: JavaScript/TypeScript Example

```javascript
const PUMAGUARD_HOST = 'http://localhost:5000';
const PLUG_MAC_ADDRESS = 'aa:bb:cc:dd:ee:ff';

async function setPlugSwitch(macAddress, on) {
  const url = `${PUMAGUARD_HOST}/api/dhcp/plugs/${macAddress}/switch`;
  
  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ on }),
  });
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  return await response.json();
}

// Turn the plug ON
setPlugSwitch(PLUG_MAC_ADDRESS, true)
  .then(result => {
    console.log(`Switch is now: ${result.on ? 'ON' : 'OFF'}`);
    console.log(`Was previously: ${result.was_on ? 'ON' : 'OFF'}`);
  })
  .catch(error => console.error('Error:', error));

// Turn the plug OFF
setPlugSwitch(PLUG_MAC_ADDRESS, false)
  .then(result => {
    console.log(`Switch is now: ${result.on ? 'ON' : 'OFF'}`);
  })
  .catch(error => console.error('Error:', error));
```

## Server-Sent Events (SSE)

When a plug switch state changes, an event is broadcast to all connected SSE clients at the `/api/dhcp/cameras/events` endpoint:

```json
{
  "type": "plug_switch_changed",
  "data": {
    "hostname": "shellyplugus-livingroom",
    "ip_address": "192.168.1.100",
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "last_seen": "2024-01-15T10:30:00Z",
    "status": "connected",
    "mode": "on",
    "switch_state": true,
    "was_on": false
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Prerequisites

1. The plug must be registered in PumaGuard (either via DHCP auto-detection or manual addition)
2. The plug must have status "connected"
3. The plug must have a valid IP address
4. The plug must be accessible on the network

## Related Endpoints

- `GET /api/dhcp/plugs` - List all plugs
- `GET /api/dhcp/plugs/<mac_address>` - Get specific plug info
- `GET /api/dhcp/plugs/<mac_address>/shelly-status` - Get real-time status from Shelly API
- `PUT /api/dhcp/plugs/<mac_address>/mode` - Set plug mode (on/off/automatic)
- `GET /api/dhcp/plugs/<mac_address>/mode` - Get current plug mode

## Shelly API Reference

This endpoint uses the Shelly Gen2 Switch.Set API. For more details, see:
https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch#switchset

### Underlying Shelly API Call

```
GET http://<plug_ip>/rpc/Switch.Set?id=0&on=true
```

**Parameters:**
- `id`: Switch component ID (always 0 for single-switch plugs)
- `on`: Boolean value (true/false)

**Response:**
```json
{
  "was_on": false
}
```

## Notes

- The switch state change is immediate
- The `was_on` field in the response indicates the previous state
- Network latency may cause a slight delay
- If the plug is unreachable, a timeout error will be returned after 5 seconds
- The plug mode setting (from `/mode` endpoint) is automatically enforced when changed to "on" or "off"
  - Setting mode to "on" immediately turns the plug on
  - Setting mode to "off" immediately turns the plug off
  - Setting mode to "automatic" does not change the current switch state
- This direct switch control allows manual override of the plug state