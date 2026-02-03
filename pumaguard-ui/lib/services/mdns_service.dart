// Conditional export for mDNS service based on platform
// Uses native implementation on mobile/desktop, stub on web

export 'mdns_service_web.dart' if (dart.library.io) 'mdns_service_io.dart';
