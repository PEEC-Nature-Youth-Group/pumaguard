import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/status.dart';
import '../models/service_status.dart';
import '../services/api_service.dart';
import 'settings_screen.dart';
import 'directories_screen.dart';
import 'image_browser_screen.dart';
import 'devices_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  Status? _status;
  bool _isLoading = true;
  String? _error;

  List<ServiceStatus> _services = [];
  bool _isLoadingServices = false;
  // Tracks which service names currently have a restart in progress.
  final Set<String> _restartingServices = {};
  bool _isPoweringOff = false;

  @override
  void initState() {
    super.initState();
    _loadStatus();
    _loadServices();
  }

  @override
  void dispose() {
    super.dispose();
  }

  Future<void> _refresh() async {
    await Future.wait([_loadStatus(), _loadServices()]);
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

  Future<void> _loadServices() async {
    setState(() => _isLoadingServices = true);
    try {
      final apiService = context.read<ApiService>();
      final services = await apiService.getServices();
      if (mounted) {
        setState(() {
          _services = services;
          _isLoadingServices = false;
        });
      }
    } catch (e) {
      // Service status is supplementary – don't block the whole page on error.
      if (mounted) {
        setState(() {
          _services = [];
          _isLoadingServices = false;
        });
      }
    }
  }

  Future<void> _restartService(String serviceName) async {
    setState(() => _restartingServices.add(serviceName));
    try {
      final apiService = context.read<ApiService>();
      final updated = await apiService.restartService(serviceName);
      if (mounted) {
        setState(() {
          _services = [
            for (final s in _services) s.name == serviceName ? updated : s,
          ];
          _restartingServices.remove(serviceName);
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$serviceName restarted successfully'),
            backgroundColor: Colors.green,
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _restartingServices.remove(serviceName));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to restart $serviceName: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
            duration: const Duration(seconds: 5),
          ),
        );
      }
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
          _buildServicesCard(),
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

  // -------------------------------------------------------------------------
  // Infrastructure services card
  // -------------------------------------------------------------------------

  Widget _buildServicesCard() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  'Infrastructure Services',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const Spacer(),
                if (_isLoadingServices)
                  const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                else
                  IconButton(
                    icon: const Icon(Icons.refresh),
                    tooltip: 'Refresh service status',
                    visualDensity: VisualDensity.compact,
                    onPressed: _loadServices,
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Wi-Fi access point and DHCP/DNS services required for '
              'camera connectivity.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            if (_isLoadingServices && _services.isEmpty)
              const Center(
                child: Padding(
                  padding: EdgeInsets.symmetric(vertical: 16),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (_services.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  children: [
                    Icon(
                      Icons.info_outline,
                      size: 16,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Service status unavailable',
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              )
            else
              ...List.generate(_services.length, (i) {
                final service = _services[i];
                return Column(
                  children: [
                    if (i > 0) const Divider(height: 1),
                    _buildServiceTile(service),
                  ],
                );
              }),
          ],
        ),
      ),
    );
  }

  Widget _buildServiceTile(ServiceStatus service) {
    final isRestarting = _restartingServices.contains(service.name);

    final Color stateColor;
    final IconData stateIcon;
    if (!service.available) {
      stateColor = Theme.of(context).colorScheme.onSurfaceVariant;
      stateIcon = Icons.help_outline;
    } else if (service.active) {
      stateColor = Colors.green;
      stateIcon = Icons.check_circle_outline;
    } else if (service.state == 'failed') {
      stateColor = Theme.of(context).colorScheme.error;
      stateIcon = Icons.error_outline;
    } else {
      stateColor = Colors.orange;
      stateIcon = Icons.warning_amber_outlined;
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        children: [
          Icon(stateIcon, color: stateColor, size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  service.displayName,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    _buildStateChip(service.stateLabel, stateColor),
                    if (service.available && !service.enabled) ...[
                      const SizedBox(width: 6),
                      _buildStateChip(
                        'Disabled on boot',
                        Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          if (service.available)
            isRestarting
                ? const SizedBox(
                    width: 32,
                    height: 32,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Tooltip(
                    message: 'Restart ${service.name}',
                    child: OutlinedButton.icon(
                      onPressed: () => _confirmRestart(service),
                      icon: const Icon(Icons.restart_alt, size: 16),
                      label: const Text('Restart'),
                      style: OutlinedButton.styleFrom(
                        visualDensity: VisualDensity.compact,
                        foregroundColor: service.active
                            ? null
                            : Theme.of(context).colorScheme.error,
                        side: service.active
                            ? null
                            : BorderSide(
                                color: Theme.of(context).colorScheme.error,
                              ),
                      ),
                    ),
                  ),
        ],
      ),
    );
  }

  Widget _buildStateChip(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: color,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  Future<void> _confirmRestart(ServiceStatus service) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Restart ${service.name}?'),
        content: Text(
          'This will briefly interrupt Wi-Fi connectivity for connected '
          'cameras.\n\nAre you sure you want to restart '
          '"${service.displayName}"?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Restart'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await _restartService(service.name);
    }
  }

  Future<void> _poweroff() async {
    setState(() => _isPoweringOff = true);
    try {
      final apiService = context.read<ApiService>();
      await apiService.poweroff();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('System is powering off…'),
            backgroundColor: Colors.orange,
            duration: Duration(seconds: 5),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isPoweringOff = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to power off: $e'),
            backgroundColor: Theme.of(context).colorScheme.error,
            duration: const Duration(seconds: 5),
          ),
        );
      }
    }
  }

  Future<void> _confirmPoweroff() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Power Off Device?'),
        content: const Text(
          'This will shut down the device completely. '
          'You will need physical access to turn it back on.\n\n'
          'Are you sure you want to power off?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(ctx).colorScheme.error,
              foregroundColor: Theme.of(ctx).colorScheme.onError,
            ),
            child: const Text('Power Off'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await _poweroff();
    }
  }

  // -------------------------------------------------------------------------

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
              icon: Icons.devices,
              label: 'Devices',
              description: 'Manage cameras and smart plugs',
              onTap: () {
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => const DevicesScreen(),
                  ),
                ).then((_) => _refresh());
              },
            ),
            const Divider(),
            _buildActionButton(
              icon: Icons.power_settings_new,
              label: 'Power Off',
              description: 'Shut down the device',
              onTap: _isPoweringOff ? null : _confirmPoweroff,
              isDestructive: true,
              isLoading: _isPoweringOff,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required String description,
    required VoidCallback? onTap,
    bool isDestructive = false,
    bool isLoading = false,
  }) {
    final Color iconBgColor = isDestructive
        ? Theme.of(context).colorScheme.errorContainer
        : Theme.of(context).colorScheme.primaryContainer;
    final Color iconColor = isDestructive
        ? Theme.of(context).colorScheme.error
        : Theme.of(context).colorScheme.primary;

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
                color: iconBgColor,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: iconColor),
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
            if (isLoading)
              const SizedBox(
                width: 20,
                height: 20,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            else
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
            _buildInfoRow('Version', _status?.version ?? 'Unknown'),
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
            const SizedBox(height: 12),
            _buildInfoRow('Uptime', _status?.uptimeFormatted ?? 'Unknown'),
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
