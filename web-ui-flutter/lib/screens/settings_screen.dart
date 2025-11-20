import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/settings.dart';
import '../services/api_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  Settings? _settings;
  bool _isLoading = true;
  bool _isSaving = false;
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
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
        actions: [
          if (!_isLoading && _settings != null)
            IconButton(
              icon: _isSaving
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save),
              onPressed: _isSaving ? null : _saveSettings,
              tooltip: 'Save Settings',
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
              decoration: const InputDecoration(
                labelText: 'YOLO Model Filename',
                hintText: 'yolo_model.pt',
                helperText: 'Path to YOLO model file',
                border: OutlineInputBorder(),
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
              decoration: const InputDecoration(
                labelText: 'Classifier Model Filename',
                hintText: 'classifier_model.h5',
                helperText: 'Path to classifier model file',
                border: OutlineInputBorder(),
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
              decoration: const InputDecoration(
                labelText: 'Deterrent Sound File',
                hintText: 'deterrent.wav',
                helperText: 'Path to sound file to play when puma detected',
                border: OutlineInputBorder(),
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
              },
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
