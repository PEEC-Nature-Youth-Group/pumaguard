import 'dart:js_interop';
import 'package:web/web.dart' as web;
import 'dart:typed_data';

/// Download files using web browser APIs
void downloadFilesWeb(Uint8List fileBytes, String filename) {
  final anchor = web.document.createElement('a') as web.HTMLAnchorElement;
  final blob = web.Blob([fileBytes.toJS].toJS);
  final url = web.URL.createObjectURL(blob);
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  web.URL.revokeObjectURL(url);
}
