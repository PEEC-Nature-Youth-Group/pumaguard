# Shelly Plug Switch Control - Implementation Summary

## Overview

This document summarizes the implementation of the Shelly plug switch control feature, which allows users to turn Shelly plugs on and off via the PumaGuard REST API.

## Implementation Date

January 2025

## Changes Made

### 1. API Endpoint Added

**File:** `pumaguard/pumaguard/web_routes/dhcp.py`

**New Route:** `PUT /api/dhcp/plugs/<mac_address>/switch`

**Function:** `set_plug_switch(mac_address: str)`

**Location:** Lines 1015-1196 (inserted between `get_shelly_status` and `camera_events` functions)

### 2. Functionality

The endpoint:
- Accepts JSON payload with `{"on": true/false}`
- Validates that the plug exists and is connected
- Calls the Shelly Gen2 Switch.Set API: `http://<plug_ip>/rpc/Switch.Set?id=0&on={true|false}`
- Returns success/failure with previous and current switch state
- Broadcasts SSE event `plug_switch_changed` to all connected clients

### 3. Request/Response

**Request:**
```json
PUT /api/dhcp/plugs/aa:bb:cc:dd:ee:ff/switch
Content-Type: application/json

{
  "on": true
}
```

**Success Response (200):**
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

**Error Responses:**
- `400` - Invalid request (missing/invalid parameters)
- `404` - Plug not found
- `503` - Plug not connected
- `504` - Timeout connecting to plug
- `500` - Internal server error

### 4. Validation

The endpoint validates:
1. JSON data is provided
2. `on` parameter exists
3. `on` parameter is a boolean
4. Plug exists in the system
5. Plug has an IP address
6. Plug status is "connected"

### 5. Error Handling

Comprehensive error handling for:
- Missing or invalid request data
- Plug not found or disconnected
- Network timeouts (5 second default)
- Connection errors
- Invalid Shelly API responses
- Unexpected exceptions

### 6. SSE Notification

When a switch state changes, the endpoint broadcasts an event to all SSE clients:

```json
{
  "type": "plug_switch_changed",
  "data": {
    "hostname": "shellyplugus-example",
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

## Tests Added

**File:** `pumaguard/tests/test_dhcp_routes.py`

**New Tests (9 total):**
1. `test_set_plug_switch_on_success` - Turn switch ON successfully
2. `test_set_plug_switch_off_success` - Turn switch OFF successfully
3. `test_set_plug_switch_no_json_data` - Error when no JSON provided
4. `test_set_plug_switch_missing_on_parameter` - Error when 'on' parameter missing
5. `test_set_plug_switch_invalid_on_parameter` - Error when 'on' is not boolean
6. `test_set_plug_switch_plug_not_found` - Error when plug doesn't exist
7. `test_set_plug_switch_plug_disconnected` - Error when plug is disconnected
8. `test_set_plug_switch_timeout` - Error on connection timeout
9. `test_set_plug_switch_connection_error` - Error on connection failure

**Test Coverage:**
- All tests pass (41/41 in test_dhcp_routes.py)
- Tests use mocking to avoid actual network calls
- Tests cover success cases, validation, and all error conditions

## Documentation Added

### 1. API Documentation
**File:** `pumaguard/docs/SHELLY_PLUG_SWITCH_API.md`

Complete API reference including:
- Endpoint description
- Request/response formats
- All error codes
- Usage examples in curl, Python, and JavaScript
- SSE event format
- Prerequisites
- Related endpoints
- Shelly API reference

### 2. Quick Reference Guide
**File:** `pumaguard/SHELLY_PLUG_CONTROL_SUMMARY.md`

Quick reference guide with:
- Overview
- Quick examples
- How it works
- Error handling
- Integration points
- Testing instructions

### 3. Implementation Summary
**File:** `pumaguard/SHELLY_PLUG_SWITCH_IMPLEMENTATION.md` (this file)

## Shelly API Integration

The implementation uses the Shelly Gen2 Switch.Set API:

**API Endpoint:** `http://<plug_ip>/rpc/Switch.Set?id=0&on={true|false}`

