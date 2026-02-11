import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'dart:developer' as developer;
import '../services/api_service.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:file_picker/file_picker.dart';
import '../utils/download_helper.dart';
import 'package:intl/intl.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum ImageGrouping { none, day, week }

enum ImageSize { small, large, full }

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
  ImageGrouping _grouping = ImageGrouping.none;
  ImageSize _imageSize = ImageSize.large;
  bool _showFolderPanel = true;

  @override
  void initState() {
    super.initState();
    _loadGroupingPreference();
    _loadFolders();
  }

  Future<void> _loadGroupingPreference() async {
    final prefs = await SharedPreferences.getInstance();
    final groupingString = prefs.getString('image_grouping') ?? 'none';
    final sizeString = prefs.getString('image_size') ?? 'large';
    setState(() {
      _grouping = ImageGrouping.values.firstWhere(
        (e) => e.name == groupingString,
        orElse: () => ImageGrouping.none,
      );
      _imageSize = ImageSize.values.firstWhere(
        (e) => e.name == sizeString,
        orElse: () => ImageSize.large,
      );
    });
  }

  Future<void> _saveGroupingPreference(ImageGrouping grouping) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('image_grouping', grouping.name);
  }

  Future<void> _saveSizePreference(ImageSize size) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('image_size', size.name);
  }

  List<Map<String, dynamic>> _groupImages(List<Map<String, dynamic>> images) {
    if (_grouping == ImageGrouping.none) {
      return images;
    }

    // Group images by date
    final Map<String, List<Map<String, dynamic>>> grouped = {};

    for (final image in images) {
      final timestamp = image['modified'];
      if (timestamp == null) continue;

      // Handle both int and double (st_mtime is a float)
      final timestampInt = (timestamp is int)
          ? timestamp
          : (timestamp as num).round();
      final date = DateTime.fromMillisecondsSinceEpoch(timestampInt * 1000);
      String groupKey;

      if (_grouping == ImageGrouping.day) {
        // Group by day
        groupKey = DateFormat('yyyy-MM-dd EEEE').format(date);
      } else {
        // Group by week
        final weekStart = date.subtract(Duration(days: date.weekday - 1));
        final weekEnd = weekStart.add(const Duration(days: 6));
        groupKey =
            '${DateFormat('MMM d').format(weekStart)} - ${DateFormat('MMM d, yyyy').format(weekEnd)}';
      }

      if (!grouped.containsKey(groupKey)) {
        grouped[groupKey] = [];
      }
      grouped[groupKey]!.add(image);
    }

    // Sort groups by date (most recent first)
    final sortedKeys = grouped.keys.toList()
      ..sort((a, b) {
        // Get the first image from each group to compare dates
        final aTimestamp = grouped[a]!.first['modified'];
        final aTimestampInt = (aTimestamp is int)
            ? aTimestamp
            : (aTimestamp as num).round();
        final aDate = DateTime.fromMillisecondsSinceEpoch(aTimestampInt * 1000);

        final bTimestamp = grouped[b]!.first['modified'];
        final bTimestampInt = (bTimestamp is int)
            ? bTimestamp
            : (bTimestamp as num).round();
        final bDate = DateTime.fromMillisecondsSinceEpoch(bTimestampInt * 1000);

        return bDate.compareTo(aDate); // Descending order
      });

    // Flatten the grouped images back into a list with headers
    final List<Map<String, dynamic>> result = [];
    for (final key in sortedKeys) {
      // Add a header item with reference to group images
      result.add({
        'is_header': true,
        'header_text': key,
        'image_count': grouped[key]!.length,
        'group_images': grouped[key]!, // Include images for group operations
      });
      // Add all images in this group
      result.addAll(grouped[key]!);
    }

    return result;
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

      // Reload images for the currently selected folder if there is one
      if (_selectedFolder != null) {
        await _loadFolderImages(_selectedFolder!);
      }
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

      // The backend returns 'path' as relative to the base directory
      // This is exactly what the /api/photos endpoint expects
      final imagesWithFullPaths = images.map((img) {
        final imageMap = img as Map<String, dynamic>;
        final relativePath = imageMap['path'] as String;
        return {
          ...imageMap,
          'full_path':
              relativePath, // Use the relative path as-is for API calls
        };
      }).toList();

      setState(() {
        _images = imagesWithFullPaths.cast<Map<String, dynamic>>();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _toggleImageSelection(String imagePath, String fullPath) {
    setState(() {
      if (_selectedImages.contains(fullPath)) {
        _selectedImages.remove(fullPath);
        _selectAll = false;
      } else {
        _selectedImages.add(fullPath);
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
        _selectedImages = _images
            .map((img) => img['full_path'] as String)
            .toSet();
      } else {
        _selectedImages.clear();
      }
    });
  }

  void _selectAllInGroup(List<Map<String, dynamic>> groupImages) {
    setState(() {
      // Add all images in this group to selected images
      for (final image in groupImages) {
        if (image['is_header'] != true) {
          final fullPath = image['full_path'] as String;
          _selectedImages.add(fullPath);
        }
      }
      // Update select all checkbox state
      if (_selectedImages.length == _images.length) {
        _selectAll = true;
      }
    });
  }

  void _deselectAllInGroup(List<Map<String, dynamic>> groupImages) {
    setState(() {
      // Remove all images in this group from selected images
      for (final image in groupImages) {
        if (image['is_header'] != true) {
          final fullPath = image['full_path'] as String;
          _selectedImages.remove(fullPath);
        }
      }
      _selectAll = false;
    });
  }

  bool _areAllImagesInGroupSelected(List<Map<String, dynamic>> groupImages) {
    for (final image in groupImages) {
      if (image['is_header'] != true) {
        final fullPath = image['full_path'] as String;
        if (!_selectedImages.contains(fullPath)) {
          return false;
        }
      }
    }
    return true;
  }

  String _formatFolderName(String folderName) {
    // Replace "intermediate" with "AI" for display
    if (folderName.toLowerCase() == 'intermediate') {
      return 'AI';
    }
    return folderName;
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

  Future<void> _deleteSelectedImages() async {
    if (_selectedImages.isEmpty) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('No images selected')));
      }
      return;
    }

    // Get apiService before async gap
    final apiService = Provider.of<ApiService>(context, listen: false);

    // Show confirmation dialog
    final confirm = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Delete Images'),
          content: Text(
            'Are you sure you want to delete ${_selectedImages.length} image(s)? This action cannot be undone.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              style: TextButton.styleFrom(foregroundColor: Colors.red),
              child: const Text('Delete'),
            ),
          ],
        );
      },
    );

    if (confirm != true) {
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final imagesToDelete = _selectedImages.toList();
      int successCount = 0;
      int failCount = 0;

      for (final imagePath in imagesToDelete) {
        try {
          await apiService.deletePhoto(imagePath);
          successCount++;

          // Remove from local state
          setState(() {
            _images.removeWhere((img) => img['full_path'] == imagePath);
            _selectedImages.remove(imagePath);
          });
        } catch (e) {
          failCount++;
          developer.log(
            'Failed to delete $imagePath: $e',
            name: 'ImageBrowser',
          );
        }
      }

      if (mounted) {
        setState(() {
          _isLoading = false;
          _selectAll = false;
        });

        if (failCount == 0) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Successfully deleted $successCount image(s)'),
              backgroundColor: Colors.green,
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Deleted $successCount image(s), failed to delete $failCount',
              ),
              backgroundColor: Colors.orange,
            ),
          );
        }

        // Reload folder list to update counts
        await _loadFolders();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Delete failed: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
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

  Widget _buildImageItem(
    BuildContext context,
    ApiService apiService,
    Map<String, dynamic> image,
  ) {
    final imagePath = image['path'] as String;
    final fullPath = image['full_path'] as String;
    final isSelected = _selectedImages.contains(fullPath);

    // Determine thumbnail parameters based on selected size
    final bool useThumbnail;
    final int? maxWidth;
    final int? maxHeight;
    final double cardMaxHeight;
    final double cardMinHeight;

    switch (_imageSize) {
      case ImageSize.small:
        useThumbnail = true;
        maxWidth = 200;
        maxHeight = 200;
        cardMaxHeight = 150;
        cardMinHeight = 100;
        break;
      case ImageSize.large:
        useThumbnail = true;
        maxWidth = 400;
        maxHeight = 400;
        cardMaxHeight = 300;
        cardMinHeight = 150;
        break;
      case ImageSize.full:
        useThumbnail = false;
        maxWidth = null;
        maxHeight = null;
        cardMaxHeight = 600;
        cardMinHeight = 300;
        break;
    }

    // Debug: log constructed photo URL
    final photoUrl = apiService.getPhotoUrl(
      fullPath,
      thumbnail: useThumbnail,
      maxWidth: maxWidth,
      maxHeight: maxHeight,
    );
    developer.log(
      'ImageBrowser: base=$_selectedFolder path=$imagePath full=$fullPath url=$photoUrl',
      name: 'ImageBrowser',
    );

    return GestureDetector(
      onTap: () => _toggleImageSelection(imagePath, fullPath),
      child: Card(
        elevation: isSelected ? 8 : 2,
        color: isSelected
            ? Theme.of(context).colorScheme.primaryContainer
            : null,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            ConstrainedBox(
              constraints: BoxConstraints(
                maxHeight: cardMaxHeight,
                minHeight: cardMinHeight,
              ),
              child: Stack(
                children: [
                  Center(
                    child: ClipRRect(
                      borderRadius: const BorderRadius.vertical(
                        top: Radius.circular(12),
                      ),
                      child: _RetryableImage(
                        photoUrl: photoUrl,
                        fit: BoxFit.contain,
                      ),
                    ),
                  ),
                  Positioned(
                    top: 8,
                    right: 8,
                    child: Container(
                      decoration: BoxDecoration(
                        color: isSelected
                            ? Theme.of(context).colorScheme.primary
                            : Colors.white,
                        shape: BoxShape.circle,
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(4),
                        child: Icon(
                          isSelected
                              ? Icons.check_circle
                              : Icons.circle_outlined,
                          color: isSelected ? Colors.white : Colors.grey,
                          size: 24,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(8),
              child: _imageSize == ImageSize.small
                  ? Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          image['filename'] as String,
                          style: Theme.of(context).textTheme.bodySmall,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ],
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          image['filename'] as String,
                          style: Theme.of(context).textTheme.bodySmall,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        // Debug: show relative path used for API
                        const SizedBox(height: 4),
                        Text(
                          'rel: $fullPath',
                          style: Theme.of(context).textTheme.bodySmall
                              ?.copyWith(color: Colors.grey[600]),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _formatFileSize(image['size'] as int),
                          style: Theme.of(context).textTheme.bodySmall
                              ?.copyWith(color: Colors.grey[600]),
                        ),
                      ],
                    ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final apiService = Provider.of<ApiService>(context, listen: false);
    final displayImages = _groupImages(_images);
    final isNarrowScreen = MediaQuery.of(context).size.width < 800;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Image Browser'),
        leading: isNarrowScreen && _selectedFolder != null
            ? IconButton(
                icon: const Icon(Icons.folder_outlined),
                onPressed: () {
                  setState(() {
                    _showFolderPanel = true;
                  });
                },
                tooltip: 'Show folders',
              )
            : null,
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
          if (_selectedImages.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.delete),
              onPressed: _isLoading ? null : _deleteSelectedImages,
              tooltip: 'Delete selected images',
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
          : isNarrowScreen
          ? _buildNarrowLayout(context, apiService, displayImages)
          : _buildWideLayout(context, apiService, displayImages),
      floatingActionButton: _isDownloading
          ? const FloatingActionButton(
              onPressed: null,
              child: CircularProgressIndicator(),
            )
          : null,
    );
  }

  Widget _buildWideLayout(
    BuildContext context,
    ApiService apiService,
    List<Map<String, dynamic>> displayImages,
  ) {
    return Row(
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
                // Debug overlay shows selected folder
                if (_selectedFolder != null)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        'Debug: Selected base = $_selectedFolder',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
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
                              title: Text(
                                _formatFolderName(folder['name'] as String),
                              ),
                              subtitle: Text('${folder['image_count']} images'),
                              onTap: () =>
                                  _loadFolderImages(folder['path'] as String),
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
                          Text(_selectAll ? 'Deselect All' : 'Select All'),
                          const Spacer(),
                          const Text('Size:'),
                          const SizedBox(width: 8),
                          DropdownButton<ImageSize>(
                            value: _imageSize,
                            underline: Container(),
                            items: const [
                              DropdownMenuItem(
                                value: ImageSize.small,
                                child: Text('Small'),
                              ),
                              DropdownMenuItem(
                                value: ImageSize.large,
                                child: Text('Large'),
                              ),
                              DropdownMenuItem(
                                value: ImageSize.full,
                                child: Text('Full'),
                              ),
                            ],
                            onChanged: (value) {
                              if (value != null) {
                                setState(() {
                                  _imageSize = value;
                                });
                                _saveSizePreference(value);
                              }
                            },
                          ),
                          const SizedBox(width: 16),
                          const Text('Group by:'),
                          const SizedBox(width: 8),
                          DropdownButton<ImageGrouping>(
                            value: _grouping,
                            underline: Container(),
                            items: const [
                              DropdownMenuItem(
                                value: ImageGrouping.none,
                                child: Text('None'),
                              ),
                              DropdownMenuItem(
                                value: ImageGrouping.day,
                                child: Text('Day'),
                              ),
                              DropdownMenuItem(
                                value: ImageGrouping.week,
                                child: Text('Week'),
                              ),
                            ],
                            onChanged: (value) {
                              if (value != null) {
                                setState(() {
                                  _grouping = value;
                                });
                                _saveGroupingPreference(value);
                              }
                            },
                          ),
                          const SizedBox(width: 16),
                          Text('${_images.length} images'),
                        ],
                      ),
                    ),
                    // Image grid with grouping
                    Expanded(
                      child: _isLoading
                          ? const Center(child: CircularProgressIndicator())
                          : _images.isEmpty
                          ? const Center(
                              child: Text('No images in this folder'),
                            )
                          : CustomScrollView(
                              slivers: [
                                SliverPadding(
                                  padding: const EdgeInsets.all(16),
                                  sliver: _imageSize == ImageSize.small
                                      ? SliverGrid(
                                          gridDelegate:
                                              const SliverGridDelegateWithMaxCrossAxisExtent(
                                                maxCrossAxisExtent: 250,
                                                childAspectRatio: 0.8,
                                                crossAxisSpacing: 16,
                                                mainAxisSpacing: 16,
                                              ),
                                          delegate: SliverChildBuilderDelegate((
                                            context,
                                            index,
                                          ) {
                                            final item = displayImages[index];

                                            // Skip headers in grid view
                                            if (item['is_header'] == true) {
                                              return const SizedBox.shrink();
                                            }

                                            return _buildImageItem(
                                              context,
                                              apiService,
                                              item,
                                            );
                                          }, childCount: displayImages.length),
                                        )
                                      : SliverList(
                                          delegate: SliverChildBuilderDelegate((
                                            context,
                                            index,
                                          ) {
                                            final item = displayImages[index];

                                            // Check if this is a header
                                            if (item['is_header'] == true) {
                                              final groupImages =
                                                  item['group_images']
                                                      as List<
                                                        Map<String, dynamic>
                                                      >;
                                              final allSelected =
                                                  _areAllImagesInGroupSelected(
                                                    groupImages,
                                                  );

                                              return Padding(
                                                padding: const EdgeInsets.only(
                                                  top: 16,
                                                  bottom: 8,
                                                ),
                                                child: Row(
                                                  children: [
                                                    Expanded(
                                                      child: Text(
                                                        item['header_text']
                                                            as String,
                                                        style: Theme.of(context)
                                                            .textTheme
                                                            .titleMedium
                                                            ?.copyWith(
                                                              fontWeight:
                                                                  FontWeight
                                                                      .bold,
                                                            ),
                                                      ),
                                                    ),
                                                    Container(
                                                      padding:
                                                          const EdgeInsets.symmetric(
                                                            horizontal: 12,
                                                            vertical: 4,
                                                          ),
                                                      decoration: BoxDecoration(
                                                        color: Theme.of(context)
                                                            .colorScheme
                                                            .primaryContainer,
                                                        borderRadius:
                                                            BorderRadius.circular(
                                                              12,
                                                            ),
                                                      ),
                                                      child: Text(
                                                        '${item['image_count']} images',
                                                        style: Theme.of(context)
                                                            .textTheme
                                                            .bodySmall
                                                            ?.copyWith(
                                                              color: Theme.of(context)
                                                                  .colorScheme
                                                                  .onPrimaryContainer,
                                                            ),
                                                      ),
                                                    ),
                                                    const SizedBox(width: 8),
                                                    OutlinedButton.icon(
                                                      onPressed: () {
                                                        if (allSelected) {
                                                          _deselectAllInGroup(
                                                            groupImages,
                                                          );
                                                        } else {
                                                          _selectAllInGroup(
                                                            groupImages,
                                                          );
                                                        }
                                                      },
                                                      icon: Icon(
                                                        allSelected
                                                            ? Icons.check_box
                                                            : Icons
                                                                  .check_box_outline_blank,
                                                        size: 18,
                                                      ),
                                                      label: Text(
                                                        allSelected
                                                            ? 'Deselect All'
                                                            : 'Select All',
                                                      ),
                                                      style: OutlinedButton.styleFrom(
                                                        padding:
                                                            const EdgeInsets.symmetric(
                                                              horizontal: 12,
                                                              vertical: 8,
                                                            ),
                                                        visualDensity:
                                                            VisualDensity
                                                                .compact,
                                                      ),
                                                    ),
                                                  ],
                                                ),
                                              );
                                            }

                                            // Regular image item
                                            return Padding(
                                              padding: const EdgeInsets.only(
                                                bottom: 16,
                                              ),
                                              child: _buildImageItem(
                                                context,
                                                apiService,
                                                item,
                                              ),
                                            );
                                          }, childCount: displayImages.length),
                                        ),
                                ),
                              ],
                            ),
                    ),
                  ],
                ),
        ),
      ],
    );
  }

  Widget _buildNarrowLayout(
    BuildContext context,
    ApiService apiService,
    List<Map<String, dynamic>> displayImages,
  ) {
    return Stack(
      children: [
        // Image grid (full screen on narrow displays)
        _buildImageGridContent(context, apiService, displayImages),
        // Folder panel overlay (modal panel that slides in from left)
        if (_showFolderPanel)
          Positioned.fill(
            child: GestureDetector(
              onTap: () {
                setState(() {
                  _showFolderPanel = false;
                });
              },
              child: Container(color: Colors.black54),
            ),
          ),
        if (_showFolderPanel)
          Positioned(
            left: 0,
            top: 0,
            bottom: 0,
            child: Material(
              elevation: 16,
              child: SizedBox(
                width: MediaQuery.of(context).size.width * 0.85,
                child: Column(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.primaryContainer,
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              'Watched Folders',
                              style: Theme.of(context).textTheme.titleLarge
                                  ?.copyWith(
                                    color: Theme.of(
                                      context,
                                    ).colorScheme.onPrimaryContainer,
                                  ),
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.close),
                            onPressed: () {
                              setState(() {
                                _showFolderPanel = false;
                              });
                            },
                            tooltip: 'Close',
                          ),
                        ],
                      ),
                    ),
                    const Divider(height: 1),
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
                                  title: Text(
                                    _formatFolderName(folder['name'] as String),
                                  ),
                                  subtitle: Text(
                                    '${folder['image_count']} images',
                                  ),
                                  onTap: () {
                                    _loadFolderImages(folder['path'] as String);
                                    setState(() {
                                      _showFolderPanel = false;
                                    });
                                  },
                                );
                              },
                            ),
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildImageGridContent(
    BuildContext context,
    ApiService apiService,
    List<Map<String, dynamic>> displayImages,
  ) {
    return _selectedFolder == null
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
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
                child: Row(
                  children: [
                    Checkbox(
                      value: _selectAll,
                      onChanged: (value) => _toggleSelectAll(),
                    ),
                    const SizedBox(width: 8),
                    Text(_selectAll ? 'Deselect All' : 'Select All'),
                    const Spacer(),
                    const Text('Size:'),
                    const SizedBox(width: 8),
                    DropdownButton<ImageSize>(
                      value: _imageSize,
                      underline: Container(),
                      items: const [
                        DropdownMenuItem(
                          value: ImageSize.small,
                          child: Text('Small'),
                        ),
                        DropdownMenuItem(
                          value: ImageSize.large,
                          child: Text('Large'),
                        ),
                        DropdownMenuItem(
                          value: ImageSize.full,
                          child: Text('Full'),
                        ),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          setState(() {
                            _imageSize = value;
                          });
                          _saveSizePreference(value);
                        }
                      },
                    ),
                    const SizedBox(width: 16),
                    const Text('Group by:'),
                    const SizedBox(width: 8),
                    DropdownButton<ImageGrouping>(
                      value: _grouping,
                      underline: Container(),
                      items: const [
                        DropdownMenuItem(
                          value: ImageGrouping.none,
                          child: Text('None'),
                        ),
                        DropdownMenuItem(
                          value: ImageGrouping.day,
                          child: Text('Day'),
                        ),
                        DropdownMenuItem(
                          value: ImageGrouping.week,
                          child: Text('Week'),
                        ),
                      ],
                      onChanged: (value) {
                        if (value != null) {
                          setState(() {
                            _grouping = value;
                          });
                          _saveGroupingPreference(value);
                        }
                      },
                    ),
                    const SizedBox(width: 16),
                    Text('${_images.length} images'),
                  ],
                ),
              ),
              // Image grid with grouping
              Expanded(
                child: _isLoading
                    ? const Center(child: CircularProgressIndicator())
                    : _images.isEmpty
                    ? const Center(child: Text('No images in this folder'))
                    : CustomScrollView(
                        slivers: [
                          SliverPadding(
                            padding: const EdgeInsets.all(16),
                            sliver: _imageSize == ImageSize.small
                                ? SliverGrid(
                                    gridDelegate:
                                        const SliverGridDelegateWithMaxCrossAxisExtent(
                                          maxCrossAxisExtent: 250,
                                          childAspectRatio: 0.8,
                                          crossAxisSpacing: 16,
                                          mainAxisSpacing: 16,
                                        ),
                                    delegate: SliverChildBuilderDelegate((
                                      context,
                                      index,
                                    ) {
                                      final item = displayImages[index];

                                      // Skip headers in grid view
                                      if (item['is_header'] == true) {
                                        return const SizedBox.shrink();
                                      }

                                      return _buildImageItem(
                                        context,
                                        apiService,
                                        item,
                                      );
                                    }, childCount: displayImages.length),
                                  )
                                : SliverList(
                                    delegate: SliverChildBuilderDelegate((
                                      context,
                                      index,
                                    ) {
                                      final item = displayImages[index];

                                      // Check if this is a header
                                      if (item['is_header'] == true) {
                                        final groupImages =
                                            item['group_images']
                                                as List<Map<String, dynamic>>;
                                        final allSelected =
                                            _areAllImagesInGroupSelected(
                                              groupImages,
                                            );

                                        return Padding(
                                          padding: const EdgeInsets.only(
                                            top: 16,
                                            bottom: 8,
                                          ),
                                          child: Row(
                                            children: [
                                              Expanded(
                                                child: Text(
                                                  item['header_text'] as String,
                                                  style: Theme.of(context)
                                                      .textTheme
                                                      .titleMedium
                                                      ?.copyWith(
                                                        fontWeight:
                                                            FontWeight.bold,
                                                      ),
                                                ),
                                              ),
                                              Container(
                                                padding:
                                                    const EdgeInsets.symmetric(
                                                      horizontal: 12,
                                                      vertical: 4,
                                                    ),
                                                decoration: BoxDecoration(
                                                  color: Theme.of(context)
                                                      .colorScheme
                                                      .primaryContainer,
                                                  borderRadius:
                                                      BorderRadius.circular(12),
                                                ),
                                                child: Text(
                                                  '${item['image_count']} images',
                                                  style: Theme.of(context)
                                                      .textTheme
                                                      .bodySmall
                                                      ?.copyWith(
                                                        color: Theme.of(context)
                                                            .colorScheme
                                                            .onPrimaryContainer,
                                                      ),
                                                ),
                                              ),
                                              const SizedBox(width: 8),
                                              OutlinedButton.icon(
                                                onPressed: () {
                                                  if (allSelected) {
                                                    _deselectAllInGroup(
                                                      groupImages,
                                                    );
                                                  } else {
                                                    _selectAllInGroup(
                                                      groupImages,
                                                    );
                                                  }
                                                },
                                                icon: Icon(
                                                  allSelected
                                                      ? Icons.check_box
                                                      : Icons
                                                            .check_box_outline_blank,
                                                  size: 18,
                                                ),
                                                label: Text(
                                                  allSelected
                                                      ? 'Deselect All'
                                                      : 'Select All',
                                                ),
                                                style: OutlinedButton.styleFrom(
                                                  padding:
                                                      const EdgeInsets.symmetric(
                                                        horizontal: 12,
                                                        vertical: 8,
                                                      ),
                                                  visualDensity:
                                                      VisualDensity.compact,
                                                ),
                                              ),
                                            ],
                                          ),
                                        );
                                      }

                                      // Regular image item
                                      return Padding(
                                        padding: const EdgeInsets.only(
                                          bottom: 16,
                                        ),
                                        child: _buildImageItem(
                                          context,
                                          apiService,
                                          item,
                                        ),
                                      );
                                    }, childCount: displayImages.length),
                                  ),
                          ),
                        ],
                      ),
              ),
            ],
          );
  }
}

