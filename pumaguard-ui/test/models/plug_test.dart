// Unit tests for Plug model
// Tests JSON serialization, deserialization, and helper methods

import 'package:flutter_test/flutter_test.dart';
import 'package:pumaguard_ui/models/plug.dart';

void main() {
  group('Plug Model Tests', () {
    group('Constructor', () {
      test('creates Plug with all fields', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.hostname, 'TestPlug');
        expect(plug.ipAddress, '192.168.52.200');
        expect(plug.macAddress, 'aa:bb:cc:dd:ee:ff');
        expect(plug.lastSeen, '2024-01-15T10:30:00Z');
        expect(plug.status, 'connected');
        expect(plug.mode, 'off');
      });

      test('creates Plug with empty strings', () {
        final plug = Plug(
          hostname: '',
          ipAddress: '',
          macAddress: '',
          lastSeen: '',
          status: '',
          mode: '',
        );

        expect(plug.hostname, '');
        expect(plug.ipAddress, '');
        expect(plug.macAddress, '');
        expect(plug.lastSeen, '');
        expect(plug.status, '');
        expect(plug.mode, '');
      });
    });

    group('fromJson', () {
      test('parses complete JSON correctly', () {
        final json = {
          'hostname': 'KasaPlug1',
          'ip_address': '192.168.52.201',
          'mac_address': 'bb:cc:dd:ee:ff:01',
          'last_seen': '2024-01-15T10:30:00Z',
          'status': 'connected',
          'mode': 'automatic',
        };

        final plug = Plug.fromJson(json);

        expect(plug.hostname, 'KasaPlug1');
        expect(plug.ipAddress, '192.168.52.201');
        expect(plug.macAddress, 'bb:cc:dd:ee:ff:01');
        expect(plug.lastSeen, '2024-01-15T10:30:00Z');
        expect(plug.status, 'connected');
        expect(plug.mode, 'automatic');
      });

      test('handles null values with defaults', () {
        final json = {
          'hostname': null,
          'ip_address': null,
          'mac_address': null,
          'last_seen': null,
          'status': null,
          'mode': null,
        };

        final plug = Plug.fromJson(json);

        expect(plug.hostname, '');
        expect(plug.ipAddress, '');
        expect(plug.macAddress, '');
        expect(plug.lastSeen, '');
        expect(plug.status, 'unknown');
        expect(plug.mode, 'automatic');
      });

      test('handles missing fields with defaults', () {
        final json = <String, dynamic>{};

        final plug = Plug.fromJson(json);

        expect(plug.hostname, '');
        expect(plug.ipAddress, '');
        expect(plug.macAddress, '');
        expect(plug.lastSeen, '');
        expect(plug.status, 'unknown');
        expect(plug.mode, 'automatic');
      });

      test('handles partial JSON with some fields missing', () {
        final json = {
          'hostname': 'PartialPlug',
          'ip_address': '192.168.52.200',
        };

        final plug = Plug.fromJson(json);

        expect(plug.hostname, 'PartialPlug');
        expect(plug.ipAddress, '192.168.52.200');
        expect(plug.macAddress, '');
        expect(plug.lastSeen, '');
        expect(plug.status, 'unknown');
        expect(plug.mode, 'automatic');
      });
    });

    group('toJson', () {
      test('converts Plug to JSON correctly', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'on',
        );

        final json = plug.toJson();

        expect(json['hostname'], 'TestPlug');
        expect(json['ip_address'], '192.168.52.200');
        expect(json['mac_address'], 'aa:bb:cc:dd:ee:ff');
        expect(json['last_seen'], '2024-01-15T10:30:00Z');
        expect(json['status'], 'connected');
        expect(json['mode'], 'on');
      });

      test('preserves empty strings in JSON', () {
        final plug = Plug(
          hostname: '',
          ipAddress: '',
          macAddress: '',
          lastSeen: '',
          status: '',
          mode: '',
        );

        final json = plug.toJson();

        expect(json['hostname'], '');
        expect(json['ip_address'], '');
        expect(json['mac_address'], '');
        expect(json['last_seen'], '');
        expect(json['status'], '');
        expect(json['mode'], '');
      });
    });

    group('JSON Round Trip', () {
      test('fromJson and toJson are inverses', () {
        final originalJson = {
          'hostname': 'RoundTripPlug',
          'ip_address': '192.168.52.250',
          'mac_address': 'aa:bb:cc:dd:ee:99',
          'last_seen': '2024-01-15T12:00:00Z',
          'status': 'disconnected',
          'mode': 'automatic',
        };

        final plug = Plug.fromJson(originalJson);
        final resultJson = plug.toJson();

        expect(resultJson['hostname'], originalJson['hostname']);
        expect(resultJson['ip_address'], originalJson['ip_address']);
        expect(resultJson['mac_address'], originalJson['mac_address']);
        expect(resultJson['last_seen'], originalJson['last_seen']);
        expect(resultJson['status'], originalJson['status']);
        expect(resultJson['mode'], originalJson['mode']);
      });
    });

    group('isConnected', () {
      test('returns true when status is "connected"', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.isConnected, true);
      });

      test('returns false when status is "disconnected"', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'disconnected',
          mode: 'off',
        );

        expect(plug.isConnected, false);
      });

      test('returns false when status is "unknown"', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'unknown',
          mode: 'off',
        );

        expect(plug.isConnected, false);
      });

      test('returns false when status is empty', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: '',
          mode: 'off',
        );

        expect(plug.isConnected, false);
      });

      test('returns false when status is any other value', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'pending',
          mode: 'off',
        );

        expect(plug.isConnected, false);
      });

      test('is case-sensitive', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'Connected', // Capital C
          mode: 'off',
        );

        expect(plug.isConnected, false);
      });
    });

    group('displayName', () {
      test('returns hostname when hostname is not empty', () {
        final plug = Plug(
          hostname: 'MySmartPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.displayName, 'MySmartPlug');
      });

      test('returns IP address when hostname is empty', () {
        final plug = Plug(
          hostname: '',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.displayName, '192.168.52.200');
      });

      test('returns empty string when both hostname and IP are empty', () {
        final plug = Plug(
          hostname: '',
          ipAddress: '',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.displayName, '');
      });

      test('prefers hostname over IP address', () {
        final plug = Plug(
          hostname: 'PreferredName',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.displayName, 'PreferredName');
        expect(plug.displayName, isNot('192.168.52.200'));
      });
    });

    group('plugUrl', () {
      test('returns IP address', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.plugUrl, '192.168.52.200');
      });

      test('returns empty string when IP is empty', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.plugUrl, '');
      });

      test('handles IPv4 addresses', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '10.0.0.1',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.plugUrl, '10.0.0.1');
      });

      test('handles IPv6 addresses', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: 'fe80::1',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.plugUrl, 'fe80::1');
      });

      test('handles IP with port', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200:9999',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.plugUrl, '192.168.52.200:9999');
      });

      test('handles localhost', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: 'localhost',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.plugUrl, 'localhost');
      });
    });

    group('Special Characters and Edge Cases', () {
      test('handles hostname with spaces', () {
        final plug = Plug(
          hostname: 'My Smart Plug',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.hostname, 'My Smart Plug');
        expect(plug.displayName, 'My Smart Plug');
      });

      test('handles hostname with special characters', () {
        final plug = Plug(
          hostname: 'Plug-1_Test@Site#A',
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.hostname, 'Plug-1_Test@Site#A');
      });

      test('handles very long hostname', () {
        final longHostname = 'P' * 100;
        final plug = Plug(
          hostname: longHostname,
          ipAddress: '192.168.52.200',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.hostname, longHostname);
        expect(plug.displayName.length, 100);
      });

      test('handles MAC address with uppercase letters', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'AA:BB:CC:DD:EE:FF',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.macAddress, 'AA:BB:CC:DD:EE:FF');
      });

      test('handles MAC address without colons', () {
        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'aabbccddeeff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        expect(plug.macAddress, 'aabbccddeeff');
      });

      test('handles ISO8601 timestamp formats', () {
        final timestamps = [
          '2024-01-15T10:30:00Z',
          '2024-01-15T10:30:00.123Z',
          '2024-01-15T10:30:00+00:00',
          '2024-01-15T10:30:00-05:00',
        ];

        for (final timestamp in timestamps) {
          final plug = Plug(
            hostname: 'TestPlug',
            ipAddress: '192.168.52.200',
            macAddress: 'aa:bb:cc:dd:ee:ff',
            lastSeen: timestamp,
            status: 'connected',
            mode: 'off',
          );

          expect(plug.lastSeen, timestamp);
        }
      });
    });

    group('Real-World Scenarios', () {
      test('creates plug from typical API response', () {
        final json = {
          'hostname': 'KasaPlug',
          'ip_address': '192.168.52.201',
          'mac_address': 'bb:cc:dd:ee:ff:01',
          'last_seen': '2024-01-15T10:30:00Z',
          'status': 'connected',
          'mode': 'automatic',
        };

        final plug = Plug.fromJson(json);

        expect(plug.hostname, 'KasaPlug');
        expect(plug.isConnected, true);
        expect(plug.displayName, 'KasaPlug');
        expect(plug.plugUrl, '192.168.52.201');
        expect(plug.mode, 'automatic');
      });

      test('creates disconnected plug', () {
        final json = {
          'hostname': 'OldPlug',
          'ip_address': '192.168.52.250',
          'mac_address': 'ff:ff:ff:ff:ff:ff',
          'last_seen': '2024-01-14T08:00:00Z',
          'status': 'disconnected',
          'mode': 'off',
        };

        final plug = Plug.fromJson(json);

        expect(plug.isConnected, false);
        expect(plug.status, 'disconnected');
        expect(plug.mode, 'off');
      });

      test('creates plug with minimal information', () {
        final json = {
          'ip_address': '192.168.52.250',
          'mac_address': 'aa:bb:cc:dd:ee:99',
        };

        final plug = Plug.fromJson(json);

        expect(plug.displayName, '192.168.52.250');
        expect(plug.status, 'unknown');
        expect(plug.isConnected, false);
        expect(plug.mode, 'automatic');
      });
    });
  });
}
