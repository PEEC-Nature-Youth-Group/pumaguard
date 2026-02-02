// Unit tests for Status model
// Tests JSON serialization, deserialization, and helper methods

import 'package:flutter_test/flutter_test.dart';
import 'package:pumaguard_ui/models/status.dart';

void main() {
  group('Status Model Tests', () {
    group('Constructor', () {
      test('creates Status with all fields', () {
        final status = Status(
          status: 'running',
          version: '1.2.3',
          directoriesCount: 5,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 3665,
        );

        expect(status.status, 'running');
        expect(status.version, '1.2.3');
        expect(status.directoriesCount, 5);
        expect(status.host, 'localhost');
        expect(status.port, 5000);
        expect(status.uptimeSeconds, 3665);
      });

      test('creates Status with empty strings', () {
        final status = Status(
          status: '',
          version: '',
          directoriesCount: 0,
          host: '',
          port: 0,
          uptimeSeconds: 0,
        );

        expect(status.status, '');
        expect(status.version, '');
        expect(status.directoriesCount, 0);
        expect(status.host, '');
        expect(status.port, 0);
        expect(status.uptimeSeconds, 0);
      });
    });

    group('fromJson', () {
      test('parses complete JSON correctly', () {
        final json = {
          'status': 'running',
          'version': '1.2.3',
          'directories_count': 5,
          'host': 'localhost',
          'port': 5000,
          'uptime_seconds': 3665,
        };

        final status = Status.fromJson(json);

        expect(status.status, 'running');
        expect(status.version, '1.2.3');
        expect(status.directoriesCount, 5);
        expect(status.host, 'localhost');
        expect(status.port, 5000);
        expect(status.uptimeSeconds, 3665);
      });

      test('handles null values with defaults', () {
        final json = {
          'status': null,
          'version': null,
          'directories_count': null,
          'host': null,
          'port': null,
          'uptime_seconds': null,
        };

        final status = Status.fromJson(json);

        expect(status.status, 'unknown');
        expect(status.version, '0.0.0');
        expect(status.directoriesCount, 0);
        expect(status.host, 'localhost');
        expect(status.port, 5000);
        expect(status.uptimeSeconds, 0);
      });

      test('handles missing fields with defaults', () {
        final json = <String, dynamic>{};

        final status = Status.fromJson(json);

        expect(status.status, 'unknown');
        expect(status.version, '0.0.0');
        expect(status.directoriesCount, 0);
        expect(status.host, 'localhost');
        expect(status.port, 5000);
        expect(status.uptimeSeconds, 0);
      });

      test('handles partial JSON with some fields missing', () {
        final json = {'status': 'stopped', 'version': '2.0.0'};

        final status = Status.fromJson(json);

        expect(status.status, 'stopped');
        expect(status.version, '2.0.0');
        expect(status.directoriesCount, 0);
        expect(status.host, 'localhost');
        expect(status.port, 5000);
        expect(status.uptimeSeconds, 0);
      });

      test('handles different status values', () {
        final statuses = ['running', 'stopped', 'error', 'idle', 'unknown'];

        for (final statusValue in statuses) {
          final json = {'status': statusValue};
          final status = Status.fromJson(json);
          expect(status.status, statusValue);
        }
      });

      test('handles different port numbers', () {
        final ports = [5000, 8080, 3000, 80, 443, 65535];

        for (final portValue in ports) {
          final json = {'port': portValue};
          final status = Status.fromJson(json);
          expect(status.port, portValue);
        }
      });

      test('handles different host values', () {
        final hosts = [
          'localhost',
          '127.0.0.1',
          '192.168.1.100',
          'pumaguard.local',
          '0.0.0.0',
        ];

        for (final hostValue in hosts) {
          final json = {'host': hostValue};
          final status = Status.fromJson(json);
          expect(status.host, hostValue);
        }
      });
    });

    group('toJson', () {
      test('converts Status to JSON correctly', () {
        final status = Status(
          status: 'running',
          version: '1.2.3',
          directoriesCount: 5,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 3665,
        );

        final json = status.toJson();

        expect(json['status'], 'running');
        expect(json['version'], '1.2.3');
        expect(json['directories_count'], 5);
        expect(json['host'], 'localhost');
        expect(json['port'], 5000);
        expect(json['uptime_seconds'], 3665);
      });

      test('preserves empty strings in JSON', () {
        final status = Status(
          status: '',
          version: '',
          directoriesCount: 0,
          host: '',
          port: 0,
          uptimeSeconds: 0,
        );

        final json = status.toJson();

        expect(json['status'], '');
        expect(json['version'], '');
        expect(json['directories_count'], 0);
        expect(json['host'], '');
        expect(json['port'], 0);
        expect(json['uptime_seconds'], 0);
      });

      test('preserves zero values in JSON', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 0,
          host: 'localhost',
          port: 0,
          uptimeSeconds: 0,
        );

        final json = status.toJson();

        expect(json['directories_count'], 0);
        expect(json['port'], 0);
        expect(json['uptime_seconds'], 0);
      });
    });

    group('JSON Round Trip', () {
      test('fromJson and toJson are inverses', () {
        final originalJson = {
          'status': 'running',
          'version': '1.2.3',
          'directories_count': 5,
          'host': 'localhost',
          'port': 5000,
          'uptime_seconds': 3665,
        };

        final status = Status.fromJson(originalJson);
        final resultJson = status.toJson();

        expect(resultJson['status'], originalJson['status']);
        expect(resultJson['version'], originalJson['version']);
        expect(
          resultJson['directories_count'],
          originalJson['directories_count'],
        );
        expect(resultJson['host'], originalJson['host']);
        expect(resultJson['port'], originalJson['port']);
        expect(resultJson['uptime_seconds'], originalJson['uptime_seconds']);
      });
    });

    group('isRunning', () {
      test('returns true when status is "running"', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 100,
        );

        expect(status.isRunning, true);
      });

      test('returns false when status is "stopped"', () {
        final status = Status(
          status: 'stopped',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 0,
        );

        expect(status.isRunning, false);
      });

      test('returns false when status is "error"', () {
        final status = Status(
          status: 'error',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 0,
        );

        expect(status.isRunning, false);
      });

      test('returns false when status is "unknown"', () {
        final status = Status(
          status: 'unknown',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 0,
        );

        expect(status.isRunning, false);
      });

      test('returns false when status is empty', () {
        final status = Status(
          status: '',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 0,
        );

        expect(status.isRunning, false);
      });

      test('is case-sensitive', () {
        final status = Status(
          status: 'Running', // Capital R
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 100,
        );

        expect(status.isRunning, false);
      });
    });

    group('uptimeFormatted', () {
      test('formats seconds only', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 5,
        );
        expect(status.uptimeFormatted, '5s');
      });

      test('formats 59 seconds', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 59,
        );
        expect(status.uptimeFormatted, '59s');
      });

      test('formats exactly 1 minute', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 60,
        );
        expect(status.uptimeFormatted, '1m 0s');
      });

      test('formats minutes and seconds', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 65,
        );
        expect(status.uptimeFormatted, '1m 5s');
      });

      test('formats 59 minutes 59 seconds', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 3599,
        );
        expect(status.uptimeFormatted, '59m 59s');
      });

      test('formats exactly 1 hour', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 3600,
        );
        expect(status.uptimeFormatted, '1h 0m 0s');
      });

      test('formats hours, minutes, and seconds', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 3665,
        );
        expect(status.uptimeFormatted, '1h 1m 5s');
      });

      test('formats 23 hours 59 minutes 59 seconds', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 86399,
        );
        expect(status.uptimeFormatted, '23h 59m 59s');
      });

      test('formats exactly 1 day', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 86400,
        );
        expect(status.uptimeFormatted, '1d 0h 0m');
      });

      test('formats days, hours, and minutes', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 90061,
        );
        expect(status.uptimeFormatted, '1d 1h 1m');
      });

      test('formats multiple days', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 172800,
        );
        expect(status.uptimeFormatted, '2d 0h 0m');
      });

      test('formats 7 days', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 604800,
        );
        expect(status.uptimeFormatted, '7d 0h 0m');
      });

      test('formats 30 days with hours and minutes', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 2595665, // 30 days + 1 hour + 1 minute + 5 seconds
        );
        expect(status.uptimeFormatted, '30d 1h 1m');
      });

      test('formats 365 days', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 31536000,
        );
        expect(status.uptimeFormatted, '365d 0h 0m');
      });

      test('formats zero seconds', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 0,
        );
        expect(status.uptimeFormatted, '0s');
      });

      test('omits seconds in day format', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 90065, // 1d 1h 1m 5s
        );
        expect(status.uptimeFormatted, '1d 1h 1m');
        expect(status.uptimeFormatted, isNot(contains('s')));
      });

      test('shows seconds in hour format', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 3665, // 1h 1m 5s
        );
        expect(status.uptimeFormatted, '1h 1m 5s');
        expect(status.uptimeFormatted, contains('5s'));
      });
    });

    group('Special Characters and Edge Cases', () {
      test('handles version with pre-release info', () {
        final status = Status(
          status: 'running',
          version: '1.2.3-beta.1',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 100,
        );

        expect(status.version, '1.2.3-beta.1');
      });

      test('handles version with build metadata', () {
        final status = Status(
          status: 'running',
          version: '1.2.3+build.456',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 100,
        );

        expect(status.version, '1.2.3+build.456');
      });

      test('handles hostname with special characters', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'my-server.local',
          port: 5000,
          uptimeSeconds: 100,
        );

        expect(status.host, 'my-server.local');
      });

      test('handles IPv6 address', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: '::1',
          port: 5000,
          uptimeSeconds: 100,
        );

        expect(status.host, '::1');
      });

      test('handles very large uptime', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 999999999,
        );

        expect(status.uptimeSeconds, 999999999);
        expect(status.uptimeFormatted, contains('d'));
      });

      test('handles large directory count', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: 1000,
          host: 'localhost',
          port: 5000,
          uptimeSeconds: 100,
        );

        expect(status.directoriesCount, 1000);
      });

      test('handles negative values', () {
        final status = Status(
          status: 'running',
          version: '1.0.0',
          directoriesCount: -1,
          host: 'localhost',
          port: -1,
          uptimeSeconds: -1,
        );

        expect(status.directoriesCount, -1);
        expect(status.port, -1);
        expect(status.uptimeSeconds, -1);
      });
    });

    group('Real-World Scenarios', () {
      test('creates status from typical API response', () {
        final json = {
          'status': 'running',
          'version': '0.9.0',
          'directories_count': 3,
          'host': 'pumaguard.local',
          'port': 5000,
          'uptime_seconds': 7200,
        };

        final status = Status.fromJson(json);

        expect(status.status, 'running');
        expect(status.isRunning, true);
        expect(status.version, '0.9.0');
        expect(status.directoriesCount, 3);
        expect(status.uptimeFormatted, '2h 0m 0s');
      });

      test('creates stopped status', () {
        final json = {
          'status': 'stopped',
          'version': '1.0.0',
          'directories_count': 0,
          'host': 'localhost',
          'port': 5000,
          'uptime_seconds': 0,
        };

        final status = Status.fromJson(json);

        expect(status.isRunning, false);
        expect(status.status, 'stopped');
        expect(status.uptimeFormatted, '0s');
      });

      test('creates status with long uptime', () {
        final json = {
          'status': 'running',
          'version': '1.0.0',
          'directories_count': 5,
          'host': '192.168.52.100',
          'port': 8080,
          'uptime_seconds': 2592000, // 30 days
        };

        final status = Status.fromJson(json);

        expect(status.isRunning, true);
        expect(status.uptimeFormatted, '30d 0h 0m');
      });

      test('creates status with custom port', () {
        final json = {
          'status': 'running',
          'version': '1.0.0',
          'directories_count': 2,
          'host': '0.0.0.0',
          'port': 8080,
          'uptime_seconds': 300,
        };

        final status = Status.fromJson(json);

        expect(status.port, 8080);
        expect(status.host, '0.0.0.0');
        expect(status.uptimeFormatted, '5m 0s');
      });

      test('creates status with mDNS hostname', () {
        final json = {
          'status': 'running',
          'version': '1.0.0',
          'directories_count': 1,
          'host': 'pumaguard.local',
          'port': 5000,
          'uptime_seconds': 86400,
        };

        final status = Status.fromJson(json);

        expect(status.host, 'pumaguard.local');
        expect(status.uptimeFormatted, '1d 0h 0m');
      });
    });
  });
}
