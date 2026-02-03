/// Web-specific implementation for getting the API base URL.
///
/// This implementation uses package:web to access the browser's window.location
/// and construct the API base URL dynamically based on the current page URL.
library;

import 'package:web/web.dart' as web;

String getApiBaseUrl() {
  // Get the current window location to construct the API base URL
  // This allows the app to work when accessed from any host/port
  final window = web.window;
  final protocol = window.location.protocol; // 'http:' or 'https:'
  final host = window.location.host; // 'hostname:port' or just 'hostname'
  return '$protocol//$host';
}
