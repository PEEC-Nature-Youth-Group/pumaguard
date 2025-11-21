# Dynamic URL Detection in Flutter Web UI

## Overview

The PumaGuard Flutter web UI automatically detects the correct API URL based on how you access it. This means you can connect to the server from any IP address or hostname without hardcoding URLs.

## How It Works

### Web Platform (Browser)

When running in a web browser, the Flutter app uses `Uri.base.origin` to get the current page's origin (protocol + hostname + port) and constructs API URLs dynamically.

**Example:**
- You access: `http://192.168.1.100:5000`
- API calls go to: `http://192.168.1.100:5000/api/status`

- You access: `http://pumaguard.local:5000`
- API calls go to: `http://pumaguard.local:5000/api/status`

### Mobile/Desktop Platforms

When running as a native app (mobile or desktop), the app uses a configured base URL or defaults to `http://localhost:5000`.

## Implementation

### ApiService.getApiUrl()

The `ApiService` class has a `getApiUrl()` method that handles URL construction:

```dart
String getApiUrl(String endpoint) {
  // On web: use browser's current location
  if (kIsWeb) {
    return '${Uri.base.origin}$endpoint';
  }
  
  // On mobile/desktop: use configured baseUrl or localhost
  else {
    final base = _baseUrl ?? 'http://localhost:5000';
    return '$base$endpoint';
  }
}
```

### Usage in API Methods

All API methods use `getApiUrl()` to construct URLs:

```dart
Future<Status> getStatus() async {
  final response = await http.get(
    Uri.parse(getApiUrl('/api/status')),  // Dynamic URL
    headers: {'Content-Type': 'application/json'},
  );
  // ...
}
```

## Benefits

1. **No IP Hardcoding**: Works with any server IP or hostname
2. **DHCP-Friendly**: Server IP can change without breaking the UI
3. **mDNS Compatible**: Works with `.local` hostnames
4. **Port Flexible**: Adapts to any port the server runs on
5. **Development Easy**: No configuration needed for testing

## Usage Scenarios

### Scenario 1: Access from Different Devices

**Laptop on local network:**
```
http://192.168.1.100:5000
→ API calls: http://192.168.1.100:5000/api/*
```

**Phone on same network:**
```
http://192.168.1.100:5000
→ API calls: http://192.168.1.100:5000/api/*
```

### Scenario 2: Using mDNS Hostname

```
http://pumaguard.local:5000
→ API calls: http://pumaguard.local:5000/api/*
```

### Scenario 3: Different Ports

```
http://10.1.20.99:8080
→ API calls: http://10.1.20.99:8080/api/*
```

### Scenario 4: HTTPS (if configured)

```
https://pumaguard.example.com
→ API calls: https://pumaguard.example.com/api/*
```

## Technical Details

### Platform Detection

The code uses Flutter's `kIsWeb` constant to detect the platform:

```dart
import 'package:flutter/foundation.dart' show kIsWeb;

if (kIsWeb) {
  // Browser environment
} else {
  // Native (mobile/desktop) environment
}
```

### Uri.base.origin

On web, `Uri.base` provides information about the current page URL:

- `Uri.base.origin` = `protocol://hostname:port`
- Example: `http://192.168.1.100:5000`

This is available at runtime in the browser and automatically reflects the actual URL used to access the page.

### Compilation

During Flutter web compilation:
- No URLs are hardcoded in the JavaScript
- `Uri.base.origin` remains a runtime call in the compiled JS
- The app adapts to any deployment URL

## Verification

### Check Built Files

```bash
# Should NOT find hardcoded localhost
grep -q "localhost:5000" pumaguard-ui/build/web/main.dart.js
echo $?  # Should be 1 (not found)

# SHOULD find dynamic URL code
grep -q "Uri.base" pumaguard-ui/build/web/main.dart.js
echo $?  # Should be 0 (found)
```

### Test From Different IPs

1. Start server:
   ```bash
   pumaguard-webui --host 0.0.0.0 --port 5000
   ```

2. Access from laptop:
   ```
   http://192.168.1.100:5000
   ```

3. Access from phone:
   ```
   http://192.168.1.100:5000
   ```

