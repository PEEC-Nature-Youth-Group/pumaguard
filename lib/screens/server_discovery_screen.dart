import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import '../services/mdns_service.dart';

class ServerDiscoveryScreen extends StatefulWidget {
  const ServerDiscoveryScreen({super.key});

  @override
  State<ServerDiscoveryScreen> createState() => _ServerDiscoveryScreenState();
}

class _ServerDiscoveryScreenState extends State<ServerDiscoveryScreen> {
  final MdnsService _mdnsService = MdnsService();
  final TextEditingController _hostnameController = TextEditingController();
  bool _isDiscovering = false;
  String? _statusMessage;
  String? _manualUrl;

  @override
  void initState() {
    super.initState();
    _startDiscovery();
  }

  @override
  void dispose() {
    _mdnsService.dispose();
    _hostnameController.dispose();
    super.dispose();
  }

  Future<void> _startDiscovery() async {
    setState(() {
      _isDiscovering = true;
      _statusMessage = 'Searching for Pumaguard servers...';
    });

    try {
      await _mdnsService.discoverServers();
      setState(() {
        _isDiscovering = false;
        _statusMessage = _mdnsService.servers.isEmpty
            ? 'No servers found. Make sure mDNS is enabled on the server.'
            : 'Found ${_mdnsService.servers.length} server(s)';
      });
    } catch (e) {
      setState(() {
        _isDiscovering = false;
        _statusMessage = 'Discovery failed: $e';
      });
    }
  }

  Future<void> _connectToServer(PumaguardServer server) async {
    final apiService = context.read<ApiService>();

    // Show connecting dialog
    if (!mounted) return;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const AlertDialog(
        content: Row(
          children: [
            CircularProgressIndicator(),
            SizedBox(width: 16),
            Text('Connecting...'),
          ],
        ),
      ),
    );

    try {
      // Update API base URL
      apiService.setBaseUrl(server.baseUrl);

      // Test connection
      await apiService.getStatus();

      if (!mounted) return;
      Navigator.of(context).pop(); // Close connecting dialog
      Navigator.of(context).pop(); // Return to previous screen

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Connected to ${server.name}'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      Navigator.of(context).pop(); // Close connecting dialog

      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Connection Failed'),
          content: Text('Could not connect to ${server.name}: $e'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    }
  }

  Future<void> _resolveAndConnect() async {
    final hostname = _hostnameController.text.trim();
    if (hostname.isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Please enter a hostname')));
      return;
    }

    setState(() {
      _statusMessage = 'Resolving $hostname...';
    });

    try {
      final ip = await _mdnsService.resolveLocalHostname(hostname);
      if (ip == null) {
        setState(() {
          _statusMessage = 'Could not resolve $hostname';
        });
        return;
      }

      final server = PumaguardServer(
        name: hostname.replaceAll('.local', ''),
        hostname: hostname,
        ip: ip,
        port: 5000, // Default port
        properties: {},
      );

      await _connectToServer(server);
    } catch (e) {
      setState(() {
        _statusMessage = 'Error: $e';
      });
    }
  }

  Future<void> _connectManual() async {
    if (_manualUrl == null || _manualUrl!.isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Please enter a URL')));
      return;
    }

    final apiService = context.read<ApiService>();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => const AlertDialog(
        content: Row(
          children: [
            CircularProgressIndicator(),
            SizedBox(width: 16),
            Text('Connecting...'),
          ],
        ),
      ),
    );

    try {
      apiService.setBaseUrl(_manualUrl!);
      await apiService.getStatus();

      if (!mounted) return;
      Navigator.of(context).pop(); // Close connecting dialog
      Navigator.of(context).pop(); // Return to previous screen

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Connected successfully'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      Navigator.of(context).pop(); // Close connecting dialog

      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Connection Failed'),
          content: Text('Could not connect: $e'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('OK'),
            ),
          ],
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Server Discovery'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _isDiscovering ? null : _startDiscovery,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Status message
            if (_statusMessage != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Row(
                    children: [
                      if (_isDiscovering)
                        const Padding(
                          padding: EdgeInsets.only(right: 16.0),
                          child: SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        ),
                      Expanded(
                        child: Text(
                          _statusMessage!,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 16),

            // Discovered servers
            if (_mdnsService.servers.isNotEmpty) ...[
              Text(
                'Discovered Servers',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              ...(_mdnsService.servers.map((server) {
                return Card(
                  child: ListTile(
                    leading: const Icon(Icons.computer, size: 40),
                    title: Text(
                      server.name,
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('IP: ${server.ip}:${server.port}'),
                        Text('Hostname: ${server.hostname}'),
                        if (server.properties['version'] != null)
                          Text('Version: ${server.properties['version']}'),
                      ],
                    ),
                    trailing: ElevatedButton(
                      onPressed: () => _connectToServer(server),
                      child: const Text('Connect'),
                    ),
                    isThreeLine: true,
                  ),
                );
              })),
              const SizedBox(height: 24),
            ],

            // Manual hostname entry
            Text(
              'Connect by Hostname',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextField(
                      controller: _hostnameController,
                      decoration: const InputDecoration(
                        labelText: 'Hostname',
                        hintText: 'pumaguard.local',
                        helperText: 'Enter .local hostname or IP address',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    ElevatedButton.icon(
                      onPressed: _resolveAndConnect,
                      icon: const Icon(Icons.search),
                      label: const Text('Resolve & Connect'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Manual URL entry
            Text(
              'Manual Connection',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    TextField(
                      decoration: const InputDecoration(
                        labelText: 'Server URL',
                        hintText: 'http://192.168.1.100:5000',
                        helperText: 'Enter full URL with port',
                        border: OutlineInputBorder(),
                      ),
                      onChanged: (value) => _manualUrl = value,
                    ),
                    const SizedBox(height: 12),
                    ElevatedButton.icon(
                      onPressed: _connectManual,
                      icon: const Icon(Icons.link),
                      label: const Text('Connect'),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Help text
            Card(
              color: Colors.blue.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.info_outline, color: Colors.blue.shade700),
                        const SizedBox(width: 8),
                        Text(
                          'Help',
                          style: Theme.of(context).textTheme.titleMedium
                              ?.copyWith(color: Colors.blue.shade700),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      '• mDNS discovery works on local networks\n'
                      '• Make sure the server has mDNS enabled\n'
                      '• Default hostname is "pumaguard.local"\n'
                      '• If discovery fails, use manual connection',
                      style: TextStyle(fontSize: 13),
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
}
