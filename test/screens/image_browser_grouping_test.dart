import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';

// Test helper to simulate the grouping logic
enum ImageGrouping { none, day, week }

List<Map<String, dynamic>> groupImages(
  List<Map<String, dynamic>> images,
  ImageGrouping grouping,
) {
  if (grouping == ImageGrouping.none) {
    return images;
  }

  // Group images by date
  final Map<String, List<Map<String, dynamic>>> grouped = {};

  for (final image in images) {
    final timestamp = image['modified'];
    if (timestamp == null) continue;

    // Handle both int and double (st_mtime is a float)
    final timestampInt = (timestamp is int)
        ? timestamp
        : (timestamp as num).round();
    final date = DateTime.fromMillisecondsSinceEpoch(timestampInt * 1000);
    String groupKey;

    if (grouping == ImageGrouping.day) {
      // Group by day
      groupKey = DateFormat('yyyy-MM-dd EEEE').format(date);
    } else {
      // Group by week
      final weekStart = date.subtract(Duration(days: date.weekday - 1));
      final weekEnd = weekStart.add(const Duration(days: 6));
      groupKey =
          '${DateFormat('MMM d').format(weekStart)} - ${DateFormat('MMM d, yyyy').format(weekEnd)}';
    }

    if (!grouped.containsKey(groupKey)) {
      grouped[groupKey] = [];
    }
    grouped[groupKey]!.add(image);
  }

  // Sort groups by date (most recent first)
  final sortedKeys = grouped.keys.toList()
    ..sort((a, b) {
      // Get the first image from each group to compare dates
      final aTimestamp = grouped[a]!.first['modified'];
      final aTimestampInt = (aTimestamp is int)
          ? aTimestamp
          : (aTimestamp as num).round();
      final aDate = DateTime.fromMillisecondsSinceEpoch(aTimestampInt * 1000);

      final bTimestamp = grouped[b]!.first['modified'];
      final bTimestampInt = (bTimestamp is int)
          ? bTimestamp
          : (bTimestamp as num).round();
      final bDate = DateTime.fromMillisecondsSinceEpoch(bTimestampInt * 1000);

      return bDate.compareTo(aDate); // Descending order
    });

  // Flatten the grouped images back into a list with headers
  final List<Map<String, dynamic>> result = [];
  for (final key in sortedKeys) {
    // Add a header item
    result.add({
      'is_header': true,
      'header_text': key,
      'image_count': grouped[key]!.length,
    });
    // Add all images in this group
    result.addAll(grouped[key]!);
  }

  return result;
}