4. Open browser DevTools → Network tab
5. Verify API calls go to `http://192.168.1.100:5000/api/*`

### Test With mDNS

1. Set up mDNS (see [MDNS_SETUP.md](MDNS_SETUP.md))

2. Start server:
   ```bash
   pumaguard-webui --host 0.0.0.0
   ```

3. Access via hostname:
   ```
   http://pumaguard.local:5000
   ```

4. Verify API calls use `http://pumaguard.local:5000/api/*`

## Troubleshooting

### Issue: API Calls Still Going to localhost

**Symptom:** Browser DevTools shows requests to `http://localhost:5000/api/*` even when accessing from different IP.

**Causes:**
1. Browser cache serving old JavaScript
2. Old build deployed
3. Service worker caching old files

**Solutions:**

1. **Hard refresh browser:**
   - Chrome/Firefox: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (macOS)
   - Or open DevTools → Network tab → Check "Disable cache"

2. **Clear browser cache:**
   - Chrome: Settings → Privacy → Clear browsing data
   - Firefox: Options → Privacy → Clear Data

3. **Rebuild UI:**
   ```bash
   cd pumaguard-ui
   rm -rf build/
   flutter build web --release
   cd ..
   make build-ui
   ```

4. **Clear service worker:**
   - Chrome DevTools → Application → Service Workers → Unregister
   - Or DevTools → Application → Clear storage

5. **Test in incognito/private mode:**
   - Opens fresh browser without cache

### Issue: CORS Errors

**Symptom:** Browser console shows CORS policy errors.

**Cause:** Server CORS configuration not allowing the origin.

**Solution:** The PumaGuard server is configured with permissive CORS for development:

```python
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
)
```

For production, you may want to restrict origins.

### Issue: Mixed Content (HTTP/HTTPS)

**Symptom:** Page loads via HTTPS but API calls fail.

**Cause:** Loading HTTPS page trying to call HTTP API (browsers block this).

**Solution:**
- Serve both page and API over same protocol
- Use HTTPS for both if accessing via HTTPS
- Or use HTTP for local development

## Code Structure

### Files Modified

1. **`lib/services/api_service.dart`**
   - Added `kIsWeb` import
   - Added `getApiUrl()` method
   - Updated all API methods to use `getApiUrl()`

2. **`lib/main.dart`**
   - Removed hardcoded `baseUrl` parameter
   - `ApiService()` now auto-detects URL

### Code Flow

```
User accesses: http://192.168.1.100:5000
    ↓
Flutter web app loads
    ↓
ApiService.getApiUrl('/api/status') called
    ↓
kIsWeb = true → Use Uri.base.origin
    ↓
Returns: http://192.168.1.100:5000/api/status
    ↓
HTTP request made to correct URL
```

## Related Features

### mDNS Service Discovery

The app also includes mDNS service discovery for native mobile/desktop apps:

- `MdnsService` can discover PumaGuard servers on the network
- `ServerDiscoveryScreen` provides UI for server selection
- Once discovered, `ApiService.setBaseUrl()` can be called to connect

See [MDNS_FEATURES.md](MDNS_FEATURES.md) for details.

### Manual URL Configuration

On mobile/desktop, users can manually configure the server URL:

```dart
final apiService = context.read<ApiService>();
apiService.setBaseUrl('http://192.168.1.100:5000');
```

## Best Practices

1. **Never hardcode URLs** in Flutter code
2. **Always use `getApiUrl()`** for API endpoint construction
3. **Test from multiple devices** to verify dynamic detection
4. **Clear cache** when testing changes
5. **Check DevTools Network tab** to verify actual URLs used

## Future Enhancements

Potential improvements:

- [ ] Remember last-used server URL in local storage
- [ ] Server URL picker in UI for mobile apps
- [ ] Automatic fallback to mDNS discovery if direct access fails
- [ ] Health check with automatic server switching
- [ ] Support for multiple simultaneous server connections

## References

- [Flutter Web Deployment](https://docs.flutter.dev/deployment/web)
- [Dart Uri Class](https://api.dart.dev/stable/dart-core/Uri-class.html)
- [CORS Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [mDNS Setup Guide](MDNS_SETUP.md)