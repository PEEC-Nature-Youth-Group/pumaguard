class Status {
  final String status;
  final String version;
  final int directoriesCount;
  final String host;
  final int port;
  final int uptimeSeconds;

  Status({
    required this.status,
    required this.version,
    required this.directoriesCount,
    required this.host,
    required this.port,
    required this.uptimeSeconds,
  });

  factory Status.fromJson(Map<String, dynamic> json) {
    return Status(
      status: json['status'] as String? ?? 'unknown',
      version: json['version'] as String? ?? '0.0.0',
      directoriesCount: json['directories_count'] as int? ?? 0,
      host: json['host'] as String? ?? 'localhost',
      port: json['port'] as int? ?? 5000,
      uptimeSeconds: json['uptime_seconds'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status,
      'version': version,
      'directories_count': directoriesCount,
      'host': host,
      'port': port,
      'uptime_seconds': uptimeSeconds,
    };
  }

  bool get isRunning => status == 'running';

  String get uptimeFormatted {
    final days = uptimeSeconds ~/ 86400;
    final hours = (uptimeSeconds % 86400) ~/ 3600;
    final minutes = (uptimeSeconds % 3600) ~/ 60;
    final seconds = uptimeSeconds % 60;

    if (days > 0) {
      return '${days}d ${hours}h ${minutes}m';
    } else if (hours > 0) {
      return '${hours}h ${minutes}m ${seconds}s';
    } else if (minutes > 0) {
      return '${minutes}m ${seconds}s';
    } else {
      return '${seconds}s';
    }
  }
}