/// A widget that displays an image with automatic retry capability on error
class _RetryableImage extends StatefulWidget {
  final String photoUrl;
  final BoxFit fit;

  const _RetryableImage({required this.photoUrl, required this.fit});

  @override
  State<_RetryableImage> createState() => _RetryableImageState();
}

class _RetryableImageState extends State<_RetryableImage> {
  int _retryCount = 0;
  static const int _maxRetries = 3;
  static const List<int> _retryDelays = [500, 1000, 2000]; // milliseconds
  bool _hasScheduledRetry = false;
  int _cacheBuster = DateTime.now().millisecondsSinceEpoch;

  @override
  void initState() {
    super.initState();
    developer.log(
      'Image widget created: ${widget.photoUrl}',
      name: 'RetryableImage.initState',
    );
  }

  @override
  void dispose() {
    developer.log(
      'Image widget disposed (retries: $_retryCount): ${widget.photoUrl}',
      name: 'RetryableImage.dispose',
    );
    super.dispose();
  }

  void _scheduleRetry() {
    if (_retryCount < _maxRetries && !_hasScheduledRetry) {
      _hasScheduledRetry = true;
      final delay = _retryDelays[_retryCount];

      developer.log(
        'Scheduling retry #${_retryCount + 1} in ${delay}ms: ${widget.photoUrl}',
        name: 'RetryableImage.scheduleRetry',
      );

      Future.delayed(Duration(milliseconds: delay), () {
        if (mounted) {
          developer.log(
            'Executing retry #${_retryCount + 1}: ${widget.photoUrl}',
            name: 'RetryableImage.scheduleRetry',
          );
          setState(() {
            _retryCount++;
            _hasScheduledRetry = false;
            _cacheBuster = DateTime.now().millisecondsSinceEpoch;
          });
        } else {
          developer.log(
            'Widget unmounted, skipping retry: ${widget.photoUrl}',
            name: 'RetryableImage.scheduleRetry',
          );
        }
      });
    } else {
      developer.log(
        'Retry not scheduled (count: $_retryCount, hasScheduled: $_hasScheduledRetry): ${widget.photoUrl}',
        name: 'RetryableImage.scheduleRetry',
      );
    }
  }

