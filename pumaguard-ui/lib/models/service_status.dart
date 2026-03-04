/// Represents the runtime status of a single managed system service
/// (e.g. hostapd or dnsmasq) as returned by GET /api/system/services.
class ServiceStatus {
  /// The systemd service name, e.g. "hostapd" or "dnsmasq".
  final String name;

  /// True when ``systemctl is-active`` exits 0 (the service is running).
  final bool active;

  /// True when ``systemctl is-enabled`` exits 0 (the service starts on boot).
  final bool enabled;

  /// Raw output of ``systemctl is-active``, e.g. "active", "inactive",
  /// "failed", "activating", "timeout", or "unavailable".
  final String state;

  /// False when systemctl itself is not installed on the host system.
  final bool available;

  const ServiceStatus({
    required this.name,
    required this.active,
    required this.enabled,
    required this.state,
    required this.available,
  });

  factory ServiceStatus.fromJson(Map<String, dynamic> json) {
    return ServiceStatus(
      name: json['name'] as String? ?? '',
      active: json['active'] as bool? ?? false,
      enabled: json['enabled'] as bool? ?? false,
      state: json['state'] as String? ?? 'unknown',
      available: json['available'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'active': active,
      'enabled': enabled,
      'state': state,
      'available': available,
    };
  }

  /// A short human-readable label derived from [state], suitable for display
  /// in a status chip or list tile subtitle.
  String get stateLabel {
    switch (state) {
      case 'active':
        return 'Running';
      case 'inactive':
        return 'Stopped';
      case 'failed':
        return 'Failed';
      case 'activating':
        return 'Starting…';
      case 'deactivating':
        return 'Stopping…';
      case 'timeout':
        return 'Timeout';
      case 'unavailable':
        return 'Unavailable';
      default:
        return state.isEmpty ? 'Unknown' : state;
    }
  }

  /// Friendly display name for the service.
  String get displayName {
    switch (name) {
      case 'hostapd':
        return 'Wi-Fi Access Point (hostapd)';
      case 'dnsmasq':
        return 'DHCP / DNS (dnsmasq)';
      default:
        return name;
    }
  }

  @override
  String toString() =>
      'ServiceStatus(name: $name, active: $active, enabled: $enabled, '
      'state: $state, available: $available)';

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ServiceStatus &&
          runtimeType == other.runtimeType &&
          name == other.name &&
          active == other.active &&
          enabled == other.enabled &&
          state == other.state &&
          available == other.available;

  @override
  int get hashCode =>
      name.hashCode ^
      active.hashCode ^
      enabled.hashCode ^
      state.hashCode ^
      available.hashCode;
}
