import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/settings.dart';
import '../services/api_service.dart';
import 'dart:developer' as developer;

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
  String? _error;

  // Controllers for text fields
  late TextEditingController _yoloMinSizeController;
  late TextEditingController _yoloConfThreshController;
  late TextEditingController _yoloMaxDetsController;
  late TextEditingController _yoloModelController;
  late TextEditingController _classifierModelController;
  late TextEditingController _soundFileController;
  late TextEditingController _fileStabilizationController;
  bool _playSound = false;
  double _volume = 80.0;
  List<Map<String, dynamic>> _availableModels = [];
  List<Map<String, dynamic>> _availableSounds = [];
  Timer? _debounceTimer;

  @override
  void initState() {
    super.initState();
    _yoloMinSizeController = TextEditingController();
    _yoloConfThreshController = TextEditingController();
    _yoloMaxDetsController = TextEditingController();
    _yoloModelController = TextEditingController();
    _classifierModelController = TextEditingController();
    _soundFileController = TextEditingController();
    _fileStabilizationController = TextEditingController();
    _loadSettings();
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _yoloMinSizeController.dispose();
    _yoloConfThreshController.dispose();
    _yoloMaxDetsController.dispose();
    _yoloModelController.dispose();
    _classifierModelController.dispose();
    _soundFileController.dispose();
    _fileStabilizationController.dispose();
    super.dispose();
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
        _soundFileController.text = settings.deterrentSoundFile;
        _fileStabilizationController.text = settings.fileStabilizationExtraWait
            .toString();
        _playSound = settings.playSound;
        _volume = settings.volume.toDouble();
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
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
        deterrentSoundFile: _soundFileController.text,
        fileStabilizationExtraWait:
            double.tryParse(_fileStabilizationController.text) ?? 2.0,
        playSound: _playSound,
        volume: _volume.round(),
      );

      final apiService = context.read<ApiService>();
      await apiService.updateSettings(updatedSettings);

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

      final selectedSound = await showDialog<String>(
        context: context,
        builder: (BuildContext context) {
          return AlertDialog(
            title: const Text('Select Sound File'),
            content: SizedBox(
              width: double.maxFinite,
              child: ListView.builder(
                shrinkWrap: true,
                itemCount: _availableSounds.length,
                itemBuilder: (context, index) {
                  final sound = _availableSounds[index];
                  final soundName = sound['name'] as String;
                  final sizeMb = sound['size_mb'] as double?;

                  return ListTile(
                    title: Text(soundName),
                    subtitle: Text(
                      sizeMb != null ? '${sizeMb.toStringAsFixed(2)} MB' : '',
                      style: const TextStyle(color: Colors.blue),
                    ),
                    leading: const Icon(Icons.music_note, color: Colors.blue),
                    trailing: soundName == _soundFileController.text
                        ? const Icon(Icons.check, color: Colors.blue)
                        : null,
                    onTap: () {
                      Navigator.of(context).pop(soundName);
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

      if (selectedSound != null) {
        setState(() {
          _soundFileController.text = selectedSound;
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
            TextField(
              controller: _soundFileController,
              decoration: InputDecoration(
                labelText: 'Deterrent Sound File',
                hintText: 'deterrent.wav',
                helperText: 'Path to sound file to play when puma detected',
                border: const OutlineInputBorder(),
                suffixIcon: IconButton(
                  icon: const Icon(Icons.folder_open),
                  onPressed: _showSoundPicker,
                  tooltip: 'Browse available sounds',
                ),
              ),
              readOnly: false,
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _showSoundPicker,
              icon: const Icon(Icons.list),
              label: const Text('Choose from Available Sounds'),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.all(12),
              ),
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
          ],
        ),
      ),
    );
  }
}
