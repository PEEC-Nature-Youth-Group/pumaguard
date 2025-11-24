# Image Browser and Smart Sync Feature

## Overview

The Image Browser feature allows users to browse, select, and download images from watched folders through the PumaGuard web UI. It includes a smart sync mechanism similar to rsync that only downloads files that don't exist locally or have changed.

## Features

### 1. **Folder Browsing**
- View all watched folders with image counts
- Browse images in any watched folder
- Thumbnail grid view of all images
- Image metadata display (filename, size, modification date)

### 2. **Image Selection**
- Select individual images by clicking
- Select/Deselect all images with one click
- Visual indication of selected images
- Selection count in toolbar

### 3. **Smart Download (Rsync-like)**
- **Checksum comparison**: Only downloads files that are new or changed
- **Efficient transfers**: Skips files that already exist with matching checksums
- **Batch download**: Multiple files downloaded as ZIP archive
- **Single file mode**: Direct download for single file selection

### 4. **Cross-Platform Support**
- **Web**: Direct browser download using download API
- **Desktop/Mobile**: File picker for destination selection (planned)

## Architecture

### Backend (Python/Flask)

#### New API Endpoints

1. **GET `/api/folders`**
   - Returns list of watched folders with image counts
   - Response:
     ```json
     {
       "folders": [
         {
           "path": "/path/to/folder",
           "name": "folder_name",
           "image_count": 42
         }
       ]
     }
     ```

2. **GET `/api/folders/<folder_path>/images`**
   - Returns list of images in a specific folder
   - Response:
     ```json
     {
       "images": [
         {
           "filename": "image.jpg",
           "path": "/full/path/image.jpg",
           "size": 1024000,
           "modified": 1234567890.0,
           "created": 1234567890.0
         }
       ],
       "folder": "/path/to/folder"
     }
     ```

3. **POST `/api/sync/checksums`**
   - Compare client-side checksums with server-side
   - Request:
     ```json
     {
       "files": {
         "/path/to/file1.jpg": "abc123...",
         "/path/to/file2.jpg": "def456..."
       }
     }
     ```
   - Response:
     ```json
     {
       "files_to_download": [
         {
           "path": "/path/to/file1.jpg",
           "checksum": "xyz789...",
           "size": 1024000,
           "modified": 1234567890.0
         }
       ],
       "total": 1
     }
     ```

4. **POST `/api/sync/download`**
   - Download multiple files as ZIP or single file
   - Request:
     ```json
     {
       "files": [
         "/path/to/file1.jpg",
         "/path/to/file2.jpg"
       ]
     }
     ```
   - Response: Binary data (ZIP archive or single file)

#### Security Features

- **Path validation**: All file paths validated against allowed directories
- **Access control**: Only files in watched folders can be accessed
- **Path traversal protection**: Absolute path checking prevents directory traversal attacks

#### Implementation Details

```python
def _calculate_file_checksum(filepath: str) -> str:
    """Calculate SHA256 checksum efficiently for large files."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
```

### Frontend (Flutter)

#### New Screens

**`ImageBrowserScreen`**
- Two-panel layout:
  - Left panel: Folder list with image counts
  - Right panel: Image grid with selection
- Features:
  - Responsive grid layout
  - Image thumbnails loaded from server
  - Selection UI with checkboxes
  - Download button in app bar
  - Progress indicators

#### API Service Methods

```dart
// Get list of folders
Future<List<Map<String, dynamic>>> getFolders()

// Get images in a folder
Future<Map<String, dynamic>> getFolderImages(String folderPath)

// Calculate client-side checksum
String calculateChecksum(Uint8List bytes)

// Get list of files to sync
Future<List<Map<String, dynamic>>> getFilesToSync(
  Map<String, String> localFilesWithChecksums
)

// Download files
Future<Uint8List> downloadFiles(List<String> filePaths)

// Get photo URL
String getPhotoUrl(String filepath)
```

#### Dependencies

Added to `pubspec.yaml`:
- `crypto: ^3.0.3` - For SHA256 checksum calculation
- `file_picker: ^8.0.0+1` - For selecting download destination (native apps)

## Usage

### Accessing the Image Browser

1. Open PumaGuard web UI
2. Click on "Image Browser" in Quick Actions
3. Select a folder from the left sidebar
4. Images will load in the grid view

### Downloading Images

#### Web Browser

1. Select images by clicking on them
2. Click the download button (📥) in the app bar
3. Files will download automatically:
   - Single file: Direct download
   - Multiple files: ZIP archive

#### Desktop/Mobile (Future Enhancement)

1. Select images
2. Click download button
3. Choose destination folder
4. App will:
   - Check if files exist locally
   - Calculate checksums for existing files
   - Only download new or changed files
   - Show progress for sync operation

### Smart Sync Workflow

```
┌─────────────────────┐
│ User Selects Images │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────┐
│ Calculate Local Checksums   │
│ (Desktop/Mobile only)        │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ POST /api/sync/checksums    │
│ Send: {file: checksum}      │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Server Compares Checksums   │
│ Returns: Files to download  │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ POST /api/sync/download     │
│ Download only needed files  │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Save Files Locally          │
└─────────────────────────────┘
```

## Performance Considerations

### Backend

1. **Chunked reading**: Files read in 4KB chunks for checksum calculation
2. **Efficient ZIP creation**: In-memory ZIP for multiple files
3. **Path caching**: Folder scans cached (future enhancement)
4. **Concurrent checksum calculation**: Could parallelize for multiple files

### Frontend

