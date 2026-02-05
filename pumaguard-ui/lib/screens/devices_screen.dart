import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:web/web.dart' as web;
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../models/camera.dart';
import '../models/plug.dart';

class DevicesScreen extends StatefulWidget {
  const DevicesScreen({super.key});

  @override
  State<DevicesScreen> createState() => _DevicesScreenState();
}

class _DevicesScreenState extends State<DevicesScreen> {
  List<Camera> _cameras = [];
  List<Plug> _plugs = [];
  bool _isLoading = true;
  String? _error;
  final Map<String, Plug> _shellyStatus = {};
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _loadDevices();
    _startAutoRefresh();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }

  void _startAutoRefresh() {
    // Refresh Shelly status every 5 seconds
    _refreshTimer = Timer.periodic(const Duration(seconds: 5), (timer) {
      if (mounted && _plugs.isNotEmpty) {
        _loadShellyStatus();
      }
    });
  }

  Future<void> _loadDevices() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final apiService = Provider.of<ApiService>(context, listen: false);

      // Load cameras and plugs in parallel
      final results = await Future.wait([
        apiService.getCameras(),
        apiService.getPlugs(),
      ]);

      if (mounted) {
        setState(() {
          _cameras = results[0] as List<Camera>;
          _plugs = results[1] as List<Plug>;
          _isLoading = false;
        });

        // Load Shelly status for connected plugs
        await _loadShellyStatus();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _loadShellyStatus() async {
    final apiService = Provider.of<ApiService>(context, listen: false);

    for (final plug in _plugs) {
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
            '[DevicesScreen._loadShellyStatus] Error loading Shelly status for ${plug.macAddress}: $e',
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

  Future<void> _openCamera(Camera camera) async {
    try {
      debugPrint(
        '[DevicesScreen._openCamera] Opening camera: ${camera.displayName}',
      );

      if (camera.ipAddress.isEmpty) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Invalid camera IP address.'),
            duration: Duration(seconds: 3),
          ),
        );
        return;
      }

      // Add http:// if no scheme is present
      String urlToOpen = camera.ipAddress;
      if (!camera.ipAddress.startsWith('http://') &&
          !camera.ipAddress.startsWith('https://')) {
        urlToOpen = 'http://${camera.ipAddress}';
      }
      debugPrint('[DevicesScreen._openCamera] URL to open: "$urlToOpen"');

      // On web, use native JavaScript window.open()
      if (kIsWeb) {
        web.window.open(urlToOpen, '_blank');
        debugPrint('[DevicesScreen._openCamera] URL opened successfully');
      } else {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Opening camera URL is only supported on web currently.',
            ),
            duration: Duration(seconds: 3),
          ),
        );
      }
    } catch (e, stackTrace) {
      debugPrint('[DevicesScreen._openCamera] Error: $e');
      debugPrint('[DevicesScreen._openCamera] Stack trace: $stackTrace');
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error opening camera: $e'),
          duration: const Duration(seconds: 3),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _setPlugMode(Plug plug, String mode) async {
    try {
      final apiService = Provider.of<ApiService>(context, listen: false);
      await apiService.setPlugMode(plug.macAddress, mode);

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${plug.displayName} set to $mode'),
          duration: const Duration(seconds: 2),
        ),
      );

      // Reload devices to get updated state
      await _loadDevices();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error setting plug mode: $e'),
          duration: const Duration(seconds: 3),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Devices'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadDevices,
            tooltip: 'Refresh',
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

    if (_error != null) {
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
              'Failed to Load Devices',
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
              onPressed: _loadDevices,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_cameras.isEmpty && _plugs.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.devices_other,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              'No Devices Found',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                'No cameras or plugs have been detected yet.',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ),
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: _loadDevices,
              icon: const Icon(Icons.refresh),
              label: const Text('Refresh'),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadDevices,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_cameras.isNotEmpty) ...[
              _buildCamerasSection(),
              const SizedBox(height: 24),
            ],
            if (_plugs.isNotEmpty) _buildPlugsSection(),
          ],
        ),
      ),
    );
  }

  Widget _buildCamerasSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.videocam,
                  color: Theme.of(context).colorScheme.primary,
                ),
                const SizedBox(width: 8),
                Text('Cameras', style: Theme.of(context).textTheme.titleLarge),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '${_cameras.length}',
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onPrimaryContainer,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ..._cameras.asMap().entries.map((entry) {
              final camera = entry.value;
              final isLast = entry.key == _cameras.length - 1;
              return Column(
                children: [
                  _buildCameraListItem(camera),
                  if (!isLast) const Divider(),
                ],
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildCameraListItem(Camera camera) {
    final isConnected = camera.isConnected;
    final statusColor = isConnected ? Colors.green : Colors.grey;
    final statusText = isConnected ? 'Connected' : 'Disconnected';

    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
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
                style: TextStyle(color: statusColor, fontSize: 12),
              ),
            ],
          ),
        ],
      ),
      trailing: IconButton(
        icon: const Icon(Icons.open_in_new),
        onPressed: () => _openCamera(camera),
        tooltip: 'Open Camera UI',
      ),
      onTap: () => _openCamera(camera),
    );
  }

  Widget _buildPlugsSection() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.power, color: Theme.of(context).colorScheme.primary),
                const SizedBox(width: 8),
                Text(
                  'Smart Plugs',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '${_plugs.length}',
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onPrimaryContainer,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ..._plugs.asMap().entries.map((entry) {
              final plug = entry.value;
              final isLast = entry.key == _plugs.length - 1;
              return Column(
                children: [
                  _buildPlugListItem(plug),
                  if (!isLast) const Divider(),
                ],
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildPlugListItem(Plug plug) {
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
    final isOutputOn = hasShelly ? (shellyPlug.output ?? false) : false;
    final outputColor = isOutputOn ? Colors.green : Colors.grey;

    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
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
                style: TextStyle(color: statusColor, fontSize: 12),
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
                  isOutputOn ? Icons.lightbulb : Icons.lightbulb_outline,
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
                Icon(Icons.flash_on, size: 14, color: Colors.orange),
                const SizedBox(width: 4),
                Text(
                  '${shellyPlug.apower?.toStringAsFixed(1) ?? '0.0'}W',
                  style: const TextStyle(fontSize: 12),
                ),
                const SizedBox(width: 12),
                Icon(Icons.electric_bolt, size: 14, color: Colors.blue),
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
                Icon(Icons.show_chart, size: 14, color: Colors.purple),
                const SizedBox(width: 4),
                Text(
                  '${shellyPlug.current?.toStringAsFixed(2) ?? '0.00'}A',
                  style: const TextStyle(fontSize: 12),
                ),
                if (shellyPlug.temperature != null &&
                    shellyPlug.temperature!['tC'] != null) ...[
                  const SizedBox(width: 12),
                  Icon(Icons.thermostat, size: 14, color: Colors.red),
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
      trailing: PopupMenuButton<String>(
        icon: const Icon(Icons.more_vert),
        tooltip: 'Plug Mode',
        onSelected: (String mode) => _setPlugMode(plug, mode),
        itemBuilder: (BuildContext context) => <PopupMenuEntry<String>>[
          PopupMenuItem<String>(
            value: 'on',
            child: Row(
              children: [
                Icon(Icons.power_settings_new, color: Colors.green, size: 20),
                const SizedBox(width: 12),
                const Text('Always On'),
              ],
            ),
          ),
          PopupMenuItem<String>(
            value: 'off',
            child: Row(
              children: [
                Icon(Icons.power_off, color: Colors.grey, size: 20),
                const SizedBox(width: 12),
                const Text('Always Off'),
              ],
            ),
          ),
          PopupMenuItem<String>(
            value: 'automatic',
            child: Row(
              children: [
                Icon(Icons.auto_mode, color: Colors.orange, size: 20),
                const SizedBox(width: 12),
                const Text('Automatic'),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
