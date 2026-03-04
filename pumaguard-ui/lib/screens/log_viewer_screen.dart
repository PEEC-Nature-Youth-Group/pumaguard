import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../services/api_service.dart';

/// Identifies which journalctl scope to fetch logs for.
enum LogScope {
  /// `journalctl --unit pumaguard --since "1 hour ago"`
  unit,

  /// `journalctl --since "1 hour ago"`
  all,
}

extension LogScopeExtension on LogScope {
  String get apiValue {
    switch (this) {
      case LogScope.unit:
        return 'unit';
      case LogScope.all:
        return 'all';
    }
  }

  String get label {
    switch (this) {
      case LogScope.unit:
        return 'PumaGuard Unit Logs';
      case LogScope.all:
        return 'All System Logs';
    }
  }

  String command(String since) {
    final sinceArg = '--since "$since"';
    switch (this) {
      case LogScope.unit:
        return 'journalctl --unit pumaguard $sinceArg';
      case LogScope.all:
        return 'journalctl $sinceArg';
    }
  }
}

/// Predefined time-window options presented to the user as chips.
class _TimeWindow {
  final String label;

  /// Value passed to journalctl --since and to the API's `since` parameter.
  final String since;

  const _TimeWindow(this.label, this.since);
}

const List<_TimeWindow> _kTimeWindows = [
  _TimeWindow('Last 15 min', '15 minutes ago'),
  _TimeWindow('Last hour', '1 hour ago'),
  _TimeWindow('Last 6 h', '6 hours ago'),
  _TimeWindow('Last 24 h', '24 hours ago'),
  _TimeWindow('Last 7 days', '7 days ago'),
  _TimeWindow('All', ''),
];

class LogViewerScreen extends StatefulWidget {
  final ApiService apiService;
  final LogScope scope;

  const LogViewerScreen({
    super.key,
    required this.apiService,
    required this.scope,
  });

  @override
  State<LogViewerScreen> createState() => _LogViewerScreenState();
}

class _LogViewerScreenState extends State<LogViewerScreen> {
  List<String> _logLines = [];
  bool _isLoading = true;
  String? _error;
  final ScrollController _scrollController = ScrollController();

  // Default to "last hour" – index 1 in _kTimeWindows.
  int _selectedWindowIndex = 1;

  _TimeWindow get _currentWindow => _kTimeWindows[_selectedWindowIndex];

  @override
  void initState() {
    super.initState();
    _loadLogs();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadLogs() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final result = await widget.apiService.getLogs(
        scope: widget.scope.apiValue,
        since: _currentWindow.since,
      );
      final rawLines = result['logs'];
      final lines = rawLines is List
          ? rawLines.map((e) => e.toString()).toList()
          : <String>[];

      if (mounted) {
        setState(() {
          _logLines = lines;
          _isLoading = false;
        });

        WidgetsBinding.instance.addPostFrameCallback((_) {
          _jumpToBottom();
        });
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

  /// Instantly positions the list at the bottom. Used after a fresh load so
  /// the user never sees the top of the list flash before scrolling down.
  void _jumpToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.jumpTo(_scrollController.position.maxScrollExtent);
    }
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  void _scrollToTop() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        0,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  Future<void> _copyToClipboard() async {
    final text = _logLines.join('\n');
    await Clipboard.setData(ClipboardData(text: text));
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Copied ${_logLines.length} log lines to clipboard'),
          duration: const Duration(seconds: 2),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.scope.label),
        actions: [
          if (!_isLoading && _error == null) ...[
            IconButton(
              icon: const Icon(Icons.vertical_align_top),
              tooltip: 'Scroll to top',
              onPressed: _scrollToTop,
            ),
            IconButton(
              icon: const Icon(Icons.vertical_align_bottom),
              tooltip: 'Scroll to bottom',
              onPressed: _scrollToBottom,
            ),
            IconButton(
              icon: const Icon(Icons.copy),
              tooltip: 'Copy all logs',
              onPressed: _copyToClipboard,
            ),
          ],
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh logs',
            onPressed: _isLoading ? null : _loadLogs,
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildCommandBanner(),
          _buildTimeWindowChips(),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildCommandBanner() {
    return Container(
      color: Theme.of(context).colorScheme.surfaceContainerHighest,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          Icon(
            Icons.terminal,
            size: 16,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              widget.scope.command(
                _currentWindow.since.isEmpty ? 'all' : _currentWindow.since,
              ),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontFamily: 'monospace',
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          if (!_isLoading && _error == null)
            Text(
              '${_logLines.length} lines',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildTimeWindowChips() {
    return Container(
      color: Theme.of(context).colorScheme.surface,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: List.generate(_kTimeWindows.length, (index) {
            final window = _kTimeWindows[index];
            final isSelected = index == _selectedWindowIndex;
            return Padding(
              padding: const EdgeInsets.only(right: 6),
              child: ChoiceChip(
                label: Text(window.label),
                selected: isSelected,
                onSelected: (_) {
                  if (!isSelected) {
                    setState(() => _selectedWindowIndex = index);
                    _loadLogs();
                  }
                },
              ),
            );
          }),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading logs...'),
          ],
        ),
      );
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
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
                'Failed to Load Logs',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: _loadLogs,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (_logLines.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.article_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              'No log entries found for "${_currentWindow.label}"',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      color: const Color(0xFF1E1E1E),
      child: Scrollbar(
        controller: _scrollController,
        thumbVisibility: true,
        child: ListView.builder(
          controller: _scrollController,
          padding: const EdgeInsets.all(8),
          itemCount: _logLines.length,
          itemBuilder: (context, index) {
            return _LogLine(line: _logLines[index]);
          },
        ),
      ),
    );
  }
}

class _LogLine extends StatelessWidget {
  final String line;

  const _LogLine({required this.line});

  Color _lineColor(String line) {
    final lower = line.toLowerCase();
    if (lower.contains(' err ') ||
        lower.contains('[error]') ||
        lower.contains('error:') ||
        lower.contains('critical') ||
        lower.contains('emerg') ||
        lower.contains('alert')) {
      return const Color(0xFFFF6B6B);
    }
    if (lower.contains(' warn') ||
        lower.contains('[warning]') ||
        lower.contains('warning:')) {
      return const Color(0xFFFFD93D);
    }
    if (lower.contains('[info]') ||
        lower.contains('info:') ||
        lower.contains(' notice')) {
      return const Color(0xFF6BCB77);
    }
    if (lower.contains('[debug]') || lower.contains('debug:')) {
      return const Color(0xFF74B9FF);
    }
    return const Color(0xFFCDD3DE);
  }

  @override
  Widget build(BuildContext context) {
    return SelectableText(
      line,
      style: TextStyle(
        fontFamily: 'monospace',
        fontSize: 12,
        height: 1.5,
        color: _lineColor(line),
      ),
    );
  }
}