**Parameters:**
- `id`: Switch component ID (always 0 for single-switch plugs)
- `on`: Boolean value (true or false)

**Shelly Response:**
```json
{
  "was_on": false
}
```

**Official Documentation:**
https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch#switchset

## Code Quality

- No new errors introduced
- Pre-existing warnings unchanged (3 warnings in dhcp.py, unrelated to new code)
- Follows existing code patterns and style
- Proper logging at INFO level for switch changes
- DEBUG level logging for API calls
- Comprehensive error logging

## Dependencies

No new dependencies required. Uses existing:
- `requests` - for HTTP calls to Shelly API
- `flask` - for REST API
- Standard Python libraries

## Security Considerations

- MAC address is normalized to lowercase for consistency
- IP address validation through plug existence check
- Timeout prevents hanging requests (5 second default)
- No authentication required (relies on network security)
- Logs don't expose sensitive information

## Performance

- Synchronous HTTP call to Shelly plug (5 second timeout)
- Response time depends on network latency to plug
- No database operations
- Minimal processing overhead

## Backwards Compatibility

- No breaking changes to existing APIs
- No changes to existing data structures
- No changes to existing plug functionality
- Purely additive feature

## Future Enhancements

Potential improvements:
1. Batch operations for multiple plugs
2. Toggle endpoint (flip current state)
3. Scheduled switch operations
4. Integration with plug mode system
5. Switch state caching
6. Retry logic for failed operations

## Usage Example

```bash
# Turn plug ON
curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/switch \
  -H "Content-Type: application/json" \
  -d '{"on": true}'

# Turn plug OFF
curl -X PUT http://localhost:5000/api/dhcp/plugs/aa:bb:cc:dd:ee:ff/switch \
  -H "Content-Type: application/json" \
  -d '{"on": false}'
```

## Testing

All tests pass:
```
$ pytest tests/test_dhcp_routes.py -v
41 passed in 3.37s
```

## Related Files

### Modified
- `pumaguard/pumaguard/web_routes/dhcp.py` - Added switch control endpoint

### Added
- `pumaguard/docs/SHELLY_PLUG_SWITCH_API.md` - Complete API documentation
- `pumaguard/SHELLY_PLUG_CONTROL_SUMMARY.md` - Quick reference guide
- `pumaguard/SHELLY_PLUG_SWITCH_IMPLEMENTATION.md` - This file
- Tests in `pumaguard/tests/test_dhcp_routes.py` - 9 new test cases

### Unchanged
- `pumaguard/pumaguard/plug_heartbeat.py` - Existing plug monitoring
- `pumaguard/pumaguard/presets.py` - Existing plug settings
- `pumaguard/pumaguard/web_ui.py` - Existing WebUI setup

## Deployment Notes

1. No database migrations required
2. No configuration changes required
3. No restart required for existing sessions (new endpoint auto-registered)
4. Works with existing Shelly Plug US Gen2 devices
5. Compatible with all Shelly Gen2 devices that support Switch.Set API

## Verification

To verify the implementation:

1. Start PumaGuard server
2. Ensure a Shelly plug is registered and connected
3. Get plug MAC address: `curl http://localhost:5000/api/dhcp/plugs`
4. Turn switch ON: `curl -X PUT http://localhost:5000/api/dhcp/plugs/<mac>/switch -H "Content-Type: application/json" -d '{"on": true}'`
5. Verify response contains `"status": "success"`
6. Check plug physically turns on
7. Turn switch OFF and verify

## Support

For questions or issues:
- See API documentation: `docs/SHELLY_PLUG_SWITCH_API.md`
- See quick reference: `SHELLY_PLUG_CONTROL_SUMMARY.md`
- Check test cases: `tests/test_dhcp_routes.py`
- Review Shelly API docs: https://shelly-api-docs.shelly.cloud/

## License

Same as PumaGuard project license.

## Contributors

- Implementation: AI Assistant (January 2025)
- Testing: Automated test suite
- Documentation: Complete API and implementation docs