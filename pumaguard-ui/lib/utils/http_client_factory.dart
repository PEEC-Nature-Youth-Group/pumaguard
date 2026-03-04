/// Platform-agnostic HTTP client factory.
///
/// Exports the correct [http.Client] factory function for the current
/// platform:
///
/// - **Web**: returns a [FetchClient] (from `package:fetch_client`), which
///   is backed by the browser's native `fetch()` API and delivers response
///   bytes as a true stream.  This is required for Server-Sent Events (SSE)
///   to work correctly in Chrome, Firefox, and Safari.  The default
///   [BrowserClient] uses `XMLHttpRequest`, which buffers the entire response
///   body and therefore prevents SSE chunks from being delivered until the
///   connection closes.
///
/// - **Non-web** (VM / tests): returns a standard [IOClient], which already
///   streams responses correctly on all desktop/mobile platforms.
library;

export 'http_client_factory_stub.dart'
    if (dart.library.js_interop) 'http_client_factory_web.dart';
