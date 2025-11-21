class Status {
  final String status;
  final String version;
  final int directoriesCount;
  final String host;
  final int port;

  Status({
    required this.status,
    required this.version,
    required this.directoriesCount,
    required this.host,
    required this.port,
  });

  factory Status.fromJson(Map<String, dynamic> json) {
    return Status(
      status: json['status'] as String? ?? 'unknown',
      version: json['version'] as String? ?? '0.0.0',
      directoriesCount: json['directories_count'] as int? ?? 0,
      host: json['host'] as String? ?? 'localhost',
      port: json['port'] as int? ?? 5000,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'status': status,
      'version': version,
      'directories_count': directoriesCount,
      'host': host,
      'port': port,
    };
  }

  bool get isRunning => status == 'running';
}
