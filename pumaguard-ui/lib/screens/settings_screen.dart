import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/settings.dart';
import '../models/plug.dart';
import '../services/api_service.dart';
import '../services/camera_events_service.dart';
import 'dart:developer' as developer;
import 'wifi_settings_screen.dart';
import 'package:file_picker/file_picker.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  Settings? _settings;
  bool _isLoading = true;
  bool _isSaving = false;
  bool _isTestingSound = false;
  bool _isTestingDetection = false;
  String? _error;

  // Controllers for text fields
  late TextEditingController _yoloMinSizeController;
  late TextEditingController _yoloConfThreshController;
  late TextEditingController _yoloMaxDetsController;
  late TextEditingController _yoloModelController;
  late TextEditingController _classifierModelController;
  late TextEditingController _fileStabilizationController;
  late TextEditingController _cameraAutoRemoveHoursController;
  List<String> _selectedSoundFiles = [];
  bool _playSound = false;
  double _volume = 80.0;
  bool _cameraAutoRemoveEnabled = false;
  List<Map<String, dynamic>> _availableModels = [];
  List<Map<String, dynamic>> _availableSounds = [];
  Timer? _debounceTimer;
  Timer? _cameraRefreshTimer;
  Timer? _shellyRefreshTimer;
  CameraEventsService? _cameraEventsService;
  StreamSubscription<CameraEvent>? _eventsSubscription;
  final Map<String, Plug> _shellyStatus = {};

  // Camera refresh interval (in seconds)
  static const int _cameraRefreshInterval = 30;

  // Server time synchronization
  String? _serverTime;
  bool _isSyncingTime = false;

  @override
  void initState() {
    super.initState();
    _yoloMinSizeController = TextEditingController();
    _yoloConfThreshController = TextEditingController();
    _yoloMaxDetsController = TextEditingController();
    _yoloModelController = TextEditingController();
    _classifierModelController = TextEditingController();
    _fileStabilizationController = TextEditingController();
    _cameraAutoRemoveHoursController = TextEditingController();

    _loadSettings();
    _initializeCameraEvents();
    _startCameraRefresh();
    _startShellyRefresh();
    _refreshServerTime();
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _cameraRefreshTimer?.cancel();
    _shellyRefreshTimer?.cancel();
    _eventsSubscription?.cancel();
    _cameraEventsService?.dispose();
    _yoloMinSizeController.dispose();
    _yoloConfThreshController.dispose();
    _yoloMaxDetsController.dispose();
    _yoloModelController.dispose();
    _classifierModelController.dispose();
    _fileStabilizationController.dispose();
    _cameraAutoRemoveHoursController.dispose();
    super.dispose();
  }

  void _initializeCameraEvents() {
    try {
      final apiService = context.read<ApiService>();
      final baseUrl = apiService.getApiUrl('').replaceAll('/api/', '');

      _cameraEventsService = CameraEventsService(baseUrl);

      // Subscribe to camera events
      _eventsSubscription = _cameraEventsService!.events.listen(
        (event) {
          // Reload settings when camera status changes
          if (event.type != CameraEventType.connected &&
              event.type != CameraEventType.unknown) {
            debugPrint(
              '[SettingsScreen] Camera event: ${event.type}, reloading settings',
            );
            _loadSettings();
          }
        },
        onError: (error) {
          debugPrint('[SettingsScreen] Camera events error: $error');
        },
      );

      // Start listening for events
      _cameraEventsService!.startListening();
      debugPrint('[SettingsScreen] Camera events service initialized');
    } catch (e) {
      debugPrint('[SettingsScreen] Error initializing camera events: $e');
    }
  }

  void _startCameraRefresh() {
    // Set up periodic timer to refresh camera status
    _cameraRefreshTimer = Timer.periodic(
      const Duration(seconds: _cameraRefreshInterval),
      (_) => _loadSettings(),
    );
  }

  void _startShellyRefresh() {
    // Refresh Shelly status every 5 seconds
    _shellyRefreshTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (mounted && _settings != null && _settings!.plugs.isNotEmpty) {
        _loadShellyStatus();
      }
    });
  }

  Future<void> _loadShellyStatus() async {
    final apiService = Provider.of<ApiService>(context, listen: false);

    for (final plug in _settings!.plugs) {
      if (plug.isConnected) {
        try {
          final shellyPlug = await apiService.getShellyStatus(plug.macAddress);
          if (mounted) {
            setState(() {
              _shellyStatus[plug.macAddress] = shellyPlug;
            });
          }
        } catch (e) {
          debugPrint(
            '[SettingsScreen._loadShellyStatus] Error loading Shelly status for ${plug.macAddress}: $e',
          );
          // Remove stale status on error
          if (mounted) {
            setState(() {
              _shellyStatus.remove(plug.macAddress);
            });
          }
        }
      } else {
        // Remove status for disconnected plugs
        if (mounted && _shellyStatus.containsKey(plug.macAddress)) {
          setState(() {
            _shellyStatus.remove(plug.macAddress);
          });
        }
      }
    }
  }

  Future<void> _loadSettings() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final apiService = context.read<ApiService>();
      final settings = await apiService.getSettings();
      setState(() {
        _settings = settings;
        _yoloMinSizeController.text = settings.yoloMinSize.toString();
        _yoloConfThreshController.text = settings.yoloConfThresh.toString();
        _yoloMaxDetsController.text = settings.yoloMaxDets.toString();
        _yoloModelController.text = settings.yoloModelFilename;
        _classifierModelController.text = settings.classifierModelFilename;
        _selectedSoundFiles = List.from(settings.deterrentSoundFiles);
        _fileStabilizationController.text = settings.fileStabilizationExtraWait
            .toString();
        _playSound = settings.playSound;
        _volume = settings.volume.toDouble();
        _cameraAutoRemoveEnabled = settings.cameraAutoRemoveEnabled;
        _cameraAutoRemoveHoursController.text = settings.cameraAutoRemoveHours
            .toString();
        _isLoading = false;
      });

      // Load Shelly status for connected plugs
      await _loadShellyStatus();
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _refreshServerTime() async {
    try {
      final apiService = context.read<ApiService>();
      final timeData = await apiService.getServerTime();
      if (mounted) {
        setState(() {
          final serverDateTime = DateTime.parse(timeData['iso'] as String);
          _serverTime = serverDateTime.toLocal().toString().substring(0, 19);
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to get server time: $e')),
        );
      }
    }
  }

  Future<void> _syncTime() async {
    setState(() {
      _isSyncingTime = true;
    });

    try {
      final apiService = context.read<ApiService>();
      final result = await apiService.syncServerTime();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              result['message'] as String? ?? 'Time synced successfully',
            ),
            backgroundColor: Colors.green,
          ),
        );

        // Refresh to show new server time
        await _refreshServerTime();
      }
    } catch (e) {
      if (mounted) {
        String errorMsg = e.toString().replaceFirst('Exception: ', '');

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(errorMsg),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSyncingTime = false;
        });
      }
    }
  }

  void _onTextFieldChanged() {
    // Cancel any existing timer
    _debounceTimer?.cancel();

    // Create a new timer that will save after 1 second of no changes
    _debounceTimer = Timer(const Duration(seconds: 1), () {
      _saveSettings();
    });
  }

  Future<void> _saveSettings() async {
    if (_settings == null) return;

    setState(() {
      _isSaving = true;
      _error = null;
    });

    try {
      final updatedSettings = Settings(
        yoloMinSize: double.tryParse(_yoloMinSizeController.text) ?? 0.01,
        yoloConfThresh: double.tryParse(_yoloConfThreshController.text) ?? 0.25,
        yoloMaxDets: int.tryParse(_yoloMaxDetsController.text) ?? 10,
        yoloModelFilename: _yoloModelController.text,
        classifierModelFilename: _classifierModelController.text,
        deterrentSoundFiles: _selectedSoundFiles,
        fileStabilizationExtraWait:
            double.tryParse(_fileStabilizationController.text) ?? 2.0,
        playSound: _playSound,
        volume: _volume.round(),
        cameras: _settings?.cameras ?? [],
        plugs: _settings?.plugs ?? [],
        cameraAutoRemoveEnabled: _cameraAutoRemoveEnabled,
        cameraAutoRemoveHours:
            int.tryParse(_cameraAutoRemoveHoursController.text) ?? 24,
      );

      developer.log(
        '[SettingsScreen._saveSettings] Settings JSON: ${updatedSettings.toJson()}',
      );

      final apiService = context.read<ApiService>();
      await apiService.updateSettings(updatedSettings);

      developer.log(
        '[SettingsScreen._saveSettings] Settings saved successfully',
      );

      setState(() {
        _settings = updatedSettings;
        _isSaving = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Settings saved successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isSaving = false;
      });

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to save settings: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _testSound() async {
    setState(() {
      _isTestingSound = true;
      _error = null;
    });

    try {
      final apiService = context.read<ApiService>();
      await apiService.testSound();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Sound test started'),
            backgroundColor: Colors.green,
            duration: Duration(seconds: 2),
          ),
        );
      }

      // Poll sound status to detect when it finishes
      while (mounted && _isTestingSound) {
        await Future.delayed(const Duration(milliseconds: 500));
        final isPlaying = await apiService.getSoundStatus();
        if (!isPlaying && mounted) {
          setState(() {
            _isTestingSound = false;
          });
          break;
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to test sound: $e'),
            backgroundColor: Colors.red,
          ),
        );
        setState(() {
          _isTestingSound = false;
        });
      }
    }
  }

  Future<void> _stopSound() async {
    try {
      final apiService = context.read<ApiService>();
      await apiService.stopSound();

      if (mounted) {
        setState(() {
          _isTestingSound = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Sound stopped'),
            backgroundColor: Colors.orange,
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to stop sound: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _testDetection() async {
    setState(() {
      _isTestingDetection = true;
      _error = null;
    });

    try {
      final apiService = context.read<ApiService>();
      await apiService.testDetection();

      if (mounted) {
        setState(() {
          _isTestingDetection = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Detection test completed'),
            backgroundColor: Colors.green,
            duration: Duration(seconds: 2),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to test detection: $e'),
            backgroundColor: Colors.red,
          ),
        );
        setState(() {
          _isTestingDetection = false;
        });
      }
    }
  }

  Future<void> _uploadSoundFile() async {
    try {
      // Get API service before any async operations
      final apiService = context.read<ApiService>();

      // Pick a file
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['mp3'],
        withData: true,
      );

      if (result == null || result.files.isEmpty) {
        // User canceled the picker
        return;
      }

      final file = result.files.first;
      if (file.bytes == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Failed to read file'),
              backgroundColor: Colors.red,
            ),
          );
        }
        return;
      }

      // Show loading indicator
      if (mounted) {
        setState(() {
          _isLoading = true;
        });
      }

      debugPrint(
        '[SettingsScreen] Attempting to upload sound file: ${file.name}',
      );
      debugPrint('[SettingsScreen] File size: ${file.bytes!.length} bytes');

      // Upload the file
      // Note: file.path is not available on web, so we pass empty string
      final response = await apiService.uploadSound(
        '', // Path not available/needed on web
        file.bytes!,
        file.name,
      );

      debugPrint('[SettingsScreen] Upload response: $response');

      if (mounted) {
        setState(() {
          _isLoading = false;
        });

        // Show success message
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              response['message'] ?? 'Sound file uploaded successfully',
            ),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 3),
          ),
        );

        // Set the uploaded file as the current sound
        final uploadedFilename = response['filename'] as String?;
        if (uploadedFilename != null) {
          setState(() {
            if (!_selectedSoundFiles.contains(uploadedFilename)) {
              _selectedSoundFiles.add(uploadedFilename);
            }
          });
          await _saveSettings();
        }

        // Refresh the sound picker dialog by calling it again
        await _showSoundPicker();
      }
    } catch (e, stackTrace) {
      developer.log('Error uploading sound', error: e, stackTrace: stackTrace);
      debugPrint('[SettingsScreen] Upload error: $e');
      debugPrint('[SettingsScreen] Stack trace: $stackTrace');
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to upload sound: $e'),
            backgroundColor: Colors.red,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    }
  }

  Future<void> _showModelPicker({String modelType = 'classifier'}) async {
    setState(() {
      _isLoading = true;
    });

    try {
      final apiService = context.read<ApiService>();
      final models = await apiService.getAvailableModels(modelType: modelType);

      setState(() {
        _availableModels = models;
        _isLoading = false;
      });

      if (!mounted) return;

      final selectedModel = await showDialog<String>(
        context: context,
        builder: (BuildContext context) {
          return AlertDialog(
            title: Text(
              modelType == 'yolo'
                  ? 'Select YOLO Model'
                  : 'Select Classifier Model',
            ),
            content: SizedBox(
              width: double.maxFinite,
              child: ListView.builder(
                shrinkWrap: true,
                itemCount: _availableModels.length,
                itemBuilder: (context, index) {
                  final model = _availableModels[index];
                  final isCached = model['cached'] as bool;
                  final modelName = model['name'] as String;
                  final sizeMb = model['size_mb'] as double?;

                  return ListTile(
                    title: Text(modelName),
                    subtitle: Text(
                      isCached
                          ? 'Cached${sizeMb != null ? " (${sizeMb.toStringAsFixed(1)} MB)" : ""}'
                          : 'Requires download',
                      style: TextStyle(
                        color: isCached ? Colors.green : Colors.orange,
                      ),
                    ),
                    leading: Icon(
                      isCached ? Icons.check_circle : Icons.cloud_download,
                      color: isCached ? Colors.green : Colors.orange,
                    ),
                    trailing: modelName == _classifierModelController.text
                        ? const Icon(Icons.check, color: Colors.blue)
                        : null,
                    onTap: () {
                      Navigator.of(context).pop(modelName);
                    },
                  );
                },
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
            ],
          );
        },
      );

      if (selectedModel != null) {
        setState(() {
          if (modelType == 'yolo') {
            _yoloModelController.text = selectedModel;
          } else {
            _classifierModelController.text = selectedModel;
          }
        });
        // Persist the change immediately
        await _saveSettings();
      }
    } catch (e) {
      developer.log('Error loading models: $e');
      setState(() {
        _isLoading = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to load models: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _showSoundPicker() async {
    setState(() {
      _isLoading = true;
    });

    try {
      final apiService = context.read<ApiService>();
      final sounds = await apiService.getAvailableSounds();

      setState(() {
        _availableSounds = sounds;
        _isLoading = false;
      });

      if (!mounted) return;

      final result = await showDialog<dynamic>(
        context: context,
        builder: (BuildContext context) {
          // Create a local copy of selected sounds for the dialog
          final tempSelectedSounds = List<String>.from(_selectedSoundFiles);

          return StatefulBuilder(
            builder: (context, setDialogState) {
              return AlertDialog(
                title: const Text('Select Sound Files'),
                content: SizedBox(
                  width: double.maxFinite,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      ElevatedButton.icon(
                        onPressed: () async {
                          Navigator.of(context).pop('__upload__');
                        },
                        icon: const Icon(Icons.upload_file),
                        label: const Text('Upload New Sound File'),
                        style: ElevatedButton.styleFrom(
                          minimumSize: const Size(double.infinity, 48),
                        ),
                      ),
                      const SizedBox(height: 16),
                      const Divider(),
                      const SizedBox(height: 8),
                      Flexible(
                        child: ListView.builder(
                          shrinkWrap: true,
                          itemCount: _availableSounds.length,
                          itemBuilder: (context, index) {
                            final sound = _availableSounds[index];
                            final soundName = sound['name'] as String;
                            final sizeMb = sound['size_mb'] as double?;
                            final isSelected = tempSelectedSounds.contains(
                              soundName,
                            );

                            return CheckboxListTile(
                              title: Text(soundName),
                              subtitle: Text(
                                sizeMb != null
                                    ? '${sizeMb.toStringAsFixed(2)} MB'
                                    : '',
                                style: const TextStyle(color: Colors.blue),
                              ),
                              secondary: const Icon(
                                Icons.music_note,
                                color: Colors.blue,
                              ),
                              value: isSelected,
                              onChanged: (bool? value) {
                                setDialogState(() {
                                  if (value == true) {
                                    tempSelectedSounds.add(soundName);
                                  } else {
                                    // Don't allow removing the last sound file
                                    if (tempSelectedSounds.length > 1) {
                                      tempSelectedSounds.remove(soundName);
                                    }
                                  }
                                });
                              },
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Cancel'),
                  ),
                  ElevatedButton(
                    onPressed: () {
                      Navigator.of(context).pop(tempSelectedSounds);
                    },
                    child: const Text('Done'),
                  ),
                ],
              );
            },
          );
        },
      );

      if (result == '__upload__') {
        // User selected upload option
        await _uploadSoundFile();
      } else if (result is List<String>) {
        // User clicked Done - update the selected sounds
        setState(() {
          _selectedSoundFiles = result;
        });
        // Persist the change immediately
        await _saveSettings();
      }
    } catch (e) {
      developer.log('Error loading sounds: $e');
      setState(() {
        _isLoading = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to load sounds: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        actions: [
          if (_isSaving)
            const Padding(
              padding: EdgeInsets.all(16.0),
              child: SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null && _settings == null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Theme.of(context).colorScheme.error,
            ),
            const SizedBox(height: 16),
            Text(
              'Failed to Load Settings',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                _error!,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _loadSettings,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildYoloSection(),
          const SizedBox(height: 16),
          _buildClassifierSection(),
          const SizedBox(height: 16),
          _buildSoundSection(),
          const SizedBox(height: 16),
          _buildSystemSection(),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _isSaving ? null : _saveSettings,
            icon: _isSaving
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.save),
            label: const Text('Save Settings'),
            style: ElevatedButton.styleFrom(padding: const EdgeInsets.all(16)),
          ),
        ],
      ),
    );
  }

  Widget _buildYoloSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.track_changes,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'YOLO Detection Settings',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Configure object detection parameters',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _yoloMinSizeController,
              onChanged: (_) => _onTextFieldChanged(),
              decoration: const InputDecoration(
                labelText: 'Minimum Size',
                hintText: '0.01',
                helperText: 'Minimum object size as fraction of image',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _yoloConfThreshController,
              onChanged: (_) => _onTextFieldChanged(),
              decoration: const InputDecoration(
                labelText: 'Confidence Threshold',
                hintText: '0.25',
                helperText: 'Detection confidence threshold (0.0 - 1.0)',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _yoloMaxDetsController,
              onChanged: (_) => _onTextFieldChanged(),
              decoration: const InputDecoration(
                labelText: 'Maximum Detections',
                hintText: '10',
                helperText: 'Maximum number of objects to detect',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _yoloModelController,
              decoration: InputDecoration(
                labelText: 'YOLO Model Filename',
                hintText: 'yolo_model.pt',
                helperText: 'Path to YOLO model file',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.folder_open),
                  onPressed: () => _showModelPicker(modelType: 'yolo'),
                  tooltip: 'Browse available models',
                ),
              ),
              readOnly: false,
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: () => _showModelPicker(modelType: 'yolo'),
              icon: const Icon(Icons.list),
              label: const Text('Choose from Available Models'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.all(12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildClassifierSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.category,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'Classifier Settings',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Configure EfficientNet classifier',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _classifierModelController,
              decoration: InputDecoration(
                labelText: 'Classifier Model Filename',
                hintText: 'classifier_model.h5',
                helperText: 'Path to classifier model file',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.folder_open),
                  onPressed: _showModelPicker,
                  tooltip: 'Browse available models',
                ),
              ),
              readOnly: false,
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _showModelPicker,
              icon: const Icon(Icons.list),
              label: const Text('Choose from Available Models'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.all(12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSoundSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.volume_up,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'Sound Settings',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Configure deterrent sound playback',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 16),
            // Display selected sound files as chips
            Container(
              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey),
                borderRadius: BorderRadius.circular(4),
              ),
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Deterrent Sound Files',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                  const SizedBox(height: 8),
                  if (_selectedSoundFiles.isEmpty)
                    const Text(
                      'No sound files selected',
                      style: TextStyle(color: Colors.grey),
                    )
                  else
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      children: _selectedSoundFiles.map((soundFile) {
                        return Chip(
                          label: Text(soundFile),
                          deleteIcon: _selectedSoundFiles.length > 1
                              ? const Icon(Icons.close, size: 18)
                              : null,
                          onDeleted: _selectedSoundFiles.length > 1
                              ? () {
                                  setState(() {
                                    _selectedSoundFiles.remove(soundFile);
                                  });
                                  _saveSettings();
                                }
                              : null,
                        );
                      }).toList(),
                    ),
                  const SizedBox(height: 4),
                  Text(
                    'One sound will be randomly selected when a puma is detected. At least one sound must be selected.',
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: Colors.grey[600]),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _showSoundPicker,
                    icon: const Icon(Icons.list),
                    label: const Text('Choose from Available Sounds'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.all(12),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isLoading ? null : _uploadSoundFile,
                    icon: const Icon(Icons.upload_file),
                    label: const Text('Upload New Sound File'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.all(12),
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SwitchListTile(
              title: const Text('Play Sound'),
              subtitle: const Text('Enable deterrent sound playback'),
              value: _playSound,
              onChanged: (value) {
                setState(() {
                  _playSound = value;
                });
                // Persist the change immediately
                _saveSettings();
              },
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Icon(
                  Icons.volume_down,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
                Expanded(
                  child: Slider(
                    value: _volume,
                    min: 0,
                    max: 100,
                    divisions: 20,
                    label: _volume.round().toString(),
                    onChanged: (value) {
                      setState(() {
                        _volume = value;
                      });
                    },
                    onChangeEnd: (value) {
                      // Save when user releases the slider
                      _saveSettings();
                    },
                  ),
                ),
                Icon(
                  Icons.volume_up,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 8),
                SizedBox(
                  width: 45,
                  child: Text(
                    '${_volume.round()}%',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontFamily: 'RobotoMono',
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _isTestingSound ? null : _testSound,
                    icon: _isTestingSound
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.play_arrow),
                    label: const Text('Test Sound'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.all(12),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _isTestingSound ? _stopSound : null,
                    icon: const Icon(Icons.stop),
                    label: const Text('Stop Sound'),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.all(12),
                      foregroundColor: Colors.orange,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _isTestingDetection ? null : _testDetection,
                icon: _isTestingDetection
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.notifications_active),
                label: const Text('Test Detection'),
                style: ElevatedButton.styleFrom(
                  padding: const EdgeInsets.all(12),
                ),
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Simulates a puma detection: plays a random sound and controls automatic plugs',
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: Colors.grey[600]),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSystemSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.settings_system_daydream,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text(
                  'System Settings',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Configure system behavior',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _fileStabilizationController,
              onChanged: (_) => _onTextFieldChanged(),
              decoration: const InputDecoration(
                labelText: 'File Stabilization Wait (seconds)',
                hintText: '2.0',
                helperText: 'Extra wait time for file operations to complete',
                border: OutlineInputBorder(),
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 24),
            // Camera Auto-Removal Section
            Row(
              children: [
                Icon(
                  Icons.auto_delete,
                  color: Theme.of(context).colorScheme.primary,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Camera Auto-Removal',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Automatically remove inactive cameras',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            SwitchListTile(
              title: const Text('Enable Auto-Removal'),
              subtitle: const Text(
                'Automatically remove cameras that have been inactive',
              ),
              value: _cameraAutoRemoveEnabled,
              onChanged: (bool value) {
                setState(() {
                  _cameraAutoRemoveEnabled = value;
                });
                _saveSettings();
              },
            ),
            if (_cameraAutoRemoveEnabled) ...[
              const SizedBox(height: 12),
              TextField(
                controller: _cameraAutoRemoveHoursController,
                onChanged: (_) => _onTextFieldChanged(),
                decoration: const InputDecoration(
                  labelText: 'Inactivity Threshold (hours)',
                  hintText: '24',
                  helperText: 'Remove cameras inactive for this many hours',
                  border: OutlineInputBorder(),
                  prefixIcon: Icon(Icons.schedule),
                ),
                keyboardType: TextInputType.number,
              ),
            ],
            const SizedBox(height: 24),
            // Server Time Section
            Row(
              children: [
                Icon(
                  Icons.access_time,
                  color: Theme.of(context).colorScheme.primary,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Server Time',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              'Synchronize or view server time',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            Card(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  children: [
                    Icon(
                      Icons.schedule,
                      size: 20,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Current Server Time',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _serverTime ?? 'Loading...',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.refresh),
                      onPressed: _isSyncingTime ? null : _refreshServerTime,
                      tooltip: 'Refresh server time',
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: _isSyncingTime ? null : _syncTime,
              icon: _isSyncingTime
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.sync),
              label: Text(
                _isSyncingTime ? 'Syncing...' : 'Sync Time from This Device',
              ),
              style: FilledButton.styleFrom(
                minimumSize: const Size(double.infinity, 48),
              ),
            ),
            const SizedBox(height: 24),
            // WiFi Settings Button
            FilledButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (context) => WifiSettingsScreen(
                      apiService: context.read<ApiService>(),
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.wifi),
              label: const Text('WiFi Settings'),
              style: FilledButton.styleFrom(
                minimumSize: const Size(double.infinity, 48),
              ),
            ),
            const SizedBox(height: 24),
            // Detected Cameras Section
            if (_settings != null && _settings!.cameras.isNotEmpty) ...[
              Text(
                'Detected Cameras',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                'Cameras detected via DHCP',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 16),
              ..._settings!.cameras.map((camera) {
                final isConnected = camera.isConnected;
                final statusColor = isConnected ? Colors.green : Colors.grey;
                final statusText = isConnected ? 'Connected' : 'Disconnected';

                return Card(
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    leading: CircleAvatar(
                      backgroundColor: statusColor.withValues(alpha: 0.2),
                      child: Icon(Icons.videocam, color: statusColor),
                    ),
                    title: Text(
                      camera.displayName,
                      style: const TextStyle(fontWeight: FontWeight.w500),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 4),
                        Text('IP: ${camera.ipAddress}'),
                        const SizedBox(height: 2),
                        Row(
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: statusColor,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              statusText,
                              style: TextStyle(
                                color: statusColor,
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline),
                      color: Theme.of(context).colorScheme.error,
                      tooltip: 'Remove camera',
                      onPressed: () async {
                        final confirmed = await showDialog<bool>(
                          context: context,
                          builder: (context) => AlertDialog(
                            title: const Text('Remove Camera'),
                            content: Text(
                              'Are you sure you want to remove "${camera.displayName}"?',
                            ),
                            actions: [
                              TextButton(
                                onPressed: () =>
                                    Navigator.of(context).pop(false),
                                child: const Text('Cancel'),
                              ),
                              FilledButton(
                                onPressed: () =>
                                    Navigator.of(context).pop(true),
                                style: FilledButton.styleFrom(
                                  backgroundColor: Theme.of(
                                    context,
                                  ).colorScheme.error,
                                ),
                                child: const Text('Remove'),
                              ),
                            ],
                          ),
                        );

                        if (confirmed == true && mounted) {
                          try {
                            await context.read<ApiService>().deleteCamera(
                              camera.macAddress,
                            );
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(
                                    'Camera "${camera.displayName}" removed',
                                  ),
                                ),
                              );
                              _loadSettings();
                            }
                          } catch (e) {
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text('Failed to remove camera: $e'),
                                  backgroundColor: Theme.of(
                                    context,
                                  ).colorScheme.error,
                                ),
                              );
                            }
                          }
                        }
                      },
                    ),
                  ),
                );
              }),
              const SizedBox(height: 24),
            ],
            // Detected Plugs Section
            if (_settings != null && _settings!.plugs.isNotEmpty) ...[
              Text(
                'Detected Plugs',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                'Smart plugs detected via DHCP (for deterrents)',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 16),
              ..._settings!.plugs.map((plug) {
                final isConnected = plug.isConnected;
                final statusColor = isConnected ? Colors.green : Colors.grey;
                final statusText = isConnected ? 'Connected' : 'Disconnected';

                // Get Shelly status if available
                final shellyPlug = _shellyStatus[plug.macAddress];
                final hasShelly = shellyPlug != null;

                Color modeColor;
                IconData modeIcon;

                switch (plug.mode) {
                  case 'on':
                    modeColor = Colors.green;
                    modeIcon = Icons.power_settings_new;
                    break;
                  case 'off':
                    modeColor = Colors.grey;
                    modeIcon = Icons.power_off;
                    break;
                  case 'automatic':
                    modeColor = Colors.orange;
                    modeIcon = Icons.auto_mode;
                    break;
                  default:
                    modeColor = Colors.grey;
                    modeIcon = Icons.power_off;
                }

                // Determine actual output state from Shelly
                final isOutputOn = hasShelly
                    ? (shellyPlug.output ?? false)
                    : false;
                final outputColor = isOutputOn ? Colors.green : Colors.grey;

                return Card(
                  child: ListTile(
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    leading: CircleAvatar(
                      backgroundColor: modeColor.withValues(alpha: 0.2),
                      child: Icon(Icons.power, color: modeColor),
                    ),
                    title: Text(
                      plug.displayName,
                      style: const TextStyle(fontWeight: FontWeight.w500),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SizedBox(height: 4),
                        Text('IP: ${plug.ipAddress}'),
                        const SizedBox(height: 2),
                        Row(
                          children: [
                            Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: statusColor,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Text(
                              statusText,
                              style: TextStyle(
                                color: statusColor,
                                fontSize: 12,
                              ),
                            ),
                            const SizedBox(width: 12),
                            Icon(modeIcon, size: 14, color: modeColor),
                            const SizedBox(width: 4),
                            Text(
                              plug.mode.toUpperCase(),
                              style: TextStyle(
                                color: modeColor,
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                        if (hasShelly) ...[
                          const SizedBox(height: 4),
                          Row(
                            children: [
                              Icon(
                                isOutputOn
                                    ? Icons.lightbulb
                                    : Icons.lightbulb_outline,
                                size: 14,
                                color: outputColor,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                isOutputOn ? 'ON' : 'OFF',
                                style: TextStyle(
                                  color: outputColor,
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              const SizedBox(width: 12),
                              Icon(
                                Icons.flash_on,
                                size: 14,
                                color: Colors.orange,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                '${shellyPlug.apower?.toStringAsFixed(1) ?? '0.0'}W',
                                style: const TextStyle(fontSize: 12),
                              ),
                              const SizedBox(width: 12),
                              Icon(
                                Icons.electric_bolt,
                                size: 14,
                                color: Colors.blue,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                '${shellyPlug.voltage?.toStringAsFixed(1) ?? '0.0'}V',
                                style: const TextStyle(fontSize: 12),
                              ),
                            ],
                          ),
                          const SizedBox(height: 2),
                          Row(
                            children: [
                              Icon(
                                Icons.show_chart,
                                size: 14,
                                color: Colors.purple,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                '${shellyPlug.current?.toStringAsFixed(2) ?? '0.00'}A',
                                style: const TextStyle(fontSize: 12),
                              ),
                              if (shellyPlug.temperature != null &&
                                  shellyPlug.temperature!['tC'] != null) ...[
                                const SizedBox(width: 12),
                                Icon(
                                  Icons.thermostat,
                                  size: 14,
                                  color: Colors.red,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  '${shellyPlug.temperature!['tC'].toStringAsFixed(1)}°C',
                                  style: const TextStyle(fontSize: 12),
                                ),
                              ],
                            ],
                          ),
                        ],
                      ],
                    ),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline),
                      color: Theme.of(context).colorScheme.error,
                      tooltip: 'Remove plug',
                      onPressed: () async {
                        final confirmed = await showDialog<bool>(
                          context: context,
                          builder: (context) => AlertDialog(
                            title: const Text('Remove Plug'),
                            content: Text(
                              'Are you sure you want to remove "${plug.displayName}"?',
                            ),
                            actions: [
                              TextButton(
                                onPressed: () =>
                                    Navigator.of(context).pop(false),
                                child: const Text('Cancel'),
                              ),
                              FilledButton(
                                onPressed: () =>
                                    Navigator.of(context).pop(true),
                                style: FilledButton.styleFrom(
                                  backgroundColor: Theme.of(
                                    context,
                                  ).colorScheme.error,
                                ),
                                child: const Text('Remove'),
                              ),
                            ],
                          ),
                        );

                        if (confirmed == true && mounted) {
                          try {
                            await context.read<ApiService>().deletePlug(
                              plug.macAddress,
                            );
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(
                                    'Plug "${plug.displayName}" removed',
                                  ),
                                ),
                              );
                              _loadSettings();
                              _loadShellyStatus();
                            }
                          } catch (e) {
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text('Failed to remove plug: $e'),
                                  backgroundColor: Theme.of(
                                    context,
                                  ).colorScheme.error,
                                ),
                              );
                            }
                          }
                        }
                      },
                    ),
                  ),
                );
              }),
            ],
          ],
        ),
      ),
    );
  }
}
