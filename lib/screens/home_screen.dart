import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:provider/provider.dart';
import 'package:web/web.dart' as web;
import '../models/status.dart';
import '../models/camera.dart';
import '../services/api_service.dart';
import '../version.dart';
import 'settings_screen.dart';
import 'directories_screen.dart';
import 'image_browser_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Status? _status;
  bool _isLoading = true;
  String? _error;
  List<Camera> _cameras = [];

  @override
  void initState() {
    super.initState();
    _loadStatus();
    _loadCameras();
  }

  Future<void> _refresh() async {
    await Future.wait([_loadStatus(), _loadCameras()]);
  }

  Future<void> _loadStatus() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final apiService = context.read<ApiService>();
      final status = await apiService.getStatus();
      setState(() {
        _status = status;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _loadCameras() async {
    try {
      final apiService = context.read<ApiService>();
      final cameras = await apiService.getCameras();
      setState(() {
        _cameras = cameras;
      });
    } catch (e) {
      debugPrint('[HomeScreen._loadCameras] Error loading cameras: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.pets, color: Theme.of(context).colorScheme.primary),
            const SizedBox(width: 8),
            const Text('PumaGuard'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _refresh,
            tooltip: 'Refresh Status',
          ),
        ],
      ),
      body: RefreshIndicator(onRefresh: _refresh, child: _buildBody()),
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
              'Connection Error',
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
              onPressed: _loadStatus,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildStatusCard(),
          const SizedBox(height: 16),
          _buildQuickActionsCard(),
          const SizedBox(height: 16),
          _buildInfoCard(),
        ],
      ),
    );
  }

  Widget _buildStatusCard() {
    final isRunning = _status?.isRunning ?? false;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            Icon(
              isRunning ? Icons.check_circle : Icons.warning,
              size: 64,
              color: isRunning ? Colors.green : Colors.orange,
            ),
            const SizedBox(height: 16),
            Text(
              isRunning ? 'System Running' : 'System Status Unknown',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              isRunning
                  ? 'PumaGuard is actively monitoring'
                  : 'Check system configuration',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickActionsCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Quick Actions',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            _buildActionButton(
              icon: Icons.settings,
              label: 'Settings',
              description: 'Configure YOLO and classifier parameters',
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const SettingsScreen(),
                  ),
                ).then((_) => _refresh());
              },
            ),
            const Divider(),
            _buildActionButton(
              icon: Icons.folder,
              label: 'Directories',
              description: 'Manage monitored image directories',
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const DirectoriesScreen(),
                  ),
                ).then((_) => _refresh());
              },
            ),
            const Divider(),
            _buildActionButton(
              icon: Icons.photo_library,
              label: 'Image Browser',
              description: 'Browse and download images from watched folders',
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const ImageBrowserScreen(),
                  ),
                ).then((_) => _refresh());
              },
            ),
            const Divider(),
            _buildActionButton(
              icon: Icons.videocam,
              label: 'Camera',
              description: 'Open camera web interface',
              onTap: _openCamera,
            ),
            // Show detected cameras if any
            if (_cameras.isNotEmpty) ...[
              const SizedBox(height: 16),
              const Divider(thickness: 2),
              const SizedBox(height: 8),
              Text(
                'Detected Cameras',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              ..._cameras.map((camera) {
                return Column(
                  children: [
                    _buildActionButton(
                      icon: Icons.videocam,
                      label: camera.displayName,
                      description: 'IP: ${camera.ipAddress} • ${camera.status}',
                      onTap: () => _openCameraByIp(camera.ipAddress),
                    ),
                    if (camera != _cameras.last) const Divider(),
                  ],
                );
              }),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _openCameraByIp(String ipAddress) async {
    try {
      debugPrint('[HomeScreen._openCameraByIp] Opening camera at: $ipAddress');

      if (ipAddress.isEmpty) {
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
      String urlToOpen = ipAddress;
      if (!ipAddress.startsWith('http://') &&
          !ipAddress.startsWith('https://')) {
        urlToOpen = 'http://$ipAddress';
      }
      debugPrint('[HomeScreen._openCameraByIp] URL to open: "$urlToOpen"');

      // On web, use native JavaScript window.open()
      if (kIsWeb) {
        web.window.open(urlToOpen, '_blank');
        debugPrint('[HomeScreen._openCameraByIp] URL opened successfully');
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
      debugPrint('[HomeScreen._openCameraByIp] Error: $e');
      debugPrint('[HomeScreen._openCameraByIp] Stack trace: $stackTrace');
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

  Future<void> _openCamera() async {
    try {
      debugPrint('[HomeScreen._openCamera] Starting camera open...');
      final apiService = context.read<ApiService>();
      final cameraUrl = await apiService.getCameraUrl();
      debugPrint('[HomeScreen._openCamera] Got camera URL: "$cameraUrl"');

      if (cameraUrl.isEmpty) {
        debugPrint('[HomeScreen._openCamera] Camera URL is empty');
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Camera URL not configured. Please set it in Settings.',
            ),
            duration: Duration(seconds: 3),
          ),
        );
        return;
      }

      // Parse the URL and add http:// if no scheme is present
      String urlToOpen = cameraUrl;
      if (!cameraUrl.startsWith('http://') &&
          !cameraUrl.startsWith('https://')) {
        urlToOpen = 'http://$cameraUrl';
      }
      debugPrint('[HomeScreen._openCamera] URL to open: "$urlToOpen"');

      // On web, use native JavaScript window.open()
      if (kIsWeb) {
        debugPrint('[HomeScreen._openCamera] Using window.open() for web...');
        web.window.open(urlToOpen, '_blank');
        debugPrint('[HomeScreen._openCamera] URL opened successfully');
      } else {
        // For mobile/desktop, would use url_launcher (not implemented yet)
        debugPrint(
          '[HomeScreen._openCamera] Non-web platform not yet supported',
        );
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
      debugPrint('[HomeScreen._openCamera] Error: $e');
      debugPrint('[HomeScreen._openCamera] Stack trace: $stackTrace');
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

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required String description,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: Theme.of(context).colorScheme.primary),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'System Information',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 16),
            _buildInfoRow('Backend Version', _status?.version ?? 'Unknown'),
            const SizedBox(height: 12),
            _buildInfoRow('UI Version', appVersion),
            const SizedBox(height: 12),
            _buildInfoRow(
              'Host',
              '${_status?.host ?? 'Unknown'}:${_status?.port ?? 0}',
            ),
            const SizedBox(height: 12),
            _buildInfoRow(
              'Monitored Directories',
              '${_status?.directoriesCount ?? 0}',
            ),
            const SizedBox(height: 12),
            _buildInfoRow('Status', _status?.status.toUpperCase() ?? 'UNKNOWN'),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        Text(
          value,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}
