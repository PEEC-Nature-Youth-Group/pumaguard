class Plug {
  final String hostname;
  final String ipAddress;
  final String macAddress;
  final String lastSeen;
  final String status;
  final String mode;

  // Shelly status fields
  final bool? output;
  final double? apower;
  final double? voltage;
  final double? current;
  final Map<String, dynamic>? temperature;

  Plug({
    required this.hostname,
    required this.ipAddress,
    required this.macAddress,
    required this.lastSeen,
    required this.status,
    required this.mode,
    this.output,
    this.apower,
    this.voltage,
    this.current,
    this.temperature,
  });

  factory Plug.fromJson(Map<String, dynamic> json) {
    return Plug(
      hostname: json['hostname'] as String? ?? '',
      ipAddress: json['ip_address'] as String? ?? '',
      macAddress: json['mac_address'] as String? ?? '',
      lastSeen: json['last_seen'] as String? ?? '',
      status: json['status'] as String? ?? 'unknown',
      mode: json['mode'] as String? ?? 'automatic',
      output: json['output'] as bool?,
      apower: (json['apower'] as num?)?.toDouble(),
      voltage: (json['voltage'] as num?)?.toDouble(),
      current: (json['current'] as num?)?.toDouble(),
      temperature: json['temperature'] as Map<String, dynamic>?,
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
      if (output != null) 'output': output,
      if (apower != null) 'apower': apower,
      if (voltage != null) 'voltage': voltage,
      if (current != null) 'current': current,
      if (temperature != null) 'temperature': temperature,
    };
  }

  bool get isConnected => status == 'connected';

  String get displayName => hostname.isNotEmpty ? hostname : ipAddress;

  String get plugUrl {
    if (ipAddress.isEmpty) return '';
    // Return URL without scheme - let caller add http:// or https://
    return ipAddress;
  }

  /// Creates a copy of this Plug with updated Shelly status
  Plug copyWithShellyStatus({
    bool? output,
    double? apower,
    double? voltage,
    double? current,
    Map<String, dynamic>? temperature,
  }) {
    return Plug(
      hostname: hostname,
      ipAddress: ipAddress,
      macAddress: macAddress,
      lastSeen: lastSeen,
      status: status,
      mode: mode,
      output: output ?? this.output,
      apower: apower ?? this.apower,
      voltage: voltage ?? this.voltage,
      current: current ?? this.current,
      temperature: temperature ?? this.temperature,
    );
  }
}
