import 'package:flutter/material.dart';
import '../services/api_service.dart';

class WifiSettingsScreen extends StatefulWidget {
  final ApiService apiService;

  const WifiSettingsScreen({super.key, required this.apiService});

  @override
  State<WifiSettingsScreen> createState() => _WifiSettingsScreenState();
}

class _WifiSettingsScreenState extends State<WifiSettingsScreen> {
  bool _isLoading = false;
  bool _isScanning = false;
  String? _errorMessage;
  String? _successMessage;

  String _currentMode = 'unknown';
  String? _currentSsid;
  bool _isConnected = false;

  List<WifiNetwork> _networks = [];
  final TextEditingController _passwordController = TextEditingController();
  final TextEditingController _apSsidController = TextEditingController();
  final TextEditingController _apPasswordController = TextEditingController();

  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();
    _loadCurrentMode();
  }

  @override
  void dispose() {
    _passwordController.dispose();
    _apSsidController.dispose();
    _apPasswordController.dispose();
    super.dispose();
  }

  Future<void> _loadCurrentMode() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final response = await widget.apiService.getWifiMode();
      setState(() {
        _currentMode = response['mode'] as String? ?? 'unknown';
        _currentSsid = response['ssid'] as String?;
        _isConnected = response['connected'] as bool? ?? false;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to load WiFi mode: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _scanNetworks() async {
    setState(() {
      _isScanning = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      final response = await widget.apiService.scanWifiNetworks();
      final networksJson = response['networks'] as List<dynamic>;

      setState(() {
        _networks = networksJson
            .map((json) => WifiNetwork.fromJson(json as Map<String, dynamic>))
            .toList();
        _isScanning = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to scan networks: $e';
        _isScanning = false;
      });
    }
  }

  Future<void> _connectToNetwork(
    String ssid,
    String password,
    bool isSecured,
  ) async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      await widget.apiService.setWifiMode(
        mode: 'client',
        ssid: ssid,
        password: isSecured ? password : null,
      );

      setState(() {
        _successMessage = 'Successfully connected to $ssid';
        _isLoading = false;
        _passwordController.clear();
      });

      // Reload current mode after a short delay
      await Future.delayed(const Duration(seconds: 2));
      await _loadCurrentMode();
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to connect: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _enableApMode() async {
    final ssid = _apSsidController.text.trim();
    final password = _apPasswordController.text.trim();

    if (ssid.isEmpty) {
      setState(() {
        _errorMessage = 'SSID cannot be empty';
      });
      return;
    }

    if (password.isNotEmpty && password.length < 8) {
      setState(() {
        _errorMessage = 'Password must be at least 8 characters';
      });
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
      _successMessage = null;
    });

    try {
      await widget.apiService.setWifiMode(
        mode: 'ap',
        ssid: ssid,
        password: password.isEmpty ? null : password,
      );

      setState(() {
        _successMessage = 'Access Point enabled: $ssid';
        _isLoading = false;
        _apSsidController.clear();
        _apPasswordController.clear();
      });

      // Reload current mode after a short delay
      await Future.delayed(const Duration(seconds: 2));
      await _loadCurrentMode();
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to enable AP mode: $e';
        _isLoading = false;
      });
    }
  }

  void _showPasswordDialog(WifiNetwork network) {
    _passwordController.clear();

    showDialog(
      context: context,
      builder: (BuildContext context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              title: Text('Connect to ${network.ssid}'),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Signal: ${network.signal}%',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 16),
                  if (network.secured) ...[
                    TextField(
                      controller: _passwordController,
                      obscureText: _obscurePassword,
                      decoration: InputDecoration(
                        labelText: 'Password',
                        border: const OutlineInputBorder(),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscurePassword
                                ? Icons.visibility
                                : Icons.visibility_off,
                          ),
                          onPressed: () {
                            setDialogState(() {
                              _obscurePassword = !_obscurePassword;
                            });
                          },
                        ),
                      ),
                    ),
                  ] else ...[
                    Text(
                      'This is an open network (no password required)',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Theme.of(context).colorScheme.secondary,
                      ),
                    ),
                  ],
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () {
                    Navigator.of(context).pop();
                    _connectToNetwork(
                      network.ssid,
                      _passwordController.text,
                      network.secured,
                    );
                  },
                  child: const Text('Connect'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('WiFi Settings')),
      body: _isLoading && _networks.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Error/Success Messages
                  if (_errorMessage != null) ...[
                    Card(
                      color: Theme.of(context).colorScheme.errorContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Row(
                          children: [
                            Icon(
                              Icons.error_outline,
                              color: Theme.of(context).colorScheme.error,
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _errorMessage!,
                                style: TextStyle(
                                  color: Theme.of(context).colorScheme.error,
                                ),
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.close),
                              onPressed: () {
                                setState(() => _errorMessage = null);
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],
                  if (_successMessage != null) ...[
                    Card(
                      color: Colors.green.shade50,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Row(
                          children: [
                            const Icon(Icons.check_circle, color: Colors.green),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _successMessage!,
                                style: const TextStyle(color: Colors.green),
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.close),
                              onPressed: () {
                                setState(() => _successMessage = null);
                              },
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                  ],

                  // Current Status
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(
                                _currentMode == 'ap'
                                    ? Icons.wifi_tethering
                                    : Icons.wifi,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                'Current Status',
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          _buildStatusRow(
                            'Mode',
                            _getModeDisplay(_currentMode),
                          ),
                          const SizedBox(height: 8),
                          if (_currentSsid != null)
                            _buildStatusRow('Network', _currentSsid!),
                          const SizedBox(height: 8),
                          _buildStatusRow(
                            'Status',
                            _isConnected ? 'Connected' : 'Disconnected',
                            statusColor: _isConnected
                                ? Colors.green
                                : Colors.grey,
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),

                  // Mode Selection Tabs
                  DefaultTabController(
                    length: 2,
                    child: Column(
                      children: [
                        TabBar(
                          tabs: const [
                            Tab(
                              icon: Icon(Icons.wifi),
                              text: 'Connect to Network',
                            ),
                            Tab(
                              icon: Icon(Icons.wifi_tethering),
                              text: 'Create Hotspot',
                            ),
                          ],
                        ),
                        SizedBox(
                          height: 500,
                          child: TabBarView(
                            children: [
                              _buildClientModeTab(),
                              _buildApModeTab(),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _buildStatusRow(String label, String value, {Color? statusColor}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.bold),
        ),
        Text(
          value,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: statusColor),
        ),
      ],
    );
  }

  String _getModeDisplay(String mode) {
    switch (mode) {
      case 'ap':
        return 'Access Point (Hotspot)';
      case 'client':
        return 'Client (Connected)';
      default:
        return 'Unknown';
    }
  }

  Widget _buildClientModeTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          FilledButton.icon(
            onPressed: _isScanning ? null : _scanNetworks,
            icon: _isScanning
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh),
            label: Text(_isScanning ? 'Scanning...' : 'Scan for Networks'),
          ),
          const SizedBox(height: 16),
          if (_networks.isEmpty && !_isScanning) ...[
            Center(
              child: Column(
                children: [
                  Icon(
                    Icons.wifi_off,
                    size: 64,
                    color: Theme.of(context).colorScheme.outline,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'No networks found',
                    style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: Theme.of(context).colorScheme.outline,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Tap the button above to scan',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.outline,
                    ),
                  ),
                ],
              ),
            ),
          ] else ...[
            Expanded(
              child: ListView.builder(
                itemCount: _networks.length,
                itemBuilder: (context, index) {
                  final network = _networks[index];
                  return Card(
                    child: ListTile(
                      leading: Icon(
                        _getSignalIcon(network.signal),
                        color: network.connected
                            ? Colors.green
                            : Theme.of(context).colorScheme.primary,
                      ),
                      title: Row(
                        children: [
                          Expanded(child: Text(network.ssid)),
                          if (network.secured)
                            Icon(
                              Icons.lock,
                              size: 16,
                              color: Theme.of(context).colorScheme.outline,
                            ),
                          if (network.connected)
                            Padding(
                              padding: const EdgeInsets.only(left: 8),
                              child: Chip(
                                label: const Text('Connected'),
                                backgroundColor: Colors.green.shade100,
                                labelStyle: const TextStyle(
                                  color: Colors.green,
                                  fontSize: 12,
                                ),
                              ),
                            ),
                        ],
                      ),
                      subtitle: Text(
                        'Signal: ${network.signal}% • ${network.security}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      trailing: network.connected
                          ? null
                          : IconButton(
                              icon: const Icon(Icons.arrow_forward),
                              onPressed: () => _showPasswordDialog(network),
                            ),
                    ),
                  );
                },
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildApModeTab() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Create your own WiFi hotspot',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Other devices will be able to connect to this network',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _apSsidController,
              decoration: const InputDecoration(
                labelText: 'Network Name (SSID)',
                hintText: 'pumaguard',
                border: OutlineInputBorder(),
                helperText: 'The name others will see',
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _apPasswordController,
              obscureText: _obscurePassword,
              decoration: InputDecoration(
                labelText: 'Password (optional)',
                hintText: 'Leave empty for open network',
                border: const OutlineInputBorder(),
                helperText: 'Minimum 8 characters if set',
                suffixIcon: IconButton(
                  icon: Icon(
                    _obscurePassword ? Icons.visibility : Icons.visibility_off,
                  ),
                  onPressed: () {
                    setState(() {
                      _obscurePassword = !_obscurePassword;
                    });
                  },
                ),
              ),
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              onPressed: _isLoading ? null : _enableApMode,
              icon: _isLoading
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.wifi_tethering),
              label: const Text('Enable Hotspot'),
            ),
            const SizedBox(height: 16),
            Card(
              color: Theme.of(context).colorScheme.surfaceContainerHighest,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          Icons.info_outline,
                          size: 20,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          'Information',
                          style: Theme.of(context).textTheme.titleSmall,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      '• Hotspot mode allows cameras and other devices to connect directly to this device\n'
                      '• You will not have internet access in hotspot mode\n'
                      '• The device IP will be 192.168.52.1\n'
                      '• To switch back, use the "Connect to Network" tab',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  IconData _getSignalIcon(int signal) {
    if (signal >= 75) {
      return Icons.signal_wifi_4_bar;
    } else if (signal >= 50) {
      return Icons.network_wifi_3_bar;
    } else if (signal >= 25) {
      return Icons.network_wifi_2_bar;
    } else {
      return Icons.network_wifi_1_bar;
    }
  }
}

class WifiNetwork {
  final String ssid;
  final int signal;
  final String security;
  final bool secured;
  final bool connected;

  WifiNetwork({
    required this.ssid,
    required this.signal,
    required this.security,
    required this.secured,
    required this.connected,
  });

  factory WifiNetwork.fromJson(Map<String, dynamic> json) {
    return WifiNetwork(
      ssid: json['ssid'] as String,
      signal: json['signal'] as int,
      security: json['security'] as String,
      secured: json['secured'] as bool,
      connected: json['connected'] as bool? ?? false,
    );
  }
}
