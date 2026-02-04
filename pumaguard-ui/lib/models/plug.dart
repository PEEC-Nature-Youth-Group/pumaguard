class Plug {
  final String hostname;
  final String ipAddress;
  final String macAddress;
  final String lastSeen;
  final String status;
  final String mode;

  Plug({
    required this.hostname,
    required this.ipAddress,
    required this.macAddress,
    required this.lastSeen,
    required this.status,
    required this.mode,
  });

  factory Plug.fromJson(Map<String, dynamic> json) {
    return Plug(
      hostname: json['hostname'] as String? ?? '',
      ipAddress: json['ip_address'] as String? ?? '',
      macAddress: json['mac_address'] as String? ?? '',
      lastSeen: json['last_seen'] as String? ?? '',
      status: json['status'] as String? ?? 'unknown',
      mode: json['mode'] as String? ?? 'off',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'hostname': hostname,
      'ip_address': ipAddress,
      'mac_address': macAddress,
      'last_seen': lastSeen,
      'status': status,
      'mode': mode,
    };
  }

  bool get isConnected => status == 'connected';

  String get displayName => hostname.isNotEmpty ? hostname : ipAddress;

  String get plugUrl {
    if (ipAddress.isEmpty) return '';
    // Return URL without scheme - let caller add http:// or https://
    return ipAddress;
  }
}
