import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Event types for image change notifications
enum ImageEventType { connected, imageAdded, imageDeleted, unknown }

/// Image event data
class ImageEvent {
  final ImageEventType type;
  final Map<String, dynamic> data;
  final String timestamp;

  ImageEvent({required this.type, required this.data, required this.timestamp});

  factory ImageEvent.fromJson(Map<String, dynamic> json) {
    final typeStr = json['type'] as String? ?? 'unknown';
    final type = _parseEventType(typeStr);
    final data = (json['data'] as Map<String, dynamic>?) ?? <String, dynamic>{};
    final timestamp = json['timestamp'] as String? ?? '';

    return ImageEvent(type: type, data: data, timestamp: timestamp);
  }

  static ImageEventType _parseEventType(String typeStr) {
    switch (typeStr) {
      case 'connected':
        return ImageEventType.connected;
      case 'image_added':
        return ImageEventType.imageAdded;
      case 'image_deleted':
        return ImageEventType.imageDeleted;
      default:
        return ImageEventType.unknown;
    }
  }
}

/// Service for receiving real-time image change notifications via SSE.
///
/// Connects to the backend `/api/images/events` endpoint and re-emits
/// parsed [ImageEvent] objects on the [events] stream.  Automatically
/// reconnects with a 5-second delay if the connection is lost.
class ImageEventsService {
  final String baseUrl;

  final _eventController = StreamController<ImageEvent>.broadcast();
  http.Client? _client;
  bool _isListening = false;

  /// When [_disposed] is true no further reconnect attempts are made.
  bool _disposed = false;

  ImageEventsService(this.baseUrl);

  /// Broadcast stream of image events.
  Stream<ImageEvent> get events => _eventController.stream;

  /// Whether the service is currently connected and listening.
  bool get isListening => _isListening;

  /// Start listening for image events.
  ///
  /// Calling this while already listening is a no-op.
  Future<void> startListening() async {
    if (_isListening || _disposed) {
      debugPrint(
        '[ImageEventsService] startListening called while '
        'isListening=$_isListening disposed=$_disposed – ignoring',
      );
      return;
    }

    _isListening = true;
    _client = http.Client();

    try {
      final url = Uri.parse('$baseUrl/api/images/events');
      debugPrint('[ImageEventsService] Connecting to SSE: $url');

      final request = http.Request('GET', url);
      request.headers['Accept'] = 'text/event-stream';
      request.headers['Cache-Control'] = 'no-cache';

      final response = await _client!.send(request);

      if (response.statusCode != 200) {
        debugPrint(
          '[ImageEventsService] Failed to connect: ${response.statusCode}',
        );
        _isListening = false;
        _scheduleReconnect();
        return;
      }

      debugPrint('[ImageEventsService] Connected successfully');

      response.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter())
          .listen(
            _handleLine,
            onError: (Object error) {
              debugPrint('[ImageEventsService] Stream error: $error');
              _handleDisconnect();
            },
            onDone: () {
              debugPrint('[ImageEventsService] Stream closed');
              _handleDisconnect();
            },
            cancelOnError: false,
          );
    } catch (e) {
      debugPrint('[ImageEventsService] Connection error: $e');
      _isListening = false;
      _client?.close();
      _client = null;
      _scheduleReconnect();
    }
  }

  /// Stop listening for image events and cancel any pending reconnects.
  void stopListening() {
    if (!_isListening) {
      return;
    }

    debugPrint('[ImageEventsService] Stopping event listener');
    _isListening = false;
    _client?.close();
    _client = null;
  }

  /// Handle an incoming SSE line.
  void _handleLine(String line) {
    // Skip empty lines and SSE comments (keepalive markers such as
    // ": keepalive").
    if (line.isEmpty || line.startsWith(':')) {
      return;
    }

    if (line.startsWith('data: ')) {
      final data = line.substring(6); // Strip the 'data: ' prefix
      try {
        final json = jsonDecode(data) as Map<String, dynamic>;
        final event = ImageEvent.fromJson(json);

        debugPrint(
          '[ImageEventsService] Received event: ${event.type} '
          '– ${event.data}',
        );

        _eventController.add(event);
      } catch (e) {
        debugPrint('[ImageEventsService] Error parsing event: $e');
      }
    }
  }

  /// Handle an unexpected stream disconnection.
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

    debugPrint('[ImageEventsService] Attempting to reconnect in 5 seconds…');
    Future.delayed(const Duration(seconds: 5), () {
      if (!_disposed && !_isListening) {
        startListening();
      }
    });
  }

  /// Release all resources.  After calling [dispose] this instance must not
  /// be used again.
  void dispose() {
    _disposed = true;
    stopListening();
    _eventController.close();
  }
}
