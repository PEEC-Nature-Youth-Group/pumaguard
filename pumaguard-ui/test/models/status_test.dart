import 'package:flutter_test/flutter_test.dart';
import '../../lib/models/status.dart';

void main() {
  group('Status uptimeFormatted', () {
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
  });
}