  void _manualRetry() {
    developer.log(
      'Manual retry triggered: ${widget.photoUrl}',
      name: 'RetryableImage.manualRetry',
    );
    setState(() {
      _retryCount = 0;
      _hasScheduledRetry = false;
      _cacheBuster = DateTime.now().millisecondsSinceEpoch;
    });
  }

  @override
  Widget build(BuildContext context) {
    // Use cache buster as query parameter to force reload
    final separator = widget.photoUrl.contains('?') ? '&' : '?';
    final imageUrl = '${widget.photoUrl}${separator}_cb=$_cacheBuster';

    developer.log(
      'Building image (retry: $_retryCount, cb: $_cacheBuster): $imageUrl',
      name: 'RetryableImage.build',
    );

    return Image.network(
      imageUrl,
      fit: widget.fit,
      loadingBuilder: (context, child, loadingProgress) {
        if (loadingProgress == null) {
          developer.log(
            'Image loaded successfully (after $_retryCount retries): ${widget.photoUrl}',
            name: 'RetryableImage.loadingBuilder',
          );
          return child;
        }
        developer.log(
          'Image loading (${loadingProgress.cumulativeBytesLoaded}/${loadingProgress.expectedTotalBytes ?? '?'}): ${widget.photoUrl}',
          name: 'RetryableImage.loadingBuilder',
        );
        return Center(
          child: CircularProgressIndicator(
            value: loadingProgress.expectedTotalBytes != null
                ? loadingProgress.cumulativeBytesLoaded /
                      loadingProgress.expectedTotalBytes!
                : null,
          ),
        );
      },
      errorBuilder: (context, error, stackTrace) {
        // Log the error for debugging
        developer.log(
          'Image load FAILED (attempt ${_retryCount + 1}/$_maxRetries): ${widget.photoUrl}',
          name: 'RetryableImage.errorBuilder',
          error: error,
          stackTrace: stackTrace,
        );

        // Schedule automatic retry only if we haven't exhausted retries
        if (_retryCount < _maxRetries) {
          developer.log(
            'Will schedule retry (hasScheduled: $_hasScheduledRetry): ${widget.photoUrl}',
            name: 'RetryableImage.errorBuilder',
          );
          WidgetsBinding.instance.addPostFrameCallback((_) {
            _scheduleRetry();
          });
        } else {
          developer.log(
            'Max retries reached, showing manual retry button: ${widget.photoUrl}',
            name: 'RetryableImage.errorBuilder',
          );
        }

        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.broken_image, size: 48, color: Colors.grey),
              const SizedBox(height: 8),
              Text(
                _retryCount < _maxRetries
                    ? 'Retrying... (${_retryCount + 1}/$_maxRetries)'
                    : 'Failed to load',
                style: Theme.of(context).textTheme.bodySmall,
              ),
              const SizedBox(height: 8),
              if (_retryCount < _maxRetries)
                const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              else
                TextButton.icon(
                  onPressed: _manualRetry,
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Retry'),
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    visualDensity: VisualDensity.compact,
                  ),
                ),
            ],
          ),
        );
      },
    );
  }
}
