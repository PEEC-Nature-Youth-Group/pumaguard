# mDNS/Zeroconf Feature Summary

## Overview

PumaGuard now includes full mDNS (multicast DNS) / Zeroconf / Bonjour support for automatic service discovery on local networks. This allows clients to discover and connect to PumaGuard servers using friendly hostnames like `pumaguard.local` without needing to know IP addresses.

## Features Added

### Python Web Server (Backend)

#### Automatic Service Advertisement
- The web server automatically registers itself via mDNS when started
- Advertises as `_http._tcp.local` service type
- Default hostname: `pumaguard.local`
- Includes service metadata (version, app name, path)

#### New Dependencies
- `zeroconf ~= 0.136` - Python library for mDNS/Zeroconf support

#### New Command-Line Options
```bash
# Customize mDNS hostname
pumaguard-webui --mdns-name custom-name
# Access at: http://custom-name.local:5000

# Disable mDNS
pumaguard-webui --no-mdns
```

#### API Enhancements
- `/api/diagnostic` endpoint now includes mDNS status:
  - `mdns_enabled`: Whether mDNS is active
  - `mdns_name`: The advertised service name
  - `mdns_url`: Full mDNS URL (e.g., `http://pumaguard.local:5000`)
  - `local_ip`: Detected local IP address

#### New Methods in WebUI Class
- `_start_mdns()`: Register mDNS service
- `_stop_mdns()`: Unregister mDNS service
- `_get_local_ip()`: Determine local network IP address

#### Constructor Parameters
```python
WebUI(
    presets=presets,
    host='0.0.0.0',
    port=5000,
    mdns_enabled=True,      # New parameter
    mdns_name='pumaguard'   # New parameter
)
```

### Flutter Web UI (Frontend)

#### New Service: MdnsService
Location: `lib/services/mdns_service.dart`

Features:
- **Automatic Discovery**: Scan local network for PumaGuard servers
- **Service Resolution**: Resolve `.local` hostnames to IP addresses
- **Continuous Discovery**: Optional periodic scanning
- **Platform-Aware**: 
  - Full functionality on mobile/desktop (using `multicast_dns` package)
  - Graceful degradation on web (stub implementation with helpful messages)

API:
```dart
final mdnsService = MdnsService();

// One-time discovery
List<PumaguardServer> servers = await mdnsService.discoverServers();

// Continuous discovery with stream
await mdnsService.startDiscovery();
mdnsService.serversStream.listen((servers) {
  print('Found ${servers.length} servers');
});

// Find specific server
PumaguardServer? server = await mdnsService.findServerByName('pumaguard');

// Resolve hostname
String? ip = await mdnsService.resolveLocalHostname('pumaguard.local');

// Cleanup
mdnsService.dispose();
```

#### New Screen: ServerDiscoveryScreen
Location: `lib/screens/server_discovery_screen.dart`

Features:
- **Visual Server Discovery**: Shows all discovered PumaGuard servers
- **One-Click Connect**: Connect to discovered servers with a button
- **Manual Hostname Entry**: Resolve and connect to `.local` hostnames
- **Manual URL Entry**: Direct connection via IP:port
- **Help Information**: Built-in troubleshooting tips
- **Status Messages**: Real-time feedback during discovery

UI Components:
- Discovered servers list with metadata (IP, hostname, version)
- Hostname resolution form
- Manual URL connection form
- Refresh button for re-scanning
- Loading indicators
- Connection status dialogs

#### Enhanced ApiService
New method:
```dart
apiService.setBaseUrl('http://192.168.1.100:5000');
```

Allows dynamic switching between servers discovered via mDNS.

#### New Model: PumaguardServer
```dart
class PumaguardServer {
  final String name;        // Service name (e.g., "pumaguard")
  final String hostname;    // Full hostname (e.g., "pumaguard.local")
  final String ip;          // IP address
  final int port;           // Port number
  final Map<String, String> properties;  // Service metadata
  
  String get baseUrl;       // http://ip:port
  String get mdnsUrl;       // http://hostname:port
}
```

#### New Dependencies
- `multicast_dns: ^0.3.2+7` - Dart package for mDNS service discovery

