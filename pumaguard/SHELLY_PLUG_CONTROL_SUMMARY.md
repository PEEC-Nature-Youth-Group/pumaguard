# Shelly Plug Control Integration - Quick Reference

## Overview

PumaGuard now supports direct control of Shelly plug switches through a REST API endpoint. This allows users to turn plugs on and off programmatically when the switch state is changed in the UI or via API calls.

## API Endpoint

**URL:** `PUT /api/dhcp/plugs/<mac_address>/switch`

**Request Body:**
```json
{
  "on": true
}
```

**Response:**
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

## Quick Examples

### Using curl

Turn ON:
```bash
curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/switch \
  -H "Content-Type: application/json" \
  -d '{"on": true}'
```

Turn OFF:
```bash
curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/switch \
  -H "Content-Type: application/json" \
  -d '{"on": false}'
```

### Using Python

```python
import requests

def control_plug(mac_address: str, turn_on: bool):
    url = f"http://localhost:5000/api/dhcp/plugs/{mac_address}/switch"
    response = requests.put(url, json={"on": turn_on})
    return response.json()

# Turn ON
control_plug("aa:bb:cc:dd:ee:ff", True)

# Turn OFF
control_plug("aa:bb:cc:dd:ee:ff", False)
```

### Using JavaScript/Fetch

```javascript
async function controlPlug(macAddress, turnOn) {
  const response = await fetch(
    `http://localhost:5000/api/dhcp/plugs/${macAddress}/switch`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ on: turnOn })
    }
  );
  return await response.json();
}

// Turn ON
await controlPlug('aa:bb:cc:dd:ee:ff', true);

// Turn OFF
await controlPlug('aa:bb:cc:dd:ee:ff', false);
```

## How It Works

1. **API Request**: Client sends PUT request with `{"on": true}` or `{"on": false}`
2. **Validation**: Server validates plug exists, is connected, and has valid IP
3. **Shelly API Call**: Server calls `http://<plug_ip>/rpc/Switch.Set?id=0&on=true`
4. **Response**: Server returns success/failure with previous and current state
5. **SSE Notification**: All connected clients receive `plug_switch_changed` event

## Underlying Shelly API

The endpoint uses the Shelly Gen2 Switch.Set API:

**Endpoint:** `GET http://<plug_ip>/rpc/Switch.Set?id=0&on={true|false}`

**Parameters:**
- `id`: Switch component ID (always 0 for single-switch plugs)
- `on`: Boolean value (true or false)

**Shelly Response:**
```json
{
  "was_on": false
}
```

**Documentation:** https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch#switchset

## Error Handling

| Status Code | Description |
|-------------|-------------|
| 200 | Success - switch state changed |
| 400 | Bad request - missing/invalid parameters |
| 404 | Plug not found |
| 503 | Plug not connected |
| 504 | Timeout connecting to plug |
| 500 | Internal server error |

## Prerequisites

- Plug must be registered in PumaGuard
- Plug status must be "connected"
- Plug must be reachable on the network
- Plug must have a valid IP address

## Integration Points

### File Modified
- `pumaguard/pumaguard/web_routes/dhcp.py` - Added `set_plug_switch()` function

### New Route
```python
@app.route("/api/dhcp/plugs/<mac_address>/switch", methods=["PUT"])
def set_plug_switch(mac_address: str):
    # Validates plug, calls Shelly API, returns result
```

### SSE Event
When switch state changes, broadcasts to `/api/dhcp/cameras/events`:
```json
{
  "type": "plug_switch_changed",
  "data": {
    "mac_address": "aa:bb:cc:dd:ee:ff",
    "hostname": "shellyplugus-example",
    "switch_state": true,
    "was_on": false
  }
}
```

## Related Endpoints

- `GET /api/dhcp/plugs` - List all plugs
- `GET /api/dhcp/plugs/<mac_address>` - Get plug info
- `GET /api/dhcp/plugs/<mac_address>/shelly-status` - Get real-time status
- `PUT /api/dhcp/plugs/<mac_address>/mode` - Set plug mode (on/off/automatic)
- `GET /api/dhcp/plugs/<mac_address>/mode` - Get plug mode

## Testing

### 1. Check Plug Status
```bash
curl http://localhost:5000/api/dhcp/plugs
```

### 2. Get Shelly Status
```bash
curl http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/shelly-status
```

### 3. Control Switch
```bash
# Turn ON
curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/switch \
  -H "Content-Type: application/json" \
  -d '{"on": true}'

# Turn OFF
curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/switch \
  -H "Content-Type: application/json" \
  -d '{"on": false}'
```

## Notes

- Switch state changes are immediate
- Default timeout is 5 seconds for Shelly API calls
- The `was_on` field indicates the previous state before the change
- Direct switch control bypasses the plug mode setting
- All switch state changes are logged to the server log

## Documentation

For complete API documentation, see:
- `docs/SHELLY_PLUG_SWITCH_API.md` - Full API reference with examples
- Shelly API Docs: https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch