import 'dart:async';

import 'package:flutter/foundation.dart';

/// Represents a discovered Pumaguard server via mDNS
class PumaguardServer {
  final String name;
  final String hostname;
  final String ip;
  final int port;
  final Map<String, String> properties;

  PumaguardServer({
    required this.name,
    required this.hostname,
    required this.ip,
    required this.port,
    required this.properties,
  });

  /// Get the base URL for this server
  String get baseUrl => 'http://$ip:$port';

  /// Get the mDNS URL (hostname.local)
  String get mdnsUrl => 'http://$hostname:$port';

  @override
  String toString() {
    return 'PumaguardServer(name: $name, ip: $ip, port: $port, hostname: $hostname)';
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is PumaguardServer &&
        other.name == name &&
        other.ip == ip &&
        other.port == port;
  }

  @override
  int get hashCode => Object.hash(name, ip, port);
}

/// Web stub for mDNS service (mDNS discovery not supported in web browsers)
///
/// Note: mDNS/Zeroconf discovery requires native socket access which is not
/// available in web browsers. This is a no-op implementation for web platforms.
/// Users should use manual URL entry or rely on the dynamic URL detection.
class MdnsService {
  static const String serviceType = '_http._tcp';
  static const Duration discoveryTimeout = Duration(seconds: 5);
  static const Duration discoveryInterval = Duration(seconds: 30);

  final List<PumaguardServer> _discoveredServers = [];
  final StreamController<List<PumaguardServer>> _serversController =
      StreamController<List<PumaguardServer>>.broadcast();

  /// Stream of discovered servers (always empty on web)
  Stream<List<PumaguardServer>> get serversStream => _serversController.stream;

  /// List of currently discovered servers (always empty on web)
  List<PumaguardServer> get servers => List.unmodifiable(_discoveredServers);

  /// Start continuous discovery (no-op on web)
  Future<void> startDiscovery() async {
    // mDNS discovery is not supported on web platforms
    debugPrint('mDNS discovery is not available in web browsers');
    return;
  }

  /// Stop continuous discovery (no-op on web)
  void stopDiscovery() {
    // No-op on web
  }

  /// Discover servers (always returns empty list on web)
  Future<List<PumaguardServer>> discoverServers() async {
    // mDNS discovery requires native socket access not available in browsers
    debugPrint('mDNS discovery is not supported on web. Use manual URL entry.');
    return [];
  }

  /// Find a specific server by name (always returns null on web)
  Future<PumaguardServer?> findServerByName(String name) async {
    // Not supported on web
    return null;
  }

  /// Resolve a .local hostname (not supported on web)
  ///
  /// Note: Browsers may be able to resolve .local hostnames through the OS
  /// if mDNS is properly configured, but programmatic resolution is not available.
  Future<String?> resolveLocalHostname(String hostname) async {
    debugPrint('Hostname resolution is not available in web browsers');
    debugPrint(
      'Browsers may resolve .local hostnames through the OS automatically',
    );
    return null;
  }

  /// Clean up resources
  void dispose() {
    _serversController.close();
  }
}