#### Platform-Specific Implementation
Uses conditional exports to provide:
- **Native** (`mdns_service_impl.dart`): Full mDNS discovery using `MDnsClient`
- **Web** (`mdns_service_web.dart`): Stub implementation with helpful messages

The web platform cannot perform mDNS discovery due to browser security restrictions, but can still resolve `.local` hostnames through the OS if mDNS is configured.

## Documentation

### New Files
1. **`docs/MDNS_SETUP.md`** (508 lines)
   - Comprehensive setup guide for Linux, macOS, Windows
   - Docker/container configuration
   - Kubernetes deployment notes
   - Troubleshooting section
   - Network requirements
   - Security considerations

2. **`docs/QUICK_START_MDNS.md`** (216 lines)
   - 5-minute quick start guide
   - Common issues and solutions
   - Docker setup examples
   - FAQ section

3. **`docs/MDNS_FEATURES.md`** (This file)
   - Feature overview and API reference

### Updated Files
- **`README.md`**: Added Web UI and mDNS sections
- **`pyproject.toml`**: Added zeroconf dependency
- **`requirements.txt`**: Added zeroconf
- **`pubspec.yaml`**: Added multicast_dns dependency

## Usage Examples

### Python Server

#### Basic Usage (mDNS enabled by default)
```python
from pumaguard.web_ui import WebUI
from pumaguard.presets import Preset

presets = Preset()
web_ui = WebUI(
    presets=presets,
    host='0.0.0.0',
    port=5000
)
web_ui.start()
# Server accessible at http://pumaguard.local:5000
```

#### Custom Hostname
```python
web_ui = WebUI(
    presets=presets,
    host='0.0.0.0',
    port=5000,
    mdns_name='wildlife-cam-1'
)
web_ui.start()
# Server accessible at http://wildlife-cam-1.local:5000
```

#### Disable mDNS
```python
web_ui = WebUI(
    presets=presets,
    host='0.0.0.0',
    port=5000,
    mdns_enabled=False
)
web_ui.start()
```

### Flutter Client

#### Basic Discovery
```dart
import 'package:pumaguard_ui/services/mdns_service.dart';

final mdnsService = MdnsService();
final servers = await mdnsService.discoverServers();

for (final server in servers) {
  print('Found: ${server.name} at ${server.ip}:${server.port}');
}
```

#### Connect to Discovered Server
```dart
import 'package:provider/provider.dart';

final apiService = context.read<ApiService>();
final mdnsService = MdnsService();

final servers = await mdnsService.discoverServers();
if (servers.isNotEmpty) {
  final server = servers.first;
  apiService.setBaseUrl(server.baseUrl);
  
  // Test connection
  final status = await apiService.getStatus();
  print('Connected to ${status.host}');
}
```

#### Using the Discovery Screen
```dart
// Navigate to server discovery
Navigator.push(
  context,
  MaterialPageRoute(
    builder: (context) => const ServerDiscoveryScreen(),
  ),
);
```

## Command-Line Examples

### Start Server with mDNS
```bash
# Default (pumaguard.local)
pumaguard-webui --host 0.0.0.0

# Custom name
pumaguard-webui --host 0.0.0.0 --mdns-name my-pumaguard

# Disable mDNS
pumaguard-webui --host 0.0.0.0 --no-mdns
```

### Test mDNS Discovery
```bash
# Linux
avahi-browse -t _http._tcp
avahi-resolve -n pumaguard.local

# macOS
dns-sd -B _http._tcp
dns-sd -G v4 pumaguard.local

# Test API
curl http://pumaguard.local:5000/api/diagnostic | jq .
```

## Requirements

### Server Requirements
- **Linux**: Avahi daemon (`avahi-daemon` package)
- **macOS**: Built-in (no additional setup)
- **Windows**: Bonjour Print Services
- **Docker**: Host networking or Avahi socket mount

### Network Requirements
- Port 5353 UDP must be open for mDNS multicast
- Devices must be on same subnet (unless using Avahi reflector)
- Network must allow multicast traffic (224.0.0.251)

### Python Dependencies
- `zeroconf >= 0.136`
- Existing PumaGuard dependencies

### Flutter Dependencies
- `multicast_dns >= 0.3.2`
- Existing Flutter dependencies

