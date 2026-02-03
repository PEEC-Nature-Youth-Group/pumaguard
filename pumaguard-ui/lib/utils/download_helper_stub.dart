import 'dart:typed_data';

/// Stub implementation for non-web platforms
void downloadFilesWeb(Uint8List fileBytes, String filename) {
  throw UnsupportedError('downloadFilesWeb is only supported on web platforms');
}
