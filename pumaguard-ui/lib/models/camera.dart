class Camera {
  final String hostname;
  final String ipAddress;
  final String macAddress;
  final String lastSeen;
  final String status;

  Camera({
    required this.hostname,
    required this.ipAddress,
    required this.macAddress,
    required this.lastSeen,
    required this.status,
  });

  factory Camera.fromJson(Map<String, dynamic> json) {
    return Camera(
      hostname: json['hostname'] as String? ?? '',
      ipAddress: json['ip_address'] as String? ?? '',
      macAddress: json['mac_address'] as String? ?? '',
      lastSeen: json['last_seen'] as String? ?? '',
      status: json['status'] as String? ?? 'unknown',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'hostname': hostname,
      'ip_address': ipAddress,
      'mac_address': macAddress,
      'last_seen': lastSeen,
      'status': status,
    };
  }

  bool get isConnected => status == 'connected';

  String get displayName => hostname.isNotEmpty ? hostname : ipAddress;

  String get cameraUrl {
    if (ipAddress.isEmpty) return '';
    // Return URL without scheme - let caller add http:// or https://
    return ipAddress;
  }
}
