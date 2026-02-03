/// Platform-agnostic URL helper that provides the API base URL.
///
/// This file uses conditional exports to provide different implementations
/// for web and non-web platforms, avoiding the use of web-only APIs
/// in test environments.
library;

export 'platform_url_stub.dart'
    if (dart.library.html) 'platform_url_web.dart'
    if (dart.library.io) 'platform_url_stub.dart';
