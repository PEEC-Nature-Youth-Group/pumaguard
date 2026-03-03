/// Non-web (VM / test) HTTP client factory.
///
/// Returns a standard [IOClient] which already delivers response bytes as a
/// true stream on all desktop, mobile, and server platforms.  SSE connections
/// work correctly out of the box with this client.
library;

import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';

/// Returns an [http.Client] appropriate for the current (non-web) platform.
///
/// Callers are responsible for closing the returned client when it is no
/// longer needed.
http.Client createStreamingHttpClient() => IOClient();
