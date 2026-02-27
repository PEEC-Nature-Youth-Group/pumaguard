import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/foundation.dart' show kIsWeb, debugPrint;
import 'package:http/http.dart' as http;
import 'package:crypto/crypto.dart';
import '../models/status.dart';
import '../models/settings.dart';
import '../models/camera.dart';
import '../models/plug.dart';

class ApiService {
  String? _baseUrl;

  ApiService({String? baseUrl})
    : _baseUrl = baseUrl?.replaceAll(RegExp(r'/$'), '');

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
      final url = getApiUrl('/api/settings');
      final settingsJson = settings.toJson();
      final body = jsonEncode(settingsJson);

      debugPrint('[ApiService.updateSettings] URL: $url');
      debugPrint('[ApiService.updateSettings] Settings JSON: $settingsJson');
      debugPrint('[ApiService.updateSettings] Body length: ${body.length}');

      final response = await http.put(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: body,
      );

      debugPrint(
        '[ApiService.updateSettings] Response status: ${response.statusCode}',
      );
      debugPrint('[ApiService.updateSettings] Response body: ${response.body}');

      if (response.statusCode == 200) {
        debugPrint('[ApiService.updateSettings] Settings updated successfully');
        return true;
      } else {
        final error = jsonDecode(response.body);
        debugPrint('[ApiService.updateSettings] Error response: $error');
        throw Exception(error['error'] ?? 'Failed to update settings');
      }
    } catch (e) {
      debugPrint('[ApiService.updateSettings] Exception: $e');
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

  /// Get list of classification output directories
  Future<List<String>> getClassificationDirectories() async {
    try {
      final response = await http.get(
        Uri.parse(getApiUrl('/api/directories/classification')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final dirs = json['directories'] as List<dynamic>;
        return dirs.map((d) => d.toString()).toList();
      } else {
        throw Exception(
          'Failed to load classification directories: ${response.statusCode}',
        );
      }
    } catch (e) {
      throw Exception('Failed to load classification directories: $e');
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
    debugPrint('[ApiService.getFolderImages] START');
    debugPrint('[ApiService.getFolderImages] Input folderPath: $folderPath');

    try {
      // Don't encode absolute paths - Flask's <path:> converter handles them directly
      // Only encode individual path components if needed
      String pathForUrl;
      if (folderPath.startsWith('/') || folderPath.startsWith('\\')) {
        // Absolute path - remove leading slash since Flask's <path:> adds it back
        pathForUrl = folderPath.substring(1);
      } else {
        // Relative path - use as-is
        pathForUrl = folderPath;
      }
      debugPrint('[ApiService.getFolderImages] Path for URL: $pathForUrl');

      final url = getApiUrl('/api/folders/$pathForUrl/images');
      debugPrint('[ApiService.getFolderImages] Full URL: $url');

      final response = await http.get(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );

      debugPrint(
        '[ApiService.getFolderImages] Response status: ${response.statusCode}',
      );
      debugPrint(
        '[ApiService.getFolderImages] Response body length: ${response.body.length} chars',
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        debugPrint(
          '[ApiService.getFolderImages] SUCCESS - Images count: ${(json['images'] as List?)?.length ?? 0}',
        );
        return json;
      } else {
        debugPrint(
          '[ApiService.getFolderImages] ERROR - Status ${response.statusCode}',
        );
        debugPrint(
          '[ApiService.getFolderImages] ERROR - Body: ${response.body}',
        );
        throw Exception('Failed to load folder images: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('[ApiService.getFolderImages] EXCEPTION: $e');
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

  /// Delete a photo/image file
  Future<bool> deletePhoto(String filepath) async {
    try {
      final encodedPath = Uri.encodeComponent(filepath);
      final response = await http.delete(
        Uri.parse(getApiUrl('/api/photos/$encodedPath')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to delete photo');
      }
    } catch (e) {
      throw Exception('Failed to delete photo: $e');
    }
  }

  /// Test deterrent sound playback
  Future<bool> testSound() async {
    try {
      final response = await http.post(
        Uri.parse(getApiUrl('/api/settings/test-sound')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to test sound');
      }
    } catch (e) {
      throw Exception('Failed to test sound: $e');
    }
  }

  /// Stop currently playing sound
  Future<bool> stopSound() async {
    try {
      final response = await http.post(
        Uri.parse(getApiUrl('/api/settings/stop-sound')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to stop sound');
      }
    } catch (e) {
      throw Exception('Failed to stop sound: $e');
    }
  }

  /// Check if sound is currently playing
  Future<bool> getSoundStatus() async {
    try {
      final response = await http.get(
        Uri.parse(getApiUrl('/api/settings/sound-status')),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['playing'] ?? false;
      } else {
        return false;
      }
    } catch (e) {
      return false;
    }
  }

  /// Test detection - simulates a puma detection with sound and plug control
  Future<bool> testDetection() async {
    try {
      final response = await http.post(
        Uri.parse(getApiUrl('/api/settings/test-detection')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        return true;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to test detection');
      }
    } catch (e) {
      throw Exception('Failed to test detection: $e');
    }
  }

  /// Get list of available models with cache status
  /// [modelType] can be 'classifier' (*.h5 files) or 'yolo' (*.pt files)
  Future<List<Map<String, dynamic>>> getAvailableModels({
    String modelType = 'classifier',
  }) async {
    try {
      final response = await http.get(
        Uri.parse(getApiUrl('/api/models/available?type=$modelType')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final models = json['models'] as List<dynamic>;
        return models.map((m) => m as Map<String, dynamic>).toList();
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to get available models');
      }
    } catch (e) {
      throw Exception('Failed to get available models: $e');
    }
  }

  /// Get list of available sound files
  Future<List<Map<String, dynamic>>> getAvailableSounds() async {
    try {
      final response = await http.get(
        Uri.parse(getApiUrl('/api/sounds/available')),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final sounds = json['sounds'] as List<dynamic>;
        return sounds.map((s) => s as Map<String, dynamic>).toList();
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to get available sounds');
      }
    } catch (e) {
      throw Exception('Failed to get available sounds: $e');
    }
  }

  /// Upload a sound file
  Future<Map<String, dynamic>> uploadSound(
    String filePath,
    Uint8List fileBytes,
    String fileName,
  ) async {
    try {
      final uri = Uri.parse(getApiUrl('/api/sounds/upload'));
      debugPrint('[ApiService.uploadSound] URI: $uri');
      debugPrint('[ApiService.uploadSound] File name: $fileName');
      debugPrint(
        '[ApiService.uploadSound] File size: ${fileBytes.length} bytes',
      );

      final request = http.MultipartRequest('POST', uri);

      // Add the file to the request
      request.files.add(
        http.MultipartFile.fromBytes('file', fileBytes, filename: fileName),
      );

      debugPrint('[ApiService.uploadSound] Sending request...');
      final streamedResponse = await request.send();
      debugPrint(
        '[ApiService.uploadSound] Response status: ${streamedResponse.statusCode}',
      );

      final response = await http.Response.fromStream(streamedResponse);
      debugPrint('[ApiService.uploadSound] Response body: ${response.body}');

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return json;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to upload sound');
      }
    } catch (e) {
      debugPrint('[ApiService.uploadSound] Exception: $e');
      throw Exception('Failed to upload sound: $e');
    }
  }

  /// Get list of detected cameras
  Future<List<Camera>> getCameras() async {
    try {
      final url = getApiUrl('/api/dhcp/cameras');
      debugPrint('[ApiService.getCameras] Requesting URL: $url');

      final response = await http.get(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );

      debugPrint(
        '[ApiService.getCameras] Response status: ${response.statusCode}',
      );
      debugPrint('[ApiService.getCameras] Response body: ${response.body}');

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final camerasList = json['cameras'] as List? ?? [];
        final cameras = camerasList
            .map(
              (cameraJson) =>
                  Camera.fromJson(cameraJson as Map<String, dynamic>),
            )
            .toList();
        debugPrint('[ApiService.getCameras] Parsed ${cameras.length} cameras');
        return cameras;
      } else {
        final error = jsonDecode(response.body);
        debugPrint('[ApiService.getCameras] Error response: $error');
        throw Exception(error['error'] ?? 'Failed to get cameras');
      }
    } catch (e) {
      debugPrint('[ApiService.getCameras] Exception: $e');
      throw Exception('Failed to get cameras: $e');
    }
  }

  /// Delete a camera by MAC address
  Future<void> deleteCamera(String macAddress) async {
    try {
      final url = getApiUrl('/api/dhcp/cameras/$macAddress');
      debugPrint('[ApiService.deleteCamera] Requesting URL: $url');

      final response = await http.delete(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );

      debugPrint(
        '[ApiService.deleteCamera] Response status: ${response.statusCode}',
      );
      debugPrint('[ApiService.deleteCamera] Response body: ${response.body}');

      if (response.statusCode != 200) {
        final error = jsonDecode(response.body);
        debugPrint('[ApiService.deleteCamera] Error response: $error');
        throw Exception(error['error'] ?? 'Failed to delete camera');
      }
    } catch (e) {
      debugPrint('[ApiService.deleteCamera] Exception: $e');
      throw Exception('Failed to delete camera: $e');
    }
  }

  /// Get list of known plugs
  Future<List<Plug>> getPlugs() async {
    try {
      final url = getApiUrl('/api/dhcp/plugs');
      debugPrint('[ApiService.getPlugs] Requesting URL: $url');

      final response = await http.get(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );

      debugPrint(
        '[ApiService.getPlugs] Response status: ${response.statusCode}',
      );
      debugPrint('[ApiService.getPlugs] Response body: ${response.body}');

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final plugsList = json['plugs'] as List? ?? [];
        final plugs = plugsList
            .map((plugJson) => Plug.fromJson(plugJson as Map<String, dynamic>))
            .toList();
        debugPrint('[ApiService.getPlugs] Parsed ${plugs.length} plugs');
        return plugs;
      } else {
        final error = jsonDecode(response.body);
        debugPrint('[ApiService.getPlugs] Error response: $error');
        throw Exception(error['error'] ?? 'Failed to get plugs');
      }
    } catch (e) {
      debugPrint('[ApiService.getPlugs] Exception: $e');
      throw Exception('Failed to get plugs: $e');
    }
  }

  /// Delete a plug by MAC address
  Future<void> deletePlug(String macAddress) async {
    try {
      final url = getApiUrl('/api/dhcp/plugs/$macAddress');
      debugPrint('[ApiService.deletePlug] Requesting URL: $url');

      final response = await http.delete(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );

      debugPrint(
        '[ApiService.deletePlug] Response status: ${response.statusCode}',
      );
      debugPrint('[ApiService.deletePlug] Response body: ${response.body}');

      if (response.statusCode != 200) {
        final error = jsonDecode(response.body);
        debugPrint('[ApiService.deletePlug] Error response: $error');
        throw Exception(error['error'] ?? 'Failed to delete plug');
      }
    } catch (e) {
      debugPrint('[ApiService.deletePlug] Exception: $e');
      throw Exception('Failed to delete plug: $e');
    }
  }

  /// Set plug mode (on/off/automatic)
  Future<Map<String, dynamic>> setPlugMode(
    String macAddress,
    String mode,
  ) async {
    try {
      final url = getApiUrl('/api/dhcp/plugs/$macAddress/mode');
      debugPrint('[ApiService.setPlugMode] Requesting URL: $url');
      debugPrint('[ApiService.setPlugMode] Mode: $mode');

      final body = jsonEncode({'mode': mode});

      final response = await http.put(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: body,
      );

      debugPrint(
        '[ApiService.setPlugMode] Response status: ${response.statusCode}',
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        debugPrint('[ApiService.setPlugMode] Success');
        return json;
      } else {
        final error = jsonDecode(response.body);
        debugPrint('[ApiService.setPlugMode] Error response: $error');
        throw Exception(error['error'] ?? 'Failed to set plug mode');
      }
    } catch (e) {
      debugPrint('[ApiService.setPlugMode] Exception: $e');
      throw Exception('Failed to set plug mode: $e');
    }
  }

  /// Get plug mode
  Future<String> getPlugMode(String macAddress) async {
    try {
      final url = getApiUrl('/api/dhcp/plugs/$macAddress/mode');
      debugPrint('[ApiService.getPlugMode] Requesting URL: $url');

      final response = await http.get(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );

      debugPrint(
        '[ApiService.getPlugMode] Response status: ${response.statusCode}',
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final mode = json['mode'] as String? ?? 'automatic';
        debugPrint('[ApiService.getPlugMode] Mode: $mode');
        return mode;
      } else {
        final error = jsonDecode(response.body);
        debugPrint('[ApiService.getPlugMode] Error response: $error');
        throw Exception(error['error'] ?? 'Failed to get plug mode');
      }
    } catch (e) {
      debugPrint('[ApiService.getPlugMode] Exception: $e');
      throw Exception('Failed to get plug mode: $e');
    }
  }

  /// Get Shelly plug real-time status
  Future<Plug> getShellyStatus(String macAddress) async {
    try {
      final url = getApiUrl('/api/dhcp/plugs/$macAddress/shelly-status');
      debugPrint('[ApiService.getShellyStatus] Requesting URL: $url');

      final response = await http.get(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );

      debugPrint(
        '[ApiService.getShellyStatus] Response status: ${response.statusCode}',
      );
      debugPrint(
        '[ApiService.getShellyStatus] Response body: ${response.body}',
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        final plug = Plug.fromJson(json);
        debugPrint(
          '[ApiService.getShellyStatus] Parsed plug with output=${plug.output}, power=${plug.apower}W',
        );
        return plug;
      } else {
        final error = jsonDecode(response.body);
        debugPrint('[ApiService.getShellyStatus] Error response: $error');
        throw Exception(error['error'] ?? 'Failed to get Shelly status');
      }
    } catch (e) {
      debugPrint('[ApiService.getShellyStatus] Exception: $e');
      throw Exception('Failed to get Shelly status: $e');
    }
  }

  /// Scan for available WiFi networks
  Future<Map<String, dynamic>> scanWifiNetworks() async {
    try {
      final url = getApiUrl('/api/wifi/scan');
      debugPrint('[ApiService.scanWifiNetworks] Requesting URL: $url');

      final response = await http.get(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );

      debugPrint(
        '[ApiService.scanWifiNetworks] Response status: ${response.statusCode}',
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return json;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to scan WiFi networks');
      }
    } catch (e) {
      debugPrint('[ApiService.scanWifiNetworks] Exception: $e');
      throw Exception('Failed to scan WiFi networks: $e');
    }
  }

  /// Get current WiFi mode (ap or client)
  Future<Map<String, dynamic>> getWifiMode() async {
    try {
      final url = getApiUrl('/api/wifi/mode');
      debugPrint('[ApiService.getWifiMode] Requesting URL: $url');

      final response = await http.get(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
      );

      debugPrint(
        '[ApiService.getWifiMode] Response status: ${response.statusCode}',
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return json;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to get WiFi mode');
      }
    } catch (e) {
      debugPrint('[ApiService.getWifiMode] Exception: $e');
      throw Exception('Failed to get WiFi mode: $e');
    }
  }

  /// Set WiFi mode (ap or client)
  Future<Map<String, dynamic>> setWifiMode({
    required String mode,
    required String ssid,
    String? password,
  }) async {
    try {
      final url = getApiUrl('/api/wifi/mode');
      debugPrint('[ApiService.setWifiMode] Requesting URL: $url');
      debugPrint('[ApiService.setWifiMode] Mode: $mode, SSID: $ssid');

      final body = jsonEncode({
        'mode': mode,
        'ssid': ssid,
        if (password != null && password.isNotEmpty) 'password': password,
      });

      final response = await http.put(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: body,
      );

      debugPrint(
        '[ApiService.setWifiMode] Response status: ${response.statusCode}',
      );
      debugPrint('[ApiService.setWifiMode] Response body: ${response.body}');

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return json;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to set WiFi mode');
      }
    } catch (e) {
      debugPrint('[ApiService.setWifiMode] Exception: $e');
      throw Exception('Failed to set WiFi mode: $e');
    }
  }

  /// Forget a saved WiFi network
  Future<Map<String, dynamic>> forgetWifiNetwork(String ssid) async {
    try {
      final url = getApiUrl('/api/wifi/forget');
      debugPrint('[ApiService.forgetWifiNetwork] Requesting URL: $url');

      final body = jsonEncode({'ssid': ssid});

      final response = await http.post(
        Uri.parse(url),
        headers: {'Content-Type': 'application/json'},
        body: body,
      );

      debugPrint(
        '[ApiService.forgetWifiNetwork] Response status: ${response.statusCode}',
      );

      if (response.statusCode == 200) {
        final json = jsonDecode(response.body) as Map<String, dynamic>;
        return json;
      } else {
        final error = jsonDecode(response.body);
        throw Exception(error['error'] ?? 'Failed to forget WiFi network');
      }
    } catch (e) {
      debugPrint('[ApiService.forgetWifiNetwork] Exception: $e');
      throw Exception('Failed to forget WiFi network: $e');
    }
  }

  /// Get server time
  Future<Map<String, dynamic>> getServerTime() async {
    try {
      final url = getApiUrl('/api/system/time');
      final uri = Uri.parse(url);

      final response = await http.get(
        uri,
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        throw Exception(
          'Failed to get server time: ${response.statusCode} ${response.body}',
        );
      }
    } catch (e) {
      throw Exception('Failed to get server time: $e');
    }
  }

  /// Set server time using client's current time
  Future<Map<String, dynamic>> syncServerTime() async {
    // Get current device time as Unix timestamp
    final now = DateTime.now().toUtc();
    return setServerTime(timestamp: now.millisecondsSinceEpoch / 1000.0);
  }

  /// Set server time
  ///
  /// Either [timestamp] (Unix seconds) or [iso] (ISO 8601 string) must be provided
  Future<Map<String, dynamic>> setServerTime({
    double? timestamp,
    String? iso,
  }) async {
    try {
      final url = getApiUrl('/api/system/time');
      final uri = Uri.parse(url);

      final body = <String, dynamic>{};
      if (timestamp != null) {
        body['timestamp'] = timestamp;
      } else if (iso != null) {
        body['iso'] = iso;
      } else {
        throw Exception('Either timestamp or iso must be provided');
      }

      final response = await http.put(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: json.encode(body),
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        final errorBody = json.decode(response.body) as Map<String, dynamic>;
        throw Exception(errorBody['error'] ?? 'Failed to set server time');
      }
    } catch (e) {
      throw Exception('Failed to set server time: $e');
    }
  }

  /// Retrieve system journal logs.
  ///
  /// [scope] can be:
  ///   - `'unit'`: logs for the pumaguard systemd unit only
  ///     (`journalctl --unit pumaguard --lines all`)
  ///   - `'all'`: all system journal logs
  ///     (`journalctl --lines all`)
  Future<Map<String, dynamic>> getLogs({String scope = 'unit'}) async {
    try {
      final url = getApiUrl('/api/system/logs');
      final uri = Uri.parse(
        url,
      ).replace(queryParameters: {'scope': scope, 'lines': 'all'});

      final response = await http.get(
        uri,
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        return json.decode(response.body) as Map<String, dynamic>;
      } else {
        final errorBody = json.decode(response.body) as Map<String, dynamic>;
        throw Exception(
          errorBody['error'] ??
              'Failed to retrieve logs: ${response.statusCode}',
        );
      }
    } catch (e) {
      throw Exception('Failed to retrieve logs: $e');
    }
  }
}
