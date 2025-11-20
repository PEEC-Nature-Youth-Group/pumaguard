import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/status.dart';
import '../models/settings.dart';

class ApiService {
  final String baseUrl;

  ApiService({this.baseUrl = 'http://localhost:5000'});

  /// Get system status
  Future<Status> getStatus() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/api/status'),
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
        Uri.parse('$baseUrl/api/settings'),
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
        Uri.parse('$baseUrl/api/settings'),
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
        Uri.parse('$baseUrl/api/settings/save'),
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
        Uri.parse('$baseUrl/api/settings/load'),
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
        Uri.parse('$baseUrl/api/directories'),
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
        Uri.parse('$baseUrl/api/directories'),
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
        Uri.parse('$baseUrl/api/directories/$index'),
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
}
