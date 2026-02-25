import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/camera.dart';

/// Event types for camera and plug status changes
enum CameraEventType {
  connected,
  cameraConnected,
  cameraDisconnected,
  cameraAdded,
  cameraRemoved,
  cameraStatusChangedOnline,
  cameraStatusChangedOffline,
  plugConnected,
  plugDisconnected,
  plugAdded,
  plugRemoved,
  plugStatusChangedOnline,
  plugStatusChangedOffline,
  plugModeChanged,
  plugSwitchChanged,
  unknown,
}

/// Camera event data
class CameraEvent {
  final CameraEventType type;
  final Camera? camera;
  final String timestamp;

  CameraEvent({required this.type, required this.timestamp, this.camera});

  factory CameraEvent.fromJson(Map<String, dynamic> json) {
    final typeStr = json['type'] as String? ?? 'unknown';
    final type = _parseEventType(typeStr);

    Camera? camera;
    if (json['data'] != null && json['data'] is Map<String, dynamic>) {
      try {
        camera = Camera.fromJson(json['data'] as Map<String, dynamic>);
      } catch (e) {
        debugPrint('[CameraEvent] Error parsing camera data: $e');
      }
    }

    return CameraEvent(
      type: type,
      timestamp: json['timestamp'] as String? ?? '',
      camera: camera,
    );
  }

  static CameraEventType _parseEventType(String typeStr) {
    switch (typeStr) {
      case 'connected':
        return CameraEventType.connected;
      case 'camera_connected':
        return CameraEventType.cameraConnected;
      case 'camera_disconnected':
        return CameraEventType.cameraDisconnected;
      case 'camera_added':
        return CameraEventType.cameraAdded;
      case 'camera_removed':
        return CameraEventType.cameraRemoved;
      case 'camera_status_changed_online':
        return CameraEventType.cameraStatusChangedOnline;
      case 'camera_status_changed_offline':
        return CameraEventType.cameraStatusChangedOffline;
      case 'plug_connected':
        return CameraEventType.plugConnected;
      case 'plug_disconnected':
        return CameraEventType.plugDisconnected;
      case 'plug_added':
        return CameraEventType.plugAdded;
      case 'plug_removed':
        return CameraEventType.plugRemoved;
      case 'plug_status_changed_online':
        return CameraEventType.plugStatusChangedOnline;
      case 'plug_status_changed_offline':
        return CameraEventType.plugStatusChangedOffline;
      case 'plug_mode_changed':
        return CameraEventType.plugModeChanged;
      case 'plug_switch_changed':
        return CameraEventType.plugSwitchChanged;
      default:
        return CameraEventType.unknown;
    }
  }
}

/// Service for receiving real-time camera status updates via Server-Sent Events
class CameraEventsService {
  final String baseUrl;
  final _eventController = StreamController<CameraEvent>.broadcast();
  http.Client? _client;
  bool _isListening = false;

  /// When [_disposed] is true no further reconnect attempts are made.
  bool _disposed = false;

  CameraEventsService(this.baseUrl);

  /// Stream of camera events
  Stream<CameraEvent> get events => _eventController.stream;

  /// Whether the service is currently listening for events
  bool get isListening => _isListening;

  /// Start listening for camera events
  Future<void> startListening() async {
    if (_isListening || _disposed) {
      debugPrint(
        '[CameraEventsService] startListening called while '
        'isListening=$_isListening disposed=$_disposed – ignoring',
      );
      return;
    }

    _isListening = true;
    _client = http.Client();

    try {
      final url = Uri.parse('$baseUrl/api/dhcp/cameras/events');
      debugPrint('[CameraEventsService] Connecting to SSE: $url');

      final request = http.Request('GET', url);
      request.headers['Accept'] = 'text/event-stream';
      request.headers['Cache-Control'] = 'no-cache';

      final response = await _client!.send(request);

      if (response.statusCode != 200) {
        debugPrint(
          '[CameraEventsService] Failed to connect: ${response.statusCode}',
        );
        _isListening = false;
        _scheduleReconnect();
        return;
      }

      debugPrint('[CameraEventsService] Connected successfully');

      // Listen to the stream
      response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen(
            _handleLine,
            onError: (error) {
              debugPrint('[CameraEventsService] Stream error: $error');
              _handleDisconnect();
            },
            onDone: () {
              debugPrint('[CameraEventsService] Stream closed');
              _handleDisconnect();
            },
            cancelOnError: false,
          );
    } catch (e) {
      debugPrint('[CameraEventsService] Connection error: $e');
      _isListening = false;
      _client?.close();
      _client = null;
      _scheduleReconnect();
    }
  }

  /// Stop listening for camera events
  void stopListening() {
    if (!_isListening) {
      return;
    }

    debugPrint('[CameraEventsService] Stopping event listener');
    _isListening = false;
    _client?.close();
    _client = null;
  }

  /// Handle incoming SSE line
  void _handleLine(String line) {
    if (line.isEmpty || line.startsWith(':')) {
      // Skip empty lines and comments (keepalive)
      return;
    }

    if (line.startsWith('data: ')) {
      final data = line.substring(6); // Remove 'data: ' prefix
      try {
        final json = jsonDecode(data) as Map<String, dynamic>;
        final event = CameraEvent.fromJson(json);

        debugPrint(
          '[CameraEventsService] Received event: ${event.type} - ${event.camera?.hostname ?? "N/A"}',
        );

        _eventController.add(event);
      } catch (e) {
        debugPrint('[CameraEventsService] Error parsing event: $e');
      }
    }
  }

  /// Handle disconnection
  void _handleDisconnect() {
    if (!_isListening) {
      return;
    }

    _isListening = false;
    _client?.close();
    _client = null;

    _scheduleReconnect();
  }

  /// Schedule a reconnect attempt after a short delay, unless disposed.
  void _scheduleReconnect() {
    if (_disposed) {
      return;
    }

    debugPrint('[CameraEventsService] Attempting to reconnect in 5 seconds');
    Future.delayed(const Duration(seconds: 5), () {
      if (!_disposed && !_isListening) {
        startListening();
      }
    });
  }

  /// Release all resources. After calling [dispose] this instance must not
  /// be used again.
  void dispose() {
    _disposed = true;
    stopListening();
    _eventController.close();
  }
}