void main() {
  group('Image Grouping Tests', () {
    late List<Map<String, dynamic>> sampleImages;

    setUp(() {
      // Create sample images with timestamps
      // Using specific dates for predictable testing
      sampleImages = [
        {
          'path': 'img1.jpg',
          'filename': 'img1.jpg',
          'modified':
              DateTime(2024, 1, 15, 10, 30).millisecondsSinceEpoch ~/
              1000, // Monday
          'size': 1024,
        },
        {
          'path': 'img2.jpg',
          'filename': 'img2.jpg',
          'modified':
              DateTime(2024, 1, 15, 14, 20).millisecondsSinceEpoch ~/
              1000, // Same day
          'size': 2048,
        },
        {
          'path': 'img3.jpg',
          'filename': 'img3.jpg',
          'modified':
              DateTime(2024, 1, 16, 9, 15).millisecondsSinceEpoch ~/
              1000, // Tuesday
          'size': 1536,
        },
        {
          'path': 'img4.jpg',
          'filename': 'img4.jpg',
          'modified':
              DateTime(2024, 1, 22, 11, 45).millisecondsSinceEpoch ~/
              1000, // Next week Monday
          'size': 3072,
        },
        {
          'path': 'img5.jpg',
          'filename': 'img5.jpg',
          'modified':
              DateTime(2024, 1, 23, 16, 0).millisecondsSinceEpoch ~/
              1000, // Next week Tuesday
          'size': 2560,
        },
      ];
    });

    test('No grouping returns images as-is', () {
      final result = groupImages(sampleImages, ImageGrouping.none);

      expect(result.length, equals(5));
      expect(result, equals(sampleImages));
      expect(result.where((img) => img['is_header'] == true).isEmpty, isTrue);
    });

    test('Group by day creates correct day headers', () {
      final result = groupImages(sampleImages, ImageGrouping.day);

      // Should have 4 groups (Jan 15, Jan 16, Jan 22, Jan 23) = 4 headers + 5 images = 9 items
      expect(result.length, equals(9));

      // Count headers
      final headers = result
          .where((item) => item['is_header'] == true)
          .toList();
      expect(headers.length, equals(4));

      // Verify first header (most recent date - Jan 23)
      expect(headers[0]['header_text'], contains('2024-01-23'));
      expect(headers[0]['image_count'], equals(1));

      // Verify second header (Jan 22)
      expect(headers[1]['header_text'], contains('2024-01-22'));
      expect(headers[1]['image_count'], equals(1));

      // Verify third header (Jan 16)
      expect(headers[2]['header_text'], contains('2024-01-16'));
      expect(headers[2]['image_count'], equals(1));

      // Verify fourth header (Jan 15 - has 2 images)
      expect(headers[3]['header_text'], contains('2024-01-15'));
      expect(headers[3]['image_count'], equals(2));
    });

    test('Group by day sorts most recent first', () {
      final result = groupImages(sampleImages, ImageGrouping.day);

      // Find all headers
      final headerIndices = <int>[];
      for (int i = 0; i < result.length; i++) {
        if (result[i]['is_header'] == true) {
          headerIndices.add(i);
        }
      }

      // Headers should be in descending order by date
      expect(headerIndices.length, equals(4));

      // Most recent should be first
      expect(result[headerIndices[0]]['header_text'], contains('2024-01-23'));
      expect(result[headerIndices[1]]['header_text'], contains('2024-01-22'));
      expect(result[headerIndices[2]]['header_text'], contains('2024-01-16'));
      expect(result[headerIndices[3]]['header_text'], contains('2024-01-15'));
    });

    test('Group by week creates correct week headers', () {
      final result = groupImages(sampleImages, ImageGrouping.week);

      // Should have 2 weeks = 2 headers + 5 images = 7 items
      expect(result.length, equals(7));

      // Count headers
      final headers = result
          .where((item) => item['is_header'] == true)
          .toList();
      expect(headers.length, equals(2));

      // Week 1: Jan 15-21 (Monday to Sunday) - contains Jan 15 and Jan 16
      // Week 2: Jan 22-28 (Monday to Sunday) - contains Jan 22 and Jan 23

      // First header should be the most recent week
      expect(headers[0]['header_text'], contains('Jan 22'));
      expect(headers[0]['header_text'], contains('Jan 28'));
      expect(headers[0]['image_count'], equals(2));

      // Second header should be the earlier week
      expect(headers[1]['header_text'], contains('Jan 15'));
      expect(headers[1]['header_text'], contains('Jan 21'));
      expect(headers[1]['image_count'], equals(3));
    });

    test('Group by week handles images in same week correctly', () {
      // Create images all in the same week
      final sameWeekImages = [
        {
          'path': 'mon.jpg',
          'filename': 'mon.jpg',
          'modified':
              DateTime(2024, 1, 15).millisecondsSinceEpoch ~/ 1000, // Monday
          'size': 1024,
        },
        {
          'path': 'wed.jpg',
          'filename': 'wed.jpg',
          'modified':
              DateTime(2024, 1, 17).millisecondsSinceEpoch ~/ 1000, // Wednesday
          'size': 1024,
        },
        {
          'path': 'sun.jpg',
          'filename': 'sun.jpg',
          'modified':
              DateTime(2024, 1, 21).millisecondsSinceEpoch ~/ 1000, // Sunday
          'size': 1024,
        },
      ];

      final result = groupImages(sameWeekImages, ImageGrouping.week);

      // Should have 1 header + 3 images = 4 items
      expect(result.length, equals(4));

      final headers = result
          .where((item) => item['is_header'] == true)
          .toList();
      expect(headers.length, equals(1));
      expect(headers[0]['image_count'], equals(3));
    });

    test('Images within group maintain original order', () {
      final result = groupImages(sampleImages, ImageGrouping.day);

      // Find the Jan 15 group (should have 2 images)
      int headerIndex = -1;
      for (int i = 0; i < result.length; i++) {
        if (result[i]['is_header'] == true &&
            result[i]['header_text'].toString().contains('2024-01-15')) {
          headerIndex = i;
          break;
        }
      }

      expect(headerIndex, greaterThanOrEqualTo(0));

      // The two images after this header should be img1 and img2
      final firstImage = result[headerIndex + 1];
      final secondImage = result[headerIndex + 2];

      expect(firstImage['filename'], equals('img1.jpg'));
      expect(secondImage['filename'], equals('img2.jpg'));
    });

    test('Handles images without timestamps gracefully', () {
      final imagesWithNull = [
        {
          'path': 'img1.jpg',
          'filename': 'img1.jpg',
          'modified': DateTime(2024, 1, 15).millisecondsSinceEpoch ~/ 1000,
          'size': 1024,
        },
        {
          'path': 'img2.jpg',
          'filename': 'img2.jpg',
          'modified': null, // No timestamp
          'size': 2048,
        },
        {
          'path': 'img3.jpg',
          'filename': 'img3.jpg',
          'modified': DateTime(2024, 1, 16).millisecondsSinceEpoch ~/ 1000,
          'size': 1536,
        },
      ];

      final result = groupImages(imagesWithNull, ImageGrouping.day);

      // Should only group the images with valid timestamps (2 headers + 2 images)
      expect(result.length, equals(4));

      final headers = result
          .where((item) => item['is_header'] == true)
          .toList();
      expect(headers.length, equals(2));

      // Verify null timestamp image is not included
      final allImagePaths = result
          .where((item) => item['is_header'] != true)
          .map((item) => item['path'])
          .toList();
      expect(allImagePaths.contains('img2.jpg'), isFalse);
    });

    test('Empty image list returns empty result', () {
      final result = groupImages([], ImageGrouping.day);
      expect(result.isEmpty, isTrue);

      final resultWeek = groupImages([], ImageGrouping.week);
      expect(resultWeek.isEmpty, isTrue);
    });

    test('Single image creates single group', () {
      final singleImage = [
        {
          'path': 'single.jpg',
          'filename': 'single.jpg',
          'modified': DateTime(2024, 1, 15).millisecondsSinceEpoch ~/ 1000,
          'size': 1024,
        },
      ];

      final result = groupImages(singleImage, ImageGrouping.day);
      expect(result.length, equals(2)); // 1 header + 1 image

      final headers = result
          .where((item) => item['is_header'] == true)
          .toList();
      expect(headers.length, equals(1));
      expect(headers[0]['image_count'], equals(1));
    });

    test('Day grouping includes day of week in header', () {
      final result = groupImages(sampleImages, ImageGrouping.day);

      final headers = result
          .where((item) => item['is_header'] == true)
          .toList();

      // Jan 15, 2024 was a Monday
      final jan15Header = headers.firstWhere(
        (h) => h['header_text'].toString().contains('2024-01-15'),
      );
      expect(jan15Header['header_text'], contains('Monday'));

      // Jan 16, 2024 was a Tuesday
      final jan16Header = headers.firstWhere(
        (h) => h['header_text'].toString().contains('2024-01-16'),
      );
      expect(jan16Header['header_text'], contains('Tuesday'));
    });

    test('Week grouping handles year boundary correctly', () {
      final yearBoundaryImages = [
        {
          'path': 'dec31.jpg',
          'filename': 'dec31.jpg',
          'modified':
              DateTime(2023, 12, 31).millisecondsSinceEpoch ~/ 1000, // Sunday
          'size': 1024,
        },
        {
          'path': 'jan1.jpg',
          'filename': 'jan1.jpg',
          'modified':
              DateTime(2024, 1, 1).millisecondsSinceEpoch ~/ 1000, // Monday
          'size': 1024,
        },
      ];

      final result = groupImages(yearBoundaryImages, ImageGrouping.week);

      // These should be in different weeks
      final headers = result
          .where((item) => item['is_header'] == true)
          .toList();
      expect(headers.length, equals(2));
    });

    test('Groups are sorted with most recent first for both day and week', () {
      // Test with deliberately unsorted input
      final unsortedImages = [
        {
          'path': 'old.jpg',
          'filename': 'old.jpg',
          'modified': DateTime(2024, 1, 1).millisecondsSinceEpoch ~/ 1000,
          'size': 1024,
        },
        {
          'path': 'new.jpg',
          'filename': 'new.jpg',
          'modified': DateTime(2024, 1, 31).millisecondsSinceEpoch ~/ 1000,
          'size': 1024,
        },
        {
          'path': 'middle.jpg',
          'filename': 'middle.jpg',
          'modified': DateTime(2024, 1, 15).millisecondsSinceEpoch ~/ 1000,
          'size': 1024,
        },
      ];

      // Test day grouping
      final dayResult = groupImages(unsortedImages, ImageGrouping.day);
      final dayHeaders = dayResult
          .where((item) => item['is_header'] == true)
          .toList();

      expect(
        dayHeaders[0]['header_text'],
        contains('2024-01-31'),
      ); // Most recent
      expect(dayHeaders[1]['header_text'], contains('2024-01-15')); // Middle
      expect(dayHeaders[2]['header_text'], contains('2024-01-01')); // Oldest

      // Test week grouping
      final weekResult = groupImages(unsortedImages, ImageGrouping.week);
      final weekHeaders = weekResult
          .where((item) => item['is_header'] == true)
          .toList();

      // Should still be ordered most recent first
      expect(weekHeaders.length, greaterThan(0));

      // First header should contain the most recent date range
      final firstHeaderText = weekHeaders[0]['header_text'] as String;
      expect(firstHeaderText, contains('Jan'));
    });

    test('Handles float timestamps from backend (st_mtime)', () {
      // Backend returns st_mtime as float, not int
      final imagesWithFloatTimestamps = [
        {
          'path': 'img1.jpg',
          'filename': 'img1.jpg',
          'modified': 1705320600.5, // Float with fractional seconds
          'size': 1024,
        },
        {
          'path': 'img2.jpg',
          'filename': 'img2.jpg',
          'modified': 1705320650.123, // Float with more precision
          'size': 2048,
        },
        {
          'path': 'img3.jpg',
          'filename': 'img3.jpg',
          'modified': 1705407000.0, // Float that's a whole number
          'size': 1536,
        },
      ];

      // Should group successfully without errors
      final resultDay = groupImages(
        imagesWithFloatTimestamps,
        ImageGrouping.day,
      );
      expect(resultDay.length, greaterThan(0));

      final headersDay = resultDay
          .where((item) => item['is_header'] == true)
          .toList();
      expect(headersDay.length, greaterThan(0));

      // Should also work with week grouping
      final resultWeek = groupImages(
        imagesWithFloatTimestamps,
        ImageGrouping.week,
      );
      expect(resultWeek.length, greaterThan(0));

      final headersWeek = resultWeek
          .where((item) => item['is_header'] == true)
          .toList();
      expect(headersWeek.length, greaterThan(0));
    });

    test('Handles mixed int and float timestamps', () {
      final mixedImages = [
        {
          'path': 'int_timestamp.jpg',
          'filename': 'int_timestamp.jpg',
          'modified': 1705320600, // Integer timestamp
          'size': 1024,
        },
        {
          'path': 'float_timestamp.jpg',
          'filename': 'float_timestamp.jpg',
          'modified': 1705320650.5, // Float timestamp
          'size': 2048,
        },
      ];

      // Should handle both types without errors
      final result = groupImages(mixedImages, ImageGrouping.day);
      expect(result.length, greaterThan(0));

      // Both images should be included
      final images = result.where((item) => item['is_header'] != true).toList();
      expect(images.length, equals(2));
    });
  });
}
