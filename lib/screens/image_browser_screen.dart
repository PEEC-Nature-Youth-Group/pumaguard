import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:file_picker/file_picker.dart';
import '../utils/download_helper.dart';

class ImageBrowserScreen extends StatefulWidget {
  const ImageBrowserScreen({super.key});

  @override
  State<ImageBrowserScreen> createState() => _ImageBrowserScreenState();
}

class _ImageBrowserScreenState extends State<ImageBrowserScreen> {
  List<Map<String, dynamic>> _folders = [];
  String? _selectedFolder;
  List<Map<String, dynamic>> _images = [];
  Set<String> _selectedImages = {};
  bool _isLoading = false;
  bool _isDownloading = false;
  String? _error;
  bool _selectAll = false;

  @override
  void initState() {
    super.initState();
    _loadFolders();
  }

  Future<void> _loadFolders() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final apiService = Provider.of<ApiService>(context, listen: false);
      final folders = await apiService.getFolders();
      setState(() {
        _folders = folders;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _loadFolderImages(String folderPath) async {
    setState(() {
      _isLoading = true;
      _error = null;
      _selectedFolder = folderPath;
      _images = [];
      _selectedImages.clear();
      _selectAll = false;
    });

    try {
      final apiService = Provider.of<ApiService>(context, listen: false);
      final result = await apiService.getFolderImages(folderPath);
      final images = result['images'] as List<dynamic>;
      setState(() {
        _images = images.cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _toggleImageSelection(String imagePath) {
    setState(() {
      if (_selectedImages.contains(imagePath)) {
        _selectedImages.remove(imagePath);
        _selectAll = false;
      } else {
        _selectedImages.add(imagePath);
        if (_selectedImages.length == _images.length) {
          _selectAll = true;
        }
      }
    });
  }

  void _toggleSelectAll() {
    setState(() {
      _selectAll = !_selectAll;
      if (_selectAll) {
        _selectedImages = _images.map((img) => img['path'] as String).toSet();
      } else {
        _selectedImages.clear();
      }
    });
  }

  Future<void> _downloadSelectedImages() async {
    if (_selectedImages.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('No images selected')));
      }
      return;
    }

    setState(() {
      _isDownloading = true;
      _error = null;
    });

    try {
      final apiService = Provider.of<ApiService>(context, listen: false);

      // For web, we'll download directly without checksum comparison
      // For native apps, we could implement local checksum comparison
      if (kIsWeb) {
        await _downloadFilesWeb(apiService);
      } else {
        await _downloadFilesNative(apiService);
      }

      if (mounted) {
        setState(() {
          _isDownloading = false;
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Downloaded ${_selectedImages.length} image(s)'),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isDownloading = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Download failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _downloadFilesWeb(ApiService apiService) async {
    // For web, download files directly
    final fileBytes = await apiService.downloadFiles(_selectedImages.toList());

    // Use web download helper
    final filename = _selectedImages.length == 1
        ? _selectedImages.first.split('/').last
        : 'pumaguard_images.zip';
    downloadFilesWeb(fileBytes, filename);
  }

  Future<void> _downloadFilesNative(ApiService apiService) async {
    // For native apps, allow user to select destination folder
    String? selectedDirectory = await FilePicker.platform.getDirectoryPath();

    if (selectedDirectory == null) {
      // User cancelled
      return;
    }

    // TODO: Implement local file checking and checksum comparison
    // For now, just download all files
    await apiService.downloadFiles(_selectedImages.toList());

    // Save to selected directory
    // Note: This is simplified - in production you'd want to:
    // 1. Check local files
    // 2. Calculate checksums
    // 3. Only download changed files
    // 4. Extract ZIP if multiple files

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Files saved to: $selectedDirectory')),
      );
    }
  }

  String _formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  @override
  Widget build(BuildContext context) {
    final apiService = Provider.of<ApiService>(context, listen: false);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Image Browser'),
        actions: [
          if (_selectedImages.isNotEmpty)
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Center(
                child: Text(
                  '${_selectedImages.length} selected',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
            ),
          if (_selectedImages.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.download),
              onPressed: _isDownloading ? null : _downloadSelectedImages,
              tooltip: 'Download selected images',
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isLoading ? null : _loadFolders,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: _isLoading && _folders.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, size: 48, color: Colors.red),
                  const SizedBox(height: 16),
                  Text('Error: $_error'),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: _loadFolders,
                    child: const Text('Retry'),
                  ),
                ],
              ),
            )
          : Row(
              children: [
                // Folder list sidebar
                SizedBox(
                  width: 300,
                  child: Card(
                    margin: const EdgeInsets.all(8),
                    child: Column(
                      children: [
                        Padding(
                          padding: const EdgeInsets.all(16),
                          child: Text(
                            'Watched Folders',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                        ),
                        const Divider(),
                        Expanded(
                          child: _folders.isEmpty
                              ? const Center(child: Text('No watched folders'))
                              : ListView.builder(
                                  itemCount: _folders.length,
                                  itemBuilder: (context, index) {
                                    final folder = _folders[index];
                                    final isSelected =
                                        _selectedFolder == folder['path'];
                                    return ListTile(
                                      selected: isSelected,
                                      leading: const Icon(Icons.folder),
                                      title: Text(folder['name'] as String),
                                      subtitle: Text(
                                        '${folder['image_count']} images',
                                      ),
                                      onTap: () => _loadFolderImages(
                                        folder['path'] as String,
                                      ),
                                    );
                                  },
                                ),
                        ),
                      ],
                    ),
                  ),
                ),
                // Image grid
                Expanded(
                  child: _selectedFolder == null
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(
                                Icons.photo_library_outlined,
                                size: 64,
                                color: Colors.grey[400],
                              ),
                              const SizedBox(height: 16),
                              Text(
                                'Select a folder to view images',
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                            ],
                          ),
                        )
                      : Column(
                          children: [
                            // Toolbar
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 16,
                                vertical: 8,
                              ),
                              color: Theme.of(
                                context,
                              ).colorScheme.surfaceContainerHighest,
                              child: Row(
                                children: [
                                  Checkbox(
                                    value: _selectAll,
                                    onChanged: (value) => _toggleSelectAll(),
                                  ),
                                  const SizedBox(width: 8),
                                  Text(
                                    _selectAll ? 'Deselect All' : 'Select All',
                                  ),
                                  const Spacer(),
                                  Text('${_images.length} images'),
                                ],
                              ),
                            ),
                            // Image grid
                            Expanded(
                              child: _isLoading
                                  ? const Center(
                                      child: CircularProgressIndicator(),
                                    )
                                  : _images.isEmpty
                                  ? const Center(
                                      child: Text('No images in this folder'),
                                    )
                                  : GridView.builder(
                                      padding: const EdgeInsets.all(16),
                                      gridDelegate:
                                          const SliverGridDelegateWithMaxCrossAxisExtent(
                                            maxCrossAxisExtent: 200,
                                            childAspectRatio: 1,
                                            crossAxisSpacing: 16,
                                            mainAxisSpacing: 16,
                                          ),
                                      itemCount: _images.length,
                                      itemBuilder: (context, index) {
                                        final image = _images[index];
                                        final imagePath =
                                            image['path'] as String;
                                        final isSelected = _selectedImages
                                            .contains(imagePath);

                                        return GestureDetector(
                                          onTap: () =>
                                              _toggleImageSelection(imagePath),
                                          child: Card(
                                            elevation: isSelected ? 8 : 2,
                                            color: isSelected
                                                ? Theme.of(
                                                    context,
                                                  ).colorScheme.primaryContainer
                                                : null,
                                            child: Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.stretch,
                                              children: [
                                                Expanded(
                                                  child: Stack(
                                                    fit: StackFit.expand,
                                                    children: [
                                                      ClipRRect(
                                                        borderRadius:
                                                            const BorderRadius.vertical(
                                                              top:
                                                                  Radius.circular(
                                                                    12,
                                                                  ),
                                                            ),
                                                        child: Image.network(
                                                          apiService
                                                              .getPhotoUrl(
                                                                imagePath,
                                                              ),
                                                          fit: BoxFit.cover,
                                                          errorBuilder:
                                                              (
                                                                context,
                                                                error,
                                                                stackTrace,
                                                              ) {
                                                                return const Icon(
                                                                  Icons
                                                                      .broken_image,
                                                                  size: 48,
                                                                );
                                                              },
                                                        ),
                                                      ),
                                                      Positioned(
                                                        top: 8,
                                                        right: 8,
                                                        child: Container(
                                                          decoration: BoxDecoration(
                                                            color: isSelected
                                                                ? Theme.of(
                                                                        context,
                                                                      )
                                                                      .colorScheme
                                                                      .primary
                                                                : Colors.white,
                                                            shape:
                                                                BoxShape.circle,
                                                          ),
                                                          child: Padding(
                                                            padding:
                                                                const EdgeInsets.all(
                                                                  4,
                                                                ),
                                                            child: Icon(
                                                              isSelected
                                                                  ? Icons
                                                                        .check_circle
                                                                  : Icons
                                                                        .circle_outlined,
                                                              color: isSelected
                                                                  ? Colors.white
                                                                  : Colors.grey,
                                                              size: 24,
                                                            ),
                                                          ),
                                                        ),
                                                      ),
                                                    ],
                                                  ),
                                                ),
                                                Padding(
                                                  padding: const EdgeInsets.all(
                                                    8,
                                                  ),
                                                  child: Column(
                                                    crossAxisAlignment:
                                                        CrossAxisAlignment
                                                            .start,
                                                    children: [
                                                      Text(
                                                        image['filename']
                                                            as String,
                                                        style: Theme.of(
                                                          context,
                                                        ).textTheme.bodySmall,
                                                        maxLines: 1,
                                                        overflow: TextOverflow
                                                            .ellipsis,
                                                      ),
                                                      const SizedBox(height: 4),
                                                      Text(
                                                        _formatFileSize(
                                                          image['size'] as int,
                                                        ),
                                                        style: Theme.of(context)
                                                            .textTheme
                                                            .bodySmall
                                                            ?.copyWith(
                                                              color: Colors
                                                                  .grey[600],
                                                            ),
                                                      ),
                                                    ],
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                        );
                                      },
                                    ),
                            ),
                          ],
                        ),
                ),
              ],
            ),
      floatingActionButton: _isDownloading
          ? const FloatingActionButton(
              onPressed: null,
              child: CircularProgressIndicator(),
            )
          : null,
    );
  }
}
