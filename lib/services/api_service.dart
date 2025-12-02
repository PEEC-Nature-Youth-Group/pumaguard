import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;
import 'package:crypto/crypto.dart';
import '../models/status.dart';
import '../models/settings.dart';

class ApiService {
  String? _baseUrl;

  ApiService({String? baseUrl}) : _baseUrl = baseUrl;

  /// Update the base URL (useful when connecting to a discovered server)
  void setBaseUrl(String url) {
    _baseUrl = url.replaceAll(RegExp(r'/$'), ''); // Remove trailing slash
  }

  /// Get the appropriate API URL for the given endpoint
  /// On web, uses the browser's current origin (e.g., http://192.168.1.100:5000)
  /// On mobile/desktop, uses the configured baseUrl or localhost:5000 as fallback
  String getApiUrl(String endpoint) {
    // 1. If we are on the Web, use the browser's current location
    if (kIsWeb) {
      // Uri.base.origin gives you "http://192.168.1.55:5000" or whatever the current IP is
      // It includes the scheme (http/https) and the port if it's not 80/443.
      return '${Uri.base.origin}$endpoint';
    }
    // 2. If we are on Mobile/Desktop, use configured baseUrl or default to localhost
    else {
      final base = _baseUrl ?? 'http://localhost:5000';
      return '$base$endpoint';
    }
  }

  /// Get system status
  Future<Status> getStatus() async {
    try {
      final response = await http.get(
        Uri.parse(getApiUrl('/api/status')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return Status.fromJson(json);
      } else {
        throw Exception('Failed to load status: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to connect to PumaGuard server: $e');
    }
  }

  /// Get current settings
  Future<Settings> getSettings() async {
    try {
      final response = await http.get(
        Uri.parse(getApiUrl('/api/settings')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return Settings.fromJson(json);
      } else {
        throw Exception('Failed to load settings: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to load settings: $e');
    }
  }

  /// Update settings
  Future<bool> updateSettings(Settings settings) async {
    try {
      final response = await http.put(
        Uri.parse(getApiUrl('/api/settings')),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(settings.toJson()),
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to update settings');
      }
    } catch (e) {
      throw Exception('Failed to update settings: $e');
    }
  }

  /// Save settings to file
  Future<String> saveSettings({String? filepath}) async {
    try {
      final body = filepath != null ? jsonEncode({'filepath': filepath}) : '{}';
      final response = await http.post(
        Uri.parse(getApiUrl('/api/settings/save')),
        headers: {'Content-Type': 'application/json'},
        body: body,
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return json['filepath'] as String;
      } else {
        throw Exception('Failed to save settings: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to save settings: $e');
    }
  }

  /// Load settings from file
  Future<bool> loadSettings(String filepath) async {
    try {
      final response = await http.post(
        Uri.parse(getApiUrl('/api/settings/load')),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'filepath': filepath}),
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to load settings');
      }
    } catch (e) {
      throw Exception('Failed to load settings: $e');
    }
  }

  /// Get list of monitored directories
  Future<List<String>> getDirectories() async {
    try {
      final response = await http.get(
        Uri.parse(getApiUrl('/api/directories')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final dirs = json['directories'] as List<dynamic>;
        return dirs.map((d) => d.toString()).toList();
      } else {
        throw Exception('Failed to load directories: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to load directories: $e');
    }
  }

  /// Add a directory to monitor
  Future<List<String>> addDirectory(String directory) async {
    try {
      final response = await http.post(
        Uri.parse(getApiUrl('/api/directories')),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'directory': directory}),
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final dirs = json['directories'] as List<dynamic>;
        return dirs.map((d) => d.toString()).toList();
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to add directory');
      }
    } catch (e) {
      throw Exception('Failed to add directory: $e');
    }
  }

  /// Remove a directory from monitoring
  Future<List<String>> removeDirectory(int index) async {
    try {
      final response = await http.delete(
        Uri.parse(getApiUrl('/api/directories/$index')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final dirs = json['directories'] as List<dynamic>;
        return dirs.map((d) => d.toString()).toList();
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to remove directory');
      }
    } catch (e) {
      throw Exception('Failed to remove directory: $e');
    }
  }

  /// Get list of watched folders with image counts
  Future<List<Map<String, dynamic>>> getFolders() async {
    try {
      final response = await http.get(
        Uri.parse(getApiUrl('/api/folders')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final folders = json['folders'] as List<dynamic>;
        return folders.map((f) => f as Map<String, dynamic>).toList();
      } else {
        throw Exception('Failed to load folders: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to load folders: $e');
    }
  }

  /// Get list of images in a specific folder
  Future<Map<String, dynamic>> getFolderImages(String folderPath) async {
    try {
      // Encode the entire path as a single component (e.g., /path/to/folder -> %2Fpath%2Fto%2Ffolder)
      final encodedPath = Uri.encodeComponent(folderPath);
      final response = await http.get(
        Uri.parse(getApiUrl('/api/folders/$encodedPath/images')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return json;
      } else {
        throw Exception('Failed to load folder images: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to load folder images: $e');
    }
  }

  /// Calculate checksum for a file (client-side)
  String calculateChecksum(Uint8List bytes) {
    return sha256.convert(bytes).toString();
  }

  /// Compare local files with server and get list of files to download
  Future<List<Map<String, dynamic>>> getFilesToSync(
    Map<String, String> localFilesWithChecksums,
  ) async {
    try {
      final response = await http.post(
        Uri.parse(getApiUrl('/api/sync/checksums')),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'files': localFilesWithChecksums}),
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final files = json['files_to_download'] as List<dynamic>;
        return files.map((f) => f as Map<String, dynamic>).toList();
      } else {
        throw Exception('Failed to get sync info: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to get sync info: $e');
    }
  }

  /// Download multiple files as ZIP or single file
  Future<Uint8List> downloadFiles(List<String> filePaths) async {
    try {
      final response = await http.post(
        Uri.parse(getApiUrl('/api/sync/download')),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'files': filePaths}),
      );

      if (response.statusCode == 200) {
        return response.bodyBytes;
      } else {
        throw Exception('Failed to download files: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to download files: $e');
    }
  }

  /// Get URL for a specific photo/image
  /// If [thumbnail] is true, request a thumbnail version (if supported by backend)
  /// [maxWidth] and [maxHeight] can be used to request specific thumbnail dimensions
  String getPhotoUrl(
    String filepath, {
    bool thumbnail = false,
    int? maxWidth,
    int? maxHeight,
  }) {
    final encodedPath = Uri.encodeComponent(filepath);
    var url = getApiUrl('/api/photos/$encodedPath');

    // Add query parameters for thumbnail if requested
    // Note: Backend may not support these yet - they will be gracefully ignored
    if (thumbnail || maxWidth != null || maxHeight != null) {
      final queryParams = <String, String>{};
      if (thumbnail) queryParams['thumbnail'] = 'true';
      if (maxWidth != null) queryParams['width'] = maxWidth.toString();
      if (maxHeight != null) queryParams['height'] = maxHeight.toString();

      if (queryParams.isNotEmpty) {
        url +=
            '?${queryParams.entries.map((e) => '${e.key}=${e.value}').join('&')}';
      }
    }

    return url;
  }
}