## Architecture

### Python Layer
```
WebUI
  ├── Flask app (HTTP server)
  ├── Zeroconf (mDNS advertisement)
  │   ├── ServiceInfo (service metadata)
  │   └── Socket binding (local IP detection)
  └── Routes
      └── /api/diagnostic (mDNS status)
```

### Flutter Layer
```
UI
  ├── ServerDiscoveryScreen (user interface)
  ├── MdnsService (discovery logic)
  │   ├── MDnsClient (native)
  │   └── Stub (web)
  ├── ApiService (HTTP client)
  └── PumaguardServer (data model)
```

### Communication Flow
```
1. Server starts → Advertises via mDNS
2. Client scans → Discovers services
3. Client selects server → Updates API base URL
4. Client connects → Makes HTTP requests
```

## Platform Support Matrix

| Feature | Linux | macOS | Windows | Docker | Web Browser |
|---------|-------|-------|---------|--------|-------------|
| Server mDNS | ✅ (Avahi) | ✅ (Native) | ✅ (Bonjour) | ✅ (Host mode) | N/A |
| Client Discovery | ✅ | ✅ | ✅ | ✅ | ❌ |
| Hostname Resolution | ✅ | ✅ | ✅ (limited) | ✅ | ⚠️ (OS-level) |
| Manual Connection | ✅ | ✅ | ✅ | ✅ | ✅ |

Legend:
- ✅ Full support
- ⚠️ Partial support
- ❌ Not supported
- N/A Not applicable

## Benefits

1. **Zero Configuration**: Works out of the box once mDNS is installed
2. **DHCP-Friendly**: Server IP can change without affecting clients
3. **User-Friendly**: No need to remember IP addresses
4. **Automatic Discovery**: Clients can find all PumaGuard servers on network
5. **Multiple Servers**: Support multiple instances with different names
6. **Cross-Platform**: Works on Linux, macOS, and Windows
7. **Container-Ready**: Works in Docker with proper configuration

## Limitations

1. **Local Network Only**: mDNS doesn't cross router boundaries by default
2. **Web Browser Restrictions**: Cannot perform programmatic discovery in browsers
3. **Requires mDNS Service**: OS-level service must be installed and running
4. **Multicast Required**: Network switches/routers must allow multicast
5. **Security**: Advertises service presence (disable for sensitive deployments)

## Future Enhancements

Potential improvements for future versions:
- [ ] DNS-SD service browsing in web UI
- [ ] mDNS reflector configuration helper
- [ ] Encryption/authentication for discovered services
- [ ] Service metadata filtering (version compatibility checks)
- [ ] Favorite servers persistence
- [ ] QR code generation for easy connection
- [ ] Network interface selection
- [ ] IPv6 support enhancement

## Troubleshooting

For detailed troubleshooting, see:
- [MDNS_SETUP.md](MDNS_SETUP.md#troubleshooting) - Comprehensive troubleshooting guide
- [QUICK_START_MDNS.md](QUICK_START_MDNS.md#common-issues--solutions) - Quick fixes

Common issues:
1. **Server not discoverable**: Check Avahi/Bonjour service status
2. **Hostname not resolving**: Verify NSS configuration (Linux)
3. **Firewall blocking**: Allow port 5353 UDP
4. **Docker issues**: Use host networking or mount Avahi socket
5. **Cross-subnet**: Enable Avahi reflector or use manual connection

## References

- [RFC 6762 - Multicast DNS](https://tools.ietf.org/html/rfc6762)
- [RFC 6763 - DNS-Based Service Discovery](https://tools.ietf.org/html/rfc6763)
- [Python zeroconf](https://github.com/python-zeroconf/python-zeroconf)
- [Flutter multicast_dns](https://pub.dev/packages/multicast_dns)
- [Avahi Documentation](https://www.avahi.org/)
- [Apple Bonjour](https://developer.apple.com/bonjour/)

## Contributing

When working with mDNS features:
1. Test on all platforms (Linux, macOS, Windows)
2. Verify Docker/container compatibility
3. Update documentation for any API changes
4. Include error handling for network failures
5. Consider graceful degradation on unsupported platforms

## License

This feature follows the same license as the main PumaGuard project.