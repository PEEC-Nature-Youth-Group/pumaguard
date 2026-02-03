import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:multicast_dns/multicast_dns.dart';

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

/// Service for discovering Pumaguard servers via mDNS/Zeroconf
class MdnsService {
  static const String serviceType = '_http._tcp';
  static const Duration discoveryTimeout = Duration(seconds: 5);
  static const Duration discoveryInterval = Duration(seconds: 30);

  final List<PumaguardServer> _discoveredServers = [];
  final StreamController<List<PumaguardServer>> _serversController =
      StreamController<List<PumaguardServer>>.broadcast();

  MDnsClient? _mdns;
  Timer? _discoveryTimer;
  bool _isDiscovering = false;

  /// Stream of discovered servers
  Stream<List<PumaguardServer>> get serversStream => _serversController.stream;

  /// List of currently discovered servers
  List<PumaguardServer> get servers => List.unmodifiable(_discoveredServers);

  /// Start continuous discovery of Pumaguard servers
  Future<void> startDiscovery() async {
    if (_isDiscovering) {
      return;
    }

    _isDiscovering = true;

    // Do initial discovery
    await discoverServers();

    // Set up periodic discovery
    _discoveryTimer = Timer.periodic(discoveryInterval, (timer) async {
      await discoverServers();
    });
  }

  /// Stop continuous discovery
  void stopDiscovery() {
    _discoveryTimer?.cancel();
    _discoveryTimer = null;
    _isDiscovering = false;
  }

  /// Discover Pumaguard servers on the network
  Future<List<PumaguardServer>> discoverServers() async {
    try {
      // Create mDNS client if needed
      if (_mdns == null) {
        _mdns = MDnsClient(
          rawDatagramSocketFactory:
              (
                dynamic host,
                int port, {
                bool? reuseAddress,
                bool? reusePort,
                int? ttl,
              }) async {
                return RawDatagramSocket.bind(
                  host,
                  port,
                  reuseAddress: reuseAddress ?? true,
                  reusePort: reusePort ?? false,
                  ttl: ttl ?? 255,
                );
              },
        );
        await _mdns!.start();
      }

      final Set<PumaguardServer> foundServers = {};

      // Query for HTTP services
      await for (final PtrResourceRecord ptr
          in _mdns!
              .lookup<PtrResourceRecord>(
                ResourceRecordQuery.serverPointer(serviceType),
              )
              .timeout(discoveryTimeout)) {
        // Get service details
        final String serviceName = ptr.domainName;

        // Query for service details (SRV and TXT records)
        final srvFuture = _mdns!
            .lookup<SrvResourceRecord>(ResourceRecordQuery.service(serviceName))
            .timeout(discoveryTimeout)
            .toList();

        final txtFuture = _mdns!
            .lookup<TxtResourceRecord>(ResourceRecordQuery.text(serviceName))
            .timeout(discoveryTimeout)
            .toList();

        final ipFuture = _mdns!
            .lookup<IPAddressResourceRecord>(
              ResourceRecordQuery.addressIPv4(serviceName),
            )
            .timeout(discoveryTimeout)
            .toList();

        final results = await Future.wait([srvFuture, txtFuture, ipFuture]);
        final srvRecords = results[0] as List<SrvResourceRecord>;
        final txtRecords = results[1] as List<TxtResourceRecord>;
        final ipRecords = results[2] as List<IPAddressResourceRecord>;

        // Process SRV records to get port and hostname
        for (final srv in srvRecords) {
          final int port = srv.port;
          final String target = srv.target;

          // Parse TXT records for properties
          final Map<String, String> properties = {};
          for (final txt in txtRecords) {
            for (final String data in txt.text.split('\n')) {
              final parts = data.split('=');
              if (parts.length == 2) {
                properties[parts[0]] = parts[1];
              }
            }
          }

          // Check if this is a Pumaguard server
          final ispumaguard =
              properties['app'] == 'pumaguard' ||
              serviceName.toLowerCase().contains('pumaguard');

          if (!ispumaguard) {
            continue;
          }

          // Get IP addresses
          for (final ip in ipRecords) {
            final server = PumaguardServer(
              name: serviceName.split('.').first,
              hostname: target.replaceAll(RegExp(r'\.$'), ''),
              ip: ip.address.address,
              port: port,
              properties: properties,
            );

            foundServers.add(server);
          }
        }
      }

      // Update discovered servers list
      _discoveredServers.clear();
      _discoveredServers.addAll(foundServers);

      // Notify listeners
      if (!_serversController.isClosed) {
        _serversController.add(_discoveredServers);
      }

      return _discoveredServers;
    } catch (e) {
      // Discovery failed, return empty list
      debugPrint('mDNS discovery error: $e');
      return [];
    }
  }

  /// Find a specific server by name
  Future<PumaguardServer?> findServerByName(String name) async {
    // First check already discovered servers
    for (final server in _discoveredServers) {
      if (server.name.toLowerCase() == name.toLowerCase()) {
        return server;
      }
    }

    // Do a fresh discovery
    final servers = await discoverServers();
    for (final server in servers) {
      if (server.name.toLowerCase() == name.toLowerCase()) {
        return server;
      }
    }

    return null;
  }

  /// Resolve a .local hostname to an IP address
  Future<String?> resolveLocalHostname(String hostname) async {
    try {
      if (_mdns == null) {
        _mdns = MDnsClient(
          rawDatagramSocketFactory:
              (
                dynamic host,
                int port, {
                bool? reuseAddress,
                bool? reusePort,
                int? ttl,
              }) async {
                return RawDatagramSocket.bind(
                  host,
                  port,
                  reuseAddress: reuseAddress ?? true,
                  reusePort: reusePort ?? false,
                  ttl: ttl ?? 255,
                );
              },
        );
        await _mdns!.start();
      }

      // Ensure hostname ends with .local
      if (!hostname.endsWith('.local')) {
        hostname = '$hostname.local';
      }

      // Query for IPv4 address
      await for (final IPAddressResourceRecord record
          in _mdns!
              .lookup<IPAddressResourceRecord>(
                ResourceRecordQuery.addressIPv4(hostname),
              )
              .timeout(discoveryTimeout)) {
        return record.address.address;
      }

      return null;
    } catch (e) {
      debugPrint('Hostname resolution error: $e');
      return null;
    }
  }

  /// Clean up resources
  void dispose() {
    stopDiscovery();
    _mdns?.stop();
    _serversController.close();
  }
}
