// Unit tests for Camera model
// Tests JSON serialization, deserialization, and helper methods

import 'package:flutter_test/flutter_test.dart';
import 'package:pumaguard_ui/models/camera.dart';

void main() {
  group('Camera Model Tests', () {
    group('Constructor', () {
      test('creates Camera with all fields', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.hostname, 'TestCamera');
        expect(camera.ipAddress, '192.168.52.100');
        expect(camera.macAddress, 'aa:bb:cc:dd:ee:ff');
        expect(camera.lastSeen, '2024-01-15T10:30:00Z');
        expect(camera.status, 'connected');
      });

      test('creates Camera with empty strings', () {
        final camera = Camera(
          hostname: '',
          ipAddress: '',
          macAddress: '',
          lastSeen: '',
          status: '',
        );

        expect(camera.hostname, '');
        expect(camera.ipAddress, '');
        expect(camera.macAddress, '');
        expect(camera.lastSeen, '');
        expect(camera.status, '');
      });
    });

    group('fromJson', () {
      test('parses complete JSON correctly', () {
        final json = {
          'hostname': 'Microseven-Cam1',
          'ip_address': '192.168.52.101',
          'mac_address': 'aa:bb:cc:dd:ee:01',
          'last_seen': '2024-01-15T10:30:00Z',
          'status': 'connected',
        };

        final camera = Camera.fromJson(json);

        expect(camera.hostname, 'Microseven-Cam1');
        expect(camera.ipAddress, '192.168.52.101');
        expect(camera.macAddress, 'aa:bb:cc:dd:ee:01');
        expect(camera.lastSeen, '2024-01-15T10:30:00Z');
        expect(camera.status, 'connected');
      });

      test('handles null values with defaults', () {
        final json = {
          'hostname': null,
          'ip_address': null,
          'mac_address': null,
          'last_seen': null,
          'status': null,
        };

        final camera = Camera.fromJson(json);

        expect(camera.hostname, '');
        expect(camera.ipAddress, '');
        expect(camera.macAddress, '');
        expect(camera.lastSeen, '');
        expect(camera.status, 'unknown');
      });

      test('handles missing fields with defaults', () {
        final json = <String, dynamic>{};

        final camera = Camera.fromJson(json);

        expect(camera.hostname, '');
        expect(camera.ipAddress, '');
        expect(camera.macAddress, '');
        expect(camera.lastSeen, '');
        expect(camera.status, 'unknown');
      });

      test('handles partial JSON with some fields missing', () {
        final json = {
          'hostname': 'PartialCamera',
          'ip_address': '192.168.52.100',
        };

        final camera = Camera.fromJson(json);

        expect(camera.hostname, 'PartialCamera');
        expect(camera.ipAddress, '192.168.52.100');
        expect(camera.macAddress, '');
        expect(camera.lastSeen, '');
        expect(camera.status, 'unknown');
      });

      test('handles wrong type by converting to string', () {
        final json = {
          'hostname': 'TestCamera',
          'ip_address': '192.168.52.100',
          'mac_address': 'aa:bb:cc:dd:ee:ff',
          'last_seen': '2024-01-15T10:30:00Z',
          'status': 'connected',
        };

        final camera = Camera.fromJson(json);

        expect(camera.hostname, isA<String>());
        expect(camera.ipAddress, isA<String>());
        expect(camera.macAddress, isA<String>());
      });
    });

    group('toJson', () {
      test('converts Camera to JSON correctly', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        final json = camera.toJson();

        expect(json['hostname'], 'TestCamera');
        expect(json['ip_address'], '192.168.52.100');
        expect(json['mac_address'], 'aa:bb:cc:dd:ee:ff');
        expect(json['last_seen'], '2024-01-15T10:30:00Z');
        expect(json['status'], 'connected');
      });

      test('preserves empty strings in JSON', () {
        final camera = Camera(
          hostname: '',
          ipAddress: '',
          macAddress: '',
          lastSeen: '',
          status: '',
        );

        final json = camera.toJson();

        expect(json['hostname'], '');
        expect(json['ip_address'], '');
        expect(json['mac_address'], '');
        expect(json['last_seen'], '');
        expect(json['status'], '');
      });
    });

    group('JSON Round Trip', () {
      test('fromJson and toJson are inverses', () {
        final originalJson = {
          'hostname': 'RoundTripCamera',
          'ip_address': '192.168.52.150',
          'mac_address': 'aa:bb:cc:dd:ee:99',
          'last_seen': '2024-01-15T12:00:00Z',
          'status': 'disconnected',
        };

        final camera = Camera.fromJson(originalJson);
        final resultJson = camera.toJson();

        expect(resultJson['hostname'], originalJson['hostname']);
        expect(resultJson['ip_address'], originalJson['ip_address']);
        expect(resultJson['mac_address'], originalJson['mac_address']);
        expect(resultJson['last_seen'], originalJson['last_seen']);
        expect(resultJson['status'], originalJson['status']);
      });
    });

    group('isConnected', () {
      test('returns true when status is "connected"', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.isConnected, true);
      });

      test('returns false when status is "disconnected"', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'disconnected',
        );

        expect(camera.isConnected, false);
      });

      test('returns false when status is "unknown"', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'unknown',
        );

        expect(camera.isConnected, false);
      });

      test('returns false when status is empty', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: '',
        );

        expect(camera.isConnected, false);
      });

      test('returns false when status is any other value', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'pending',
        );

        expect(camera.isConnected, false);
      });

      test('is case-sensitive', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'Connected', // Capital C
        );

        expect(camera.isConnected, false);
      });
    });

    group('displayName', () {
      test('returns hostname when hostname is not empty', () {
        final camera = Camera(
          hostname: 'MyCoolCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.displayName, 'MyCoolCamera');
      });

      test('returns IP address when hostname is empty', () {
        final camera = Camera(
          hostname: '',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.displayName, '192.168.52.100');
      });

      test('returns empty string when both hostname and IP are empty', () {
        final camera = Camera(
          hostname: '',
          ipAddress: '',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.displayName, '');
      });

      test('prefers hostname over IP address', () {
        final camera = Camera(
          hostname: 'PreferredName',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.displayName, 'PreferredName');
        expect(camera.displayName, isNot('192.168.52.100'));
      });
    });

    group('cameraUrl', () {
      test('returns IP address', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.cameraUrl, '192.168.52.100');
      });

      test('returns empty string when IP is empty', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.cameraUrl, '');
      });

      test('handles IPv4 addresses', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '10.0.0.1',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.cameraUrl, '10.0.0.1');
      });

      test('handles IPv6 addresses', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: 'fe80::1',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.cameraUrl, 'fe80::1');
      });

      test('handles IP with port', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100:8080',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.cameraUrl, '192.168.52.100:8080');
      });

      test('handles localhost', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: 'localhost',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.cameraUrl, 'localhost');
      });
    });

    group('Special Characters and Edge Cases', () {
      test('handles hostname with spaces', () {
        final camera = Camera(
          hostname: 'My Test Camera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.hostname, 'My Test Camera');
        expect(camera.displayName, 'My Test Camera');
      });

      test('handles hostname with special characters', () {
        final camera = Camera(
          hostname: 'Camera-1_Test@Site#A',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.hostname, 'Camera-1_Test@Site#A');
      });

      test('handles very long hostname', () {
        final longHostname = 'A' * 100;
        final camera = Camera(
          hostname: longHostname,
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.hostname, longHostname);
        expect(camera.displayName.length, 100);
      });

      test('handles MAC address with uppercase letters', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'AA:BB:CC:DD:EE:FF',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.macAddress, 'AA:BB:CC:DD:EE:FF');
      });

      test('handles MAC address without colons', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aabbccddeeff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.macAddress, 'aabbccddeeff');
      });

      test('handles ISO8601 timestamp formats', () {
        final timestamps = [
          '2024-01-15T10:30:00Z',
          '2024-01-15T10:30:00.123Z',
          '2024-01-15T10:30:00+00:00',
          '2024-01-15T10:30:00-05:00',
        ];

        for (final timestamp in timestamps) {
          final camera = Camera(
            hostname: 'TestCamera',
            ipAddress: '192.168.52.100',
            macAddress: 'aa:bb:cc:dd:ee:ff',
            lastSeen: timestamp,
            status: 'connected',
          );

          expect(camera.lastSeen, timestamp);
        }
      });
    });

    group('Real-World Scenarios', () {
      test('creates camera from typical API response', () {
        final json = {
          'hostname': 'Microseven',
          'ip_address': '192.168.52.101',
          'mac_address': 'aa:bb:cc:dd:ee:01',
          'last_seen': '2024-01-15T10:30:00Z',
          'status': 'connected',
        };

        final camera = Camera.fromJson(json);

        expect(camera.hostname, 'Microseven');
        expect(camera.isConnected, true);
        expect(camera.displayName, 'Microseven');
        expect(camera.cameraUrl, '192.168.52.101');
      });

      test('creates disconnected camera', () {
        final json = {
          'hostname': 'OldCamera',
          'ip_address': '192.168.52.200',
          'mac_address': 'ff:ff:ff:ff:ff:ff',
          'last_seen': '2024-01-14T08:00:00Z',
          'status': 'disconnected',
        };

        final camera = Camera.fromJson(json);

        expect(camera.isConnected, false);
        expect(camera.status, 'disconnected');
      });

      test('creates camera with minimal information', () {
        final json = {
          'ip_address': '192.168.52.250',
          'mac_address': 'aa:bb:cc:dd:ee:99',
        };

        final camera = Camera.fromJson(json);

        expect(camera.displayName, '192.168.52.250');
        expect(camera.status, 'unknown');
        expect(camera.isConnected, false);
      });
    });
  });
}
