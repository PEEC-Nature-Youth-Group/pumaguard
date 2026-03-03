/// Web HTTP client factory.
///
/// Returns a [FetchClient] backed by the browser's native `fetch()` API,
/// which delivers response bytes as a true stream.  This is required for
/// Server-Sent Events (SSE) to work correctly in Chrome, Firefox, and Safari.
///
/// The default [BrowserClient] (used by `http.Client()` on the web) is backed
/// by `XMLHttpRequest`, which buffers the entire response body before
/// delivering it.  That means SSE chunks are never delivered while the
/// connection is open – they all arrive at once when the server closes it,
/// which completely breaks real-time notifications.
library;

import 'package:fetch_client/fetch_client.dart';
import 'package:http/http.dart' as http;

/// Returns a [FetchClient] appropriate for web platforms.
///
/// Callers are responsible for closing the returned client when it is no
/// longer needed.
http.Client createStreamingHttpClient() => FetchClient(mode: RequestMode.cors);