1. **Lazy loading**: Images loaded on-demand as thumbnails
2. **Network caching**: Browser caches image thumbnails
3. **Efficient state management**: Only selected images tracked
4. **Responsive grid**: Adapts to screen size

## Security Considerations

### Path Traversal Prevention

```python
# Validate file is in allowed directory
abs_filepath = os.path.abspath(filepath)
allowed = False
for directory in self.image_directories:
    abs_directory = os.path.abspath(directory)
    if abs_filepath.startswith(abs_directory):
        allowed = True
        break

if not allowed:
    return jsonify({"error": "Access denied"}), 403
```

### Cross-Origin Resource Sharing (CORS)

- CORS configured to allow web UI access
- All endpoints protected by path validation
- No directory listing outside watched folders

## Future Enhancements

### 1. **Local Checksum Comparison** (Desktop/Mobile)
- Implement full rsync-like behavior
- Store local file database
- Background sync capability

### 2. **Thumbnail Optimization**
- Server-side thumbnail generation
- Reduced bandwidth for browsing
- Lazy loading with intersection observer

### 3. **Bulk Operations**
- Delete selected images
- Move images between folders
- Tag/categorize images

### 4. **Search and Filter**
- Search by filename
- Filter by date range
- Filter by file size
- Filter by classification result

### 5. **Preview Mode**
- Full-size image preview
- Image metadata overlay
- Classification results display
- Exif data viewing

### 6. **Download Progress**
- Real-time progress indicator
- Cancellable downloads
- Resume capability
- Speed/ETA display

### 7. **Background Sync**
- Automatic sync on schedule
- Watch for new images
- Notification on completion

## Testing

### Manual Testing

1. **Folder Listing**:
   ```bash
   curl http://localhost:5000/api/folders
   ```

2. **Folder Images**:
   ```bash
   curl http://localhost:5000/api/folders/%2Fpath%2Fto%2Ffolder/images
   ```

3. **Checksum Comparison**:
   ```bash
   curl -X POST http://localhost:5000/api/sync/checksums \
     -H "Content-Type: application/json" \
     -d '{"files": {"/path/to/file.jpg": "abc123"}}'
   ```

4. **Download Files**:
   ```bash
   curl -X POST http://localhost:5000/api/sync/download \
     -H "Content-Type: application/json" \
     -d '{"files": ["/path/to/file1.jpg", "/path/to/file2.jpg"]}' \
     -o download.zip
   ```

### Unit Tests (TODO)

- Test checksum calculation
- Test path validation
- Test ZIP creation
- Test checksum comparison logic
- Test download endpoint

### Integration Tests (TODO)

- End-to-end folder browsing
- End-to-end image selection and download
- Checksum comparison workflow
- Multi-file ZIP download

## Troubleshooting

### Images Not Loading

**Problem**: Thumbnails show broken image icon

**Solutions**:
- Check that files exist in watched folders
- Verify CORS is configured correctly
- Check browser console for network errors
- Ensure file extensions are supported (.jpg, .jpeg, .png, .gif, .bmp, .webp)

### Download Fails

**Problem**: Download button doesn't work or returns error

**Solutions**:
- Check that files are in allowed directories
- Verify sufficient disk space
- Check server logs for errors
- Ensure no file permission issues

### Slow Performance

**Problem**: Folder loading or image browsing is slow

**Solutions**:
- Reduce number of images in folders
- Check network bandwidth
- Enable thumbnail generation (future enhancement)
- Consider pagination for large folders

### Checksum Mismatch

**Problem**: Files re-download even though they exist locally

**Solutions**:
- Verify checksum algorithm matches (SHA256)
- Check for file corruption
- Ensure file paths are exact matches
- Verify file hasn't been modified locally

## Code Examples

### Backend: Adding Custom Metadata

```python
# In web_ui.py, extend image info
def get_folder_images(folder_path):
    # ... existing code ...
    for filename in os.listdir(abs_folder):
        # ... existing code ...
        images.append({
            'filename': filename,
            'path': filepath,
            'size': stat.st_size,
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            # Add custom metadata
            'classification': get_classification_result(filepath),
            'confidence': get_confidence_score(filepath),
        })
```

### Frontend: Custom Image Card

```dart
// In image_browser_screen.dart
Widget buildImageCard(Map<String, dynamic> image) {
  return Card(
    child: Column(
      children: [
        Image.network(apiService.getPhotoUrl(image['path'])),
        Text(image['filename']),
        // Add classification badge
        if (image['classification'] == 'lion')
          Chip(
            label: Text('🦁 Lion Detected'),
            backgroundColor: Colors.orange,
          ),
      ],
    ),
  );
}
```

## API Reference

See inline documentation in:
- Backend: `pumaguard/web_ui.py`
- Frontend: `pumaguard-ui/lib/services/api_service.dart`
- Screen: `pumaguard-ui/lib/screens/image_browser_screen.dart`

## Related Documentation

- [Web UI Documentation](../README.md#web-ui)
- [API Documentation](API.md)
- [XDG Configuration](XDG_MIGRATION.md)
- [Development Guide](../CONTRIBUTING.md)

## Changelog

### Version 1.0 (Initial Implementation)
- ✅ Folder browsing with image counts
- ✅ Image grid view with thumbnails
- ✅ Multi-select functionality
- ✅ Checksum-based sync API
- ✅ ZIP download for multiple files
- ✅ Web platform support
- ✅ Security: Path validation and access control

### Future Versions
- ⏳ Native app local checksum comparison
- ⏳ Server-side thumbnail generation
- ⏳ Advanced filtering and search
- ⏳ Image preview mode
- ⏳ Download progress tracking
- ⏳ Background sync capability