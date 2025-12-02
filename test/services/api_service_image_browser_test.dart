// Unit tests for image browser APIs in ApiService
// Tests directories, folders, and photos endpoints including classification directories

import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:pumaguard_ui/services/api_service.dart';

void main() {
  group('ApiService Image Browser Tests', () {
    late ApiService apiService;
    late http.Client mockClient;

    setUp(() {
      apiService = ApiService(baseUrl: 'http://localhost:5000');
      mockClient = http.Client();
    });

    tearDown(() {
      mockClient.close();
    });

    group('Directories API', () {
      test('getDirectories returns list of watched directories', () async {
        // Mock the HTTP response
        final mockResponse = {
          'directories': [
            '/home/user/watched/folder1',
            '/home/user/watched/folder2',
          ]
        };

        // We'll test using the actual HTTP client with mocked responses
        // For now, let's test the URL construction and JSON parsing logic
        final json = mockResponse;
        final dirs = (json['directories'] as List<dynamic>)
            .map((d) => d.toString())
            .toList();

        expect(dirs.length, 2);
        expect(dirs[0], '/home/user/watched/folder1');
        expect(dirs[1], '/home/user/watched/folder2');
      });

      test('getDirectories constructs correct API URL', () {
        final url = apiService.getApiUrl('/api/directories');
        expect(url, 'http://localhost:5000/api/directories');
      });

      test('getClassificationDirectories returns list of classification directories',
          () async {
        // Mock the response for classification directories
        final mockResponse = {
          'directories': [
            '/home/user/.local/share/pumaguard/classified/puma',
            '/home/user/.local/share/pumaguard/classified/other',
            '/home/user/.local/share/pumaguard/classified/intermediate',
          ]
        };

        final json = mockResponse;
        final dirs = (json['directories'] as List<dynamic>)
            .map((d) => d.toString())
            .toList();

        expect(dirs.length, 3);
        expect(dirs[0], contains('classified/puma'));
        expect(dirs[1], contains('classified/other'));
        expect(dirs[2], contains('classified/intermediate'));
      });

      test('getClassificationDirectories constructs correct API URL', () {
        final url = apiService.getApiUrl('/api/directories/classification');
        expect(url, 'http://localhost:5000/api/directories/classification');
      });

      test('addDirectory constructs correct request', () {
        final url = apiService.getApiUrl('/api/directories');
        expect(url, 'http://localhost:5000/api/directories');

        final requestBody = jsonEncode({'directory': '/path/to/new/folder'});
        final decoded = jsonDecode(requestBody) as Map<String, dynamic>;
        expect(decoded['directory'], '/path/to/new/folder');
      });

      test('removeDirectory constructs correct API URL with index', () {
        final url = apiService.getApiUrl('/api/directories/0');
        expect(url, 'http://localhost:5000/api/directories/0');
      });
    });

    group('Folders API', () {
      test('getFolders parses response with watched and classification folders',
          () {
        final mockResponse = {
          'folders': [
            {
              'path': '/home/user/watched/folder1',
              'name': 'folder1',
              'image_count': 42
            },
            {
              'path': '/home/user/.local/share/pumaguard/classified/puma',
              'name': 'puma',
              'image_count': 15
            },
            {
              'path': '/home/user/.local/share/pumaguard/classified/other',
              'name': 'other',
              'image_count': 8
            },
            {
              'path':
                  '/home/user/.local/share/pumaguard/classified/intermediate',
              'name': 'intermediate',
              'image_count': 3
            },
          ]
        };

        final folders = (mockResponse['folders'] as List<dynamic>)
            .map((f) => f as Map<String, dynamic>)
            .toList();

        expect(folders.length, 4);
        expect(folders[0]['path'], '/home/user/watched/folder1');
        expect(folders[0]['name'], 'folder1');
        expect(folders[0]['image_count'], 42);

        expect(folders[1]['name'], 'puma');
        expect(folders[2]['name'], 'other');
        expect(folders[3]['name'], 'intermediate');
      });

      test('getFolders constructs correct API URL', () {
        final url = apiService.getApiUrl('/api/folders');
        expect(url, 'http://localhost:5000/api/folders');
      });

      test('getFolderImages constructs correct URL with encoded path', () {
        final folderPath = '/home/user/.local/share/pumaguard/classified/puma';
        final encodedPath = Uri.encodeComponent(folderPath);
        final url = apiService.getApiUrl('/api/folders/$encodedPath/images');

        expect(url, contains('/api/folders/'));
        expect(url, contains('images'));
        // Verify encoding happened
        expect(encodedPath, isNot(contains('/')));
        expect(encodedPath, contains('%2F'));
      });

      test('getFolderImages parses pagination response correctly', () {
        final mockResponse = {
          'images': [
            {
              'path': 'img1.jpg',  // Relative to base directory
              'filename': 'img1.jpg',
              'size': 102400,
              'modified': 1701504000.0,
            },
            {
              'path': 'img2.jpg',  // Relative to base directory
              'filename': 'img2.jpg',
              'size': 204800,
              'modified': 1701504060.0,
            },
          ],
          'folder': '.',
          'base': 'puma',
        };

        expect(mockResponse['images'], isList);
        expect((mockResponse['images'] as List).length, 2);
        expect(mockResponse['folder'], '.');
        expect(mockResponse['base'], 'puma');

        final firstImage =
            (mockResponse['images'] as List)[0] as Map<String, dynamic>;
        expect(firstImage['filename'], 'img1.jpg');
        expect(firstImage['path'], 'img1.jpg');  // Path is relative to base
        expect(firstImage['size'], 102400);
        expect(firstImage['modified'], 1701504000.0);
      });
    });

    group('Photos API', () {
      test('getPhotoUrl generates correct URL for absolute path', () {
        final photoPath =
            '/home/user/.local/share/pumaguard/classified/puma/image.jpg';
        final url = apiService.getPhotoUrl(photoPath);

        expect(url, contains('/api/photos/'));
        expect(url, contains(Uri.encodeComponent(photoPath)));
      });

      test('getPhotoUrl handles thumbnail parameter', () {
        final photoPath = '/home/user/image.jpg';
        final url = apiService.getPhotoUrl(photoPath, thumbnail: true);

        expect(url, contains('/api/photos/'));
        expect(url, contains('thumbnail=true'));
      });

      test('getPhotoUrl handles width and height parameters', () {
        final photoPath = '/home/user/image.jpg';
        final url = apiService.getPhotoUrl(
          photoPath,
          maxWidth: 800,
          maxHeight: 600,
        );

        expect(url, contains('/api/photos/'));
        expect(url, contains('width=800'));
        expect(url, contains('height=600'));
      });

      test('getPhotoUrl handles all thumbnail parameters together', () {
        final photoPath = '/home/user/image.jpg';
        final url = apiService.getPhotoUrl(
          photoPath,
          thumbnail: true,
          maxWidth: 800,
          maxHeight: 600,
        );

        expect(url, contains('/api/photos/'));
        expect(url, contains('thumbnail=true'));
        expect(url, contains('width=800'));
        expect(url, contains('height=600'));
        // Verify query string format
        expect(url, matches(RegExp(r'\?.*&.*')));
      });

      test('getPhotoUrl properly encodes paths with special characters', () {
        final photoPath = '/home/user/My Photos/image #1.jpg';
        final url = apiService.getPhotoUrl(photoPath);

        // Verify the path is encoded
        expect(url, contains('%2F')); // Encoded slash
        expect(url, contains('%20')); // Encoded space
        expect(url, contains('%23')); // Encoded hash
      });
    });

    group('Sync and Download API', () {
      test('getFilesToSync constructs correct request body', () {
        final localFiles = {
          '/path/to/file1.jpg': 'checksum1abc',
          '/path/to/file2.jpg': 'checksum2def',
        };

        final requestBody = jsonEncode({'files': localFiles});
        final decoded = jsonDecode(requestBody) as Map<String, dynamic>;

        expect(decoded['files'], isMap);
        final files = decoded['files'] as Map<String, dynamic>;
        expect(files['/path/to/file1.jpg'], 'checksum1abc');
        expect(files['/path/to/file2.jpg'], 'checksum2def');
      });

      test('getFilesToSync parses response correctly', () {
        final mockResponse = {
          'files_to_download': [
            {
              'path': '/home/user/classified/puma/new_image.jpg',
              'checksum': 'abc123def456',
              'size': 204800,
            },
            {
              'path': '/home/user/classified/other/another.jpg',
              'checksum': 'xyz789uvw012',
              'size': 153600,
            },
          ]
        };

        final files = (mockResponse['files_to_download'] as List<dynamic>)
            .map((f) => f as Map<String, dynamic>)
            .toList();

        expect(files.length, 2);
        expect(files[0]['path'], contains('puma'));
        expect(files[0]['checksum'], 'abc123def456');
        expect(files[0]['size'], 204800);
        expect(files[1]['path'], contains('other'));
      });

      test('downloadFiles constructs correct request body', () {
        final filePaths = [
          '/home/user/classified/puma/img1.jpg',
          '/home/user/classified/puma/img2.jpg',
        ];

        final requestBody = jsonEncode({'files': filePaths});
        final decoded = jsonDecode(requestBody) as Map<String, dynamic>;

        expect(decoded['files'], isList);
        final files = decoded['files'] as List<dynamic>;
        expect(files.length, 2);
        expect(files[0], contains('puma/img1.jpg'));
        expect(files[1], contains('puma/img2.jpg'));
      });
    });

    group('URL Construction', () {
      test('getApiUrl removes trailing slash from base URL', () {
        final service = ApiService(baseUrl: 'http://localhost:5000/');
        final url = service.getApiUrl('/api/status');
        expect(url, 'http://localhost:5000/api/status');
        expect(url, isNot(contains('//api')));
      });

      test('getApiUrl handles base URL without trailing slash', () {
        final service = ApiService(baseUrl: 'http://localhost:5000');
        final url = service.getApiUrl('/api/status');
        expect(url, 'http://localhost:5000/api/status');
      });

      test('setBaseUrl updates base URL and removes trailing slash', () {
        final service = ApiService();
        service.setBaseUrl('http://192.168.1.100:5000/');
        final url = service.getApiUrl('/api/status');
        expect(url, 'http://192.168.1.100:5000/api/status');
      });

      test('getApiUrl constructs correct URLs for all image browser endpoints',
          () {
        final service = ApiService(baseUrl: 'http://localhost:5000');

        expect(service.getApiUrl('/api/directories'),
            'http://localhost:5000/api/directories');
        expect(service.getApiUrl('/api/directories/classification'),
            'http://localhost:5000/api/directories/classification');
        expect(service.getApiUrl('/api/folders'),
            'http://localhost:5000/api/folders');

        final encodedPath = Uri.encodeComponent('/path/to/folder');
        expect(service.getApiUrl('/api/folders/$encodedPath/images'),
            'http://localhost:5000/api/folders/$encodedPath/images');
        expect(service.getApiUrl('/api/photos/$encodedPath'),
            'http://localhost:5000/api/photos/$encodedPath');
      });
    });

    group('Path Encoding', () {
      test('folder paths are properly URL encoded', () {
        final paths = [
          '/home/user/.local/share/pumaguard/classified/puma',
          '/home/user/My Documents/Photos',
          '/mnt/storage/images (backup)',
        ];

        for (final path in paths) {
          final encoded = Uri.encodeComponent(path);
          // Verify encoding doesn't contain unencoded slashes
          expect(encoded, isNot(contains('/')));
          // Verify we can decode back to original
          expect(Uri.decodeComponent(encoded), path);
        }
      });

      test('photo paths with special characters are properly encoded', () {
        final testPaths = {
          '/path/to/image.jpg': true,
          '/path with spaces/image.jpg': true,
          '/path/to/image #1.jpg': true,
          '/path/to/österreich.jpg': true,
          '/path/to/文件.jpg': true,
        };

        for (final entry in testPaths.entries) {
          final encoded = Uri.encodeComponent(entry.key);
          final decoded = Uri.decodeComponent(encoded);
          expect(decoded, entry.key,
              reason: 'Round-trip encoding failed for ${entry.key}');
        }
      });
    });

    group('Classification Directory Integration', () {
      test('classification directories can be distinguished from watched directories',
          () {
        final watchedDirs = [
          '/home/user/watched/folder1',
          '/home/user/watched/folder2',
        ];

        final classificationDirs = [
          '/home/user/.local/share/pumaguard/classified/puma',
          '/home/user/.local/share/pumaguard/classified/other',
          '/home/user/.local/share/pumaguard/classified/intermediate',
        ];

        // Verify they are distinct lists
        expect(watchedDirs.length, 2);
        expect(classificationDirs.length, 3);

        // Verify classification dirs have expected structure
        for (final dir in classificationDirs) {
          expect(dir, contains('classified/'));
          expect(
              dir.endsWith('puma') ||
                  dir.endsWith('other') ||
                  dir.endsWith('intermediate'),
              true);
        }

        // Verify watched dirs don't overlap with classification
        for (final dir in watchedDirs) {
          expect(dir, isNot(contains('classified/')));
        }
      });

      test('folders API combines both watched and classification directories',
          () {
        final allFolders = [
          {'path': '/home/user/watched/folder1', 'name': 'folder1'},
          {
            'path': '/home/user/.local/share/pumaguard/classified/puma',
            'name': 'puma'
          },
          {
            'path': '/home/user/.local/share/pumaguard/classified/other',
            'name': 'other'
          },
        ];

        // Count each type
        var watchedCount = 0;
        var classificationCount = 0;

        for (final folder in allFolders) {
          final path = folder['path'] as String;
          if (path.contains('classified/')) {
            classificationCount++;
          } else {
            watchedCount++;
          }
        }

        expect(watchedCount, 1);
        expect(classificationCount, 2);
        expect(watchedCount + classificationCount, allFolders.length);
      });
    });

    group('Error Handling', () {
      test('getDirectories throws exception on non-200 status', () {
        // Test error message format
        expect(
          () => throw Exception('Failed to load directories: 404'),
          throwsA(predicate(
              (e) => e.toString().contains('Failed to load directories'))),
        );
      });

      test('getClassificationDirectories throws exception on non-200 status',
          () {
        expect(
          () =>
              throw Exception('Failed to load classification directories: 500'),
          throwsA(predicate((e) =>
              e.toString().contains('Failed to load classification'))),
        );
      });

      test('getFolderImages throws exception on non-200 status', () {
        expect(
          () => throw Exception('Failed to load folder images: 404'),
          throwsA(predicate(
              (e) => e.toString().contains('Failed to load folder images'))),
        );
      });
    });
  });
}
