// Unit tests for ServiceStatus model
// Tests JSON serialization, deserialization, and helper getters.

import 'package:flutter_test/flutter_test.dart';
import 'package:pumaguard_ui/models/service_status.dart';

void main() {
  group('ServiceStatus Model Tests', () {
    group('Constructor', () {
      test('creates ServiceStatus with all fields', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );

        expect(service.name, 'hostapd');
        expect(service.active, true);
        expect(service.enabled, true);
        expect(service.state, 'active');
        expect(service.available, true);
      });

      test('creates ServiceStatus with false booleans', () {
        const service = ServiceStatus(
          name: 'dnsmasq',
          active: false,
          enabled: false,
          state: 'inactive',
          available: false,
        );

        expect(service.name, 'dnsmasq');
        expect(service.active, false);
        expect(service.enabled, false);
        expect(service.state, 'inactive');
        expect(service.available, false);
      });
    });

    group('fromJson', () {
      test('parses a complete active-service JSON correctly', () {
        final json = {
          'name': 'hostapd',
          'active': true,
          'enabled': true,
          'state': 'active',
          'available': true,
        };

        final service = ServiceStatus.fromJson(json);

        expect(service.name, 'hostapd');
        expect(service.active, true);
        expect(service.enabled, true);
        expect(service.state, 'active');
        expect(service.available, true);
      });

      test('parses a failed service JSON correctly', () {
        final json = {
          'name': 'dnsmasq',
          'active': false,
          'enabled': true,
          'state': 'failed',
          'available': true,
        };

        final service = ServiceStatus.fromJson(json);

        expect(service.name, 'dnsmasq');
        expect(service.active, false);
        expect(service.enabled, true);
        expect(service.state, 'failed');
        expect(service.available, true);
      });

      test('handles null values with defaults', () {
        final json = <String, dynamic>{
          'name': null,
          'active': null,
          'enabled': null,
          'state': null,
          'available': null,
        };

        final service = ServiceStatus.fromJson(json);

        expect(service.name, '');
        expect(service.active, false);
        expect(service.enabled, false);
        expect(service.state, 'unknown');
        expect(service.available, false);
      });

      test('handles missing fields with defaults', () {
        final json = <String, dynamic>{};

        final service = ServiceStatus.fromJson(json);

        expect(service.name, '');
        expect(service.active, false);
        expect(service.enabled, false);
        expect(service.state, 'unknown');
        expect(service.available, false);
      });

      test('handles partial JSON', () {
        final json = <String, dynamic>{'name': 'hostapd', 'active': true};

        final service = ServiceStatus.fromJson(json);

        expect(service.name, 'hostapd');
        expect(service.active, true);
        expect(service.enabled, false);
        expect(service.state, 'unknown');
        expect(service.available, false);
      });

      test('parses unavailable service (systemctl not installed)', () {
        final json = {
          'name': 'hostapd',
          'active': false,
          'enabled': false,
          'state': 'unavailable',
          'available': false,
        };

        final service = ServiceStatus.fromJson(json);

        expect(service.available, false);
        expect(service.state, 'unavailable');
      });

      test('parses timeout state', () {
        final json = {
          'name': 'dnsmasq',
          'active': false,
          'enabled': false,
          'state': 'timeout',
          'available': true,
        };

        final service = ServiceStatus.fromJson(json);

        expect(service.state, 'timeout');
        expect(service.available, true);
      });
    });

    group('toJson', () {
      test('serializes all fields correctly', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );

        final json = service.toJson();

        expect(json['name'], 'hostapd');
        expect(json['active'], true);
        expect(json['enabled'], true);
        expect(json['state'], 'active');
        expect(json['available'], true);
      });

      test('round-trip fromJson -> toJson preserves all fields', () {
        final original = {
          'name': 'dnsmasq',
          'active': false,
          'enabled': true,
          'state': 'failed',
          'available': true,
        };

        final json = ServiceStatus.fromJson(original).toJson();

        expect(json['name'], original['name']);
        expect(json['active'], original['active']);
        expect(json['enabled'], original['enabled']);
        expect(json['state'], original['state']);
        expect(json['available'], original['available']);
      });
    });

    group('stateLabel', () {
      test('returns "Running" for active state', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );
        expect(service.stateLabel, 'Running');
      });

      test('returns "Stopped" for inactive state', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: false,
          enabled: true,
          state: 'inactive',
          available: true,
        );
        expect(service.stateLabel, 'Stopped');
      });

      test('returns "Failed" for failed state', () {
        const service = ServiceStatus(
          name: 'dnsmasq',
          active: false,
          enabled: true,
          state: 'failed',
          available: true,
        );
        expect(service.stateLabel, 'Failed');
      });

      test('returns "Starting\u2026" for activating state', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: false,
          enabled: true,
          state: 'activating',
          available: true,
        );
        expect(service.stateLabel, 'Starting\u2026');
      });

      test('returns "Stopping\u2026" for deactivating state', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: false,
          enabled: true,
          state: 'deactivating',
          available: true,
        );
        expect(service.stateLabel, 'Stopping\u2026');
      });

      test('returns "Timeout" for timeout state', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: false,
          enabled: false,
          state: 'timeout',
          available: true,
        );
        expect(service.stateLabel, 'Timeout');
      });

      test('returns "Unavailable" for unavailable state', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: false,
          enabled: false,
          state: 'unavailable',
          available: false,
        );
        expect(service.stateLabel, 'Unavailable');
      });

      test('returns raw state string for unrecognised states', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: false,
          enabled: false,
          state: 'reloading',
          available: true,
        );
        expect(service.stateLabel, 'reloading');
      });

      test('returns "Unknown" for empty state string', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: false,
          enabled: false,
          state: '',
          available: true,
        );
        expect(service.stateLabel, 'Unknown');
      });
    });

    group('displayName', () {
      test('returns friendly name for hostapd', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );
        expect(service.displayName, 'Wi-Fi Access Point (hostapd)');
      });

      test('returns friendly name for dnsmasq', () {
        const service = ServiceStatus(
          name: 'dnsmasq',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );
        expect(service.displayName, 'DHCP / DNS (dnsmasq)');
      });

      test('returns raw name for unknown services', () {
        const service = ServiceStatus(
          name: 'some-other-service',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );
        expect(service.displayName, 'some-other-service');
      });
    });

    group('Equality and hashCode', () {
      test('two identical instances are equal', () {
        const a = ServiceStatus(
          name: 'hostapd',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );
        const b = ServiceStatus(
          name: 'hostapd',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );

        expect(a, equals(b));
        expect(a.hashCode, equals(b.hashCode));
      });

      test('instances differing in name are not equal', () {
        const a = ServiceStatus(
          name: 'hostapd',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );
        const b = ServiceStatus(
          name: 'dnsmasq',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );

        expect(a, isNot(equals(b)));
      });

      test('instances differing in active are not equal', () {
        const a = ServiceStatus(
          name: 'hostapd',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );
        const b = ServiceStatus(
          name: 'hostapd',
          active: false,
          enabled: true,
          state: 'active',
          available: true,
        );

        expect(a, isNot(equals(b)));
      });

      test('instances differing in state are not equal', () {
        const a = ServiceStatus(
          name: 'hostapd',
          active: false,
          enabled: true,
          state: 'inactive',
          available: true,
        );
        const b = ServiceStatus(
          name: 'hostapd',
          active: false,
          enabled: true,
          state: 'failed',
          available: true,
        );

        expect(a, isNot(equals(b)));
      });

      test('identical instance is equal to itself', () {
        const a = ServiceStatus(
          name: 'dnsmasq',
          active: true,
          enabled: true,
          state: 'active',
          available: true,
        );

        // ignore: unrelated_type_equality_checks
        expect(a == a, isTrue);
      });
    });

    group('toString', () {
      test('includes all field values', () {
        const service = ServiceStatus(
          name: 'hostapd',
          active: true,
          enabled: false,
          state: 'active',
          available: true,
        );

        final str = service.toString();

        expect(str, contains('hostapd'));
        expect(str, contains('true'));
        expect(str, contains('false'));
        expect(str, contains('active'));
      });
    });
  });
}
