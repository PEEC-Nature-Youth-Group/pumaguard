// Unit tests for camera APIs in ApiService
// Tests camera data transformation and parsing logic

import 'package:flutter_test/flutter_test.dart';
import 'package:pumaguard_ui/services/api_service.dart';
import 'package:pumaguard_ui/models/camera.dart';

void main() {
  group('ApiService Camera Tests', () {
    late ApiService apiService;

    setUp(() {
      apiService = ApiService(baseUrl: 'http://localhost:5000');
    });

    group('API URL Construction', () {
      test('constructs correct camera list API URL', () {
        final url = apiService.getApiUrl('/api/dhcp/cameras');
        expect(url, 'http://localhost:5000/api/dhcp/cameras');
      });

      test('constructs correct camera detail API URL', () {
        final url = apiService.getApiUrl('/api/dhcp/cameras/aa:bb:cc:dd:ee:ff');
        expect(url, 'http://localhost:5000/api/dhcp/cameras/aa:bb:cc:dd:ee:ff');
      });

      test('handles base URL without trailing slash', () {
        final service = ApiService(baseUrl: 'http://example.com');
        final url = service.getApiUrl('/api/dhcp/cameras');
        expect(url, 'http://example.com/api/dhcp/cameras');
      });

      test('handles base URL with trailing slash', () {
        final service = ApiService(baseUrl: 'http://example.com/');
        final url = service.getApiUrl('/api/dhcp/cameras');
        expect(url, 'http://example.com/api/dhcp/cameras');
      });
    });

    group('Camera Response Parsing', () {
      test('parses empty camera list response', () {
        final mockResponse = {'cameras': [], 'count': 0};

        final camerasList = mockResponse['cameras'] as List;
        final cameras = camerasList
            .map((json) => Camera.fromJson(json as Map<String, dynamic>))
            .toList();

        expect(cameras, isEmpty);
        expect(cameras.length, 0);
      });

      test('parses single camera response', () {
        final mockResponse = {
          'cameras': [
            {
              'hostname': 'Microseven-Cam1',
              'ip_address': '192.168.52.101',
              'mac_address': 'aa:bb:cc:dd:ee:01',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'connected',
            },
          ],
          'count': 1,
        };

        final camerasList = mockResponse['cameras'] as List;
        final cameras = camerasList
            .map((json) => Camera.fromJson(json as Map<String, dynamic>))
            .toList();

        expect(cameras.length, 1);
        expect(cameras[0].hostname, 'Microseven-Cam1');
        expect(cameras[0].ipAddress, '192.168.52.101');
        expect(cameras[0].macAddress, 'aa:bb:cc:dd:ee:01');
        expect(cameras[0].status, 'connected');
        expect(cameras[0].isConnected, true);
      });

      test('parses multiple cameras response', () {
        final mockResponse = {
          'cameras': [
            {
              'hostname': 'Microseven-Cam1',
              'ip_address': '192.168.52.101',
              'mac_address': 'aa:bb:cc:dd:ee:01',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'connected',
            },
            {
              'hostname': 'Microseven-Cam2',
              'ip_address': '192.168.52.102',
              'mac_address': 'aa:bb:cc:dd:ee:02',
              'last_seen': '2024-01-15T10:35:00Z',
              'status': 'disconnected',
            },
          ],
          'count': 2,
        };

        final camerasList = mockResponse['cameras'] as List;
        final cameras = camerasList
            .map((json) => Camera.fromJson(json as Map<String, dynamic>))
            .toList();

        expect(cameras.length, 2);
        expect(cameras[0].hostname, 'Microseven-Cam1');
        expect(cameras[0].status, 'connected');
        expect(cameras[0].isConnected, true);

        expect(cameras[1].hostname, 'Microseven-Cam2');
        expect(cameras[1].status, 'disconnected');
        expect(cameras[1].isConnected, false);
      });

      test('handles camera with missing optional fields', () {
        final json = {
          'hostname': '',
          'ip_address': '192.168.52.100',
          'mac_address': 'aa:bb:cc:dd:ee:ff',
          'last_seen': '',
          'status': 'unknown',
        };

        final camera = Camera.fromJson(json);

        expect(camera.hostname, '');
        expect(camera.ipAddress, '192.168.52.100');
        expect(camera.macAddress, 'aa:bb:cc:dd:ee:ff');
        expect(camera.lastSeen, '');
        expect(camera.status, 'unknown');
        expect(camera.isConnected, false);
      });
    });

    group('Camera Model Integration', () {
      test('fromJson creates valid Camera object', () {
        final json = {
          'hostname': 'TestCamera',
          'ip_address': '192.168.52.100',
          'mac_address': 'aa:bb:cc:dd:ee:ff',
          'last_seen': '2024-01-15T10:30:00Z',
          'status': 'connected',
        };

        final camera = Camera.fromJson(json);

        expect(camera.hostname, 'TestCamera');
        expect(camera.ipAddress, '192.168.52.100');
        expect(camera.macAddress, 'aa:bb:cc:dd:ee:ff');
        expect(camera.lastSeen, '2024-01-15T10:30:00Z');
        expect(camera.status, 'connected');
      });

      test('toJson creates valid JSON object', () {
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

      test('isConnected returns true for connected status', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.isConnected, true);
      });

      test('isConnected returns false for disconnected status', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'disconnected',
        );

        expect(camera.isConnected, false);
      });

      test('isConnected returns false for unknown status', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'unknown',
        );

        expect(camera.isConnected, false);
      });

      test('displayName returns hostname when available', () {
        final camera = Camera(
          hostname: 'MyCoolCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.displayName, 'MyCoolCamera');
      });

      test('displayName returns IP when hostname is empty', () {
        final camera = Camera(
          hostname: '',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.displayName, '192.168.52.100');
      });

      test('cameraUrl returns IP address', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.cameraUrl, '192.168.52.100');
      });

      test('cameraUrl returns empty string when IP is empty', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.cameraUrl, '');
      });
    });

    group('Camera JSON Parsing Edge Cases', () {
      test('handles null hostname', () {
        final json = {
          'hostname': null,
          'ip_address': '192.168.52.100',
          'mac_address': 'aa:bb:cc:dd:ee:ff',
          'last_seen': '2024-01-15T10:30:00Z',
          'status': 'connected',
        };

        final camera = Camera.fromJson(json);
        expect(camera.hostname, '');
      });

      test('handles null ip_address', () {
        final json = {
          'hostname': 'TestCamera',
          'ip_address': null,
          'mac_address': 'aa:bb:cc:dd:ee:ff',
          'last_seen': '2024-01-15T10:30:00Z',
          'status': 'connected',
        };

        final camera = Camera.fromJson(json);
        expect(camera.ipAddress, '');
      });

      test('handles null mac_address', () {
        final json = {
          'hostname': 'TestCamera',
          'ip_address': '192.168.52.100',
          'mac_address': null,
          'last_seen': '2024-01-15T10:30:00Z',
          'status': 'connected',
        };

        final camera = Camera.fromJson(json);
        expect(camera.macAddress, '');
      });

      test('handles null last_seen', () {
        final json = {
          'hostname': 'TestCamera',
          'ip_address': '192.168.52.100',
          'mac_address': 'aa:bb:cc:dd:ee:ff',
          'last_seen': null,
          'status': 'connected',
        };

        final camera = Camera.fromJson(json);
        expect(camera.lastSeen, '');
      });

      test('handles null status with default', () {
        final json = {
          'hostname': 'TestCamera',
          'ip_address': '192.168.52.100',
          'mac_address': 'aa:bb:cc:dd:ee:ff',
          'last_seen': '2024-01-15T10:30:00Z',
          'status': null,
        };

        final camera = Camera.fromJson(json);
        expect(camera.status, 'unknown');
      });

      test('handles missing fields', () {
        final json = <String, dynamic>{};

        final camera = Camera.fromJson(json);
        expect(camera.hostname, '');
        expect(camera.ipAddress, '');
        expect(camera.macAddress, '');
        expect(camera.lastSeen, '');
        expect(camera.status, 'unknown');
      });
    });

    group('Multiple Cameras Scenarios', () {
      test('parses list with mixed connected and disconnected cameras', () {
        final mockResponse = {
          'cameras': [
            {
              'hostname': 'Camera1',
              'ip_address': '192.168.52.101',
              'mac_address': 'aa:bb:cc:dd:ee:01',
              'last_seen': '2024-01-15T10:00:00Z',
              'status': 'connected',
            },
            {
              'hostname': 'Camera2',
              'ip_address': '192.168.52.102',
              'mac_address': 'aa:bb:cc:dd:ee:02',
              'last_seen': '2024-01-15T09:55:00Z',
              'status': 'disconnected',
            },
            {
              'hostname': 'Camera3',
              'ip_address': '192.168.52.103',
              'mac_address': 'aa:bb:cc:dd:ee:03',
              'last_seen': '2024-01-15T10:05:00Z',
              'status': 'connected',
            },
          ],
          'count': 3,
        };

        final camerasList = mockResponse['cameras'] as List;
        final cameras = camerasList
            .map((json) => Camera.fromJson(json as Map<String, dynamic>))
            .toList();

        expect(cameras.length, 3);
        expect(cameras.where((c) => c.isConnected).length, 2);
        expect(cameras.where((c) => !c.isConnected).length, 1);
      });

      test('handles cameras with duplicate hostnames', () {
        final mockResponse = {
          'cameras': [
            {
              'hostname': 'Microseven',
              'ip_address': '192.168.52.101',
              'mac_address': 'aa:bb:cc:dd:ee:01',
              'last_seen': '2024-01-15T10:00:00Z',
              'status': 'connected',
            },
            {
              'hostname': 'Microseven',
              'ip_address': '192.168.52.102',
              'mac_address': 'aa:bb:cc:dd:ee:02',
              'last_seen': '2024-01-15T10:00:00Z',
              'status': 'connected',
            },
          ],
          'count': 2,
        };

        final camerasList = mockResponse['cameras'] as List;
        final cameras = camerasList
            .map((json) => Camera.fromJson(json as Map<String, dynamic>))
            .toList();

        expect(cameras.length, 2);
        expect(cameras[0].hostname, cameras[1].hostname);
        expect(cameras[0].macAddress, isNot(cameras[1].macAddress));
        expect(cameras[0].ipAddress, isNot(cameras[1].ipAddress));
      });

      test('handles cameras with special characters in hostname', () {
        final json = {
          'hostname': 'Camera-1_Test@Site#A',
          'ip_address': '192.168.52.100',
          'mac_address': 'aa:bb:cc:dd:ee:ff',
          'last_seen': '2024-01-15T10:30:00Z',
          'status': 'connected',
        };

        final camera = Camera.fromJson(json);
        expect(camera.hostname, 'Camera-1_Test@Site#A');
        expect(camera.displayName, 'Camera-1_Test@Site#A');
      });
    });

    group('Camera URL Construction', () {
      test('cameraUrl can be used to construct HTTP URL', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        final httpUrl = 'http://${camera.cameraUrl}';
        expect(httpUrl, 'http://192.168.52.100');
      });

      test('cameraUrl handles IPv6 addresses', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: 'fe80::1',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.cameraUrl, 'fe80::1');
      });

      test('cameraUrl handles IP with port', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100:8080',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        expect(camera.cameraUrl, '192.168.52.100:8080');
      });
    });

    group('Camera Equality and Identity', () {
      test('cameras with same MAC address are identifiable', () {
        final camera1 = Camera(
          hostname: 'Camera1',
          ipAddress: '192.168.52.101',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:00:00Z',
          status: 'connected',
        );

        final camera2 = Camera(
          hostname: 'Camera1',
          ipAddress: '192.168.52.102', // Different IP
          macAddress: 'aa:bb:cc:dd:ee:ff', // Same MAC
          lastSeen: '2024-01-15T10:05:00Z',
          status: 'connected',
        );

        expect(camera1.macAddress, camera2.macAddress);
      });

      test('cameras with different MAC addresses are distinguishable', () {
        final camera1 = Camera(
          hostname: 'Camera1',
          ipAddress: '192.168.52.101',
          macAddress: 'aa:bb:cc:dd:ee:01',
          lastSeen: '2024-01-15T10:00:00Z',
          status: 'connected',
        );

        final camera2 = Camera(
          hostname: 'Camera1',
          ipAddress: '192.168.52.101',
          macAddress: 'aa:bb:cc:dd:ee:02',
          lastSeen: '2024-01-15T10:00:00Z',
          status: 'connected',
        );

        expect(camera1.macAddress, isNot(camera2.macAddress));
      });
    });

    group('API Response Count Validation', () {
      test('count matches number of cameras in list', () {
        final mockResponse = {
          'cameras': [
            {
              'hostname': 'Camera1',
              'ip_address': '192.168.52.101',
              'mac_address': 'aa:bb:cc:dd:ee:01',
              'last_seen': '2024-01-15T10:00:00Z',
              'status': 'connected',
            },
            {
              'hostname': 'Camera2',
              'ip_address': '192.168.52.102',
              'mac_address': 'aa:bb:cc:dd:ee:02',
              'last_seen': '2024-01-15T10:00:00Z',
              'status': 'connected',
            },
          ],
          'count': 2,
        };

        final count = mockResponse['count'] as int;
        final cameras = mockResponse['cameras'] as List;

        expect(count, cameras.length);
      });

      test('handles empty cameras list with zero count', () {
        final mockResponse = {'cameras': [], 'count': 0};

        final count = mockResponse['count'] as int;
        final cameras = mockResponse['cameras'] as List;

        expect(count, 0);
        expect(cameras, isEmpty);
      });

      test('validates count matches camera list length', () {
        final mockResponse = {
          'cameras': [
            {
              'hostname': 'Camera1',
              'ip_address': '192.168.52.101',
              'mac_address': 'aa:bb:cc:dd:ee:01',
              'last_seen': '2024-01-15T10:00:00Z',
              'status': 'connected',
            },
            {
              'hostname': 'Camera2',
              'ip_address': '192.168.52.102',
              'mac_address': 'aa:bb:cc:dd:ee:02',
              'last_seen': '2024-01-15T10:05:00Z',
              'status': 'connected',
            },
            {
              'hostname': 'Camera3',
              'ip_address': '192.168.52.103',
              'mac_address': 'aa:bb:cc:dd:ee:03',
              'last_seen': '2024-01-15T10:10:00Z',
              'status': 'disconnected',
            },
          ],
          'count': 3,
        };

        final count = mockResponse['count'] as int;
        final camerasList = mockResponse['cameras'] as List;
        final cameras = camerasList
            .map((json) => Camera.fromJson(json as Map<String, dynamic>))
            .toList();

        expect(count, cameras.length);
        expect(cameras.length, 3);
      });
    });
  });
}
