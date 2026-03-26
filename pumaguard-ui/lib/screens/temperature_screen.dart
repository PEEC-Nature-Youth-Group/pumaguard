import 'dart:async';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../services/api_service.dart';

// ---------------------------------------------------------------------------
// Data models
// ---------------------------------------------------------------------------

/// A single sensor reading at a point in time.
class _Reading {
  final DateTime timestamp;

  /// chip name → sensor label → °C value
  final Map<String, Map<String, double>> temperatures;

  const _Reading({required this.timestamp, required this.temperatures});
}

/// A time-series for one (chip, label) pair, ready for fl_chart.
class _Series {
  final String chip;
  final String label;
  final Color color;
  final List<FlSpot> spots; // x = minutes-from-start, y = °C

  const _Series({
    required this.chip,
    required this.label,
    required this.color,
    required this.spots,
  });

  String get displayName => '$chip › $label';
}

// ---------------------------------------------------------------------------
// Palette – distinct colours for up to 12 series
// ---------------------------------------------------------------------------

const List<Color> _palette = [
  Color(0xFFE53935), // red
  Color(0xFF1E88E5), // blue
  Color(0xFF43A047), // green
  Color(0xFFFB8C00), // orange
  Color(0xFF8E24AA), // purple
  Color(0xFF00ACC1), // cyan
  Color(0xFFFFB300), // amber
  Color(0xFF6D4C41), // brown
  Color(0xFF00897B), // teal
  Color(0xFFD81B60), // pink
  Color(0xFF3949AB), // indigo
  Color(0xFF546E7A), // blue-grey
];

// ---------------------------------------------------------------------------
// Screen
// ---------------------------------------------------------------------------

class TemperatureScreen extends StatefulWidget {
  final ApiService apiService;

  const TemperatureScreen({super.key, required this.apiService});

  @override
  State<TemperatureScreen> createState() => _TemperatureScreenState();
}

class _TemperatureScreenState extends State<TemperatureScreen> {
  // -- state -----------------------------------------------------------------
  bool _loading = true;
  String? _error;

  /// How many hours of history to display.
  int _hours = 1;

  /// All parsed readings from the API.
  List<_Reading> _readings = [];

  /// Derived time-series, one per (chip, label) pair.
  List<_Series> _series = [];

  /// Which series are currently visible (toggled by the legend).
  late Set<String> _visible;

  /// Millisecond timestamp of the window start (x=0 reference = now - _hours).
  double _originMs = 0;

  // -- time span options -----------------------------------------------------
  static const List<_SpanOption> _spans = [
    _SpanOption(label: '1 h', hours: 1),
    _SpanOption(label: '3 h', hours: 3),
    _SpanOption(label: '6 h', hours: 6),
    _SpanOption(label: '12 h', hours: 12),
    _SpanOption(label: '24 h', hours: 24),
    _SpanOption(label: '3 d', hours: 72),
    _SpanOption(label: '7 d', hours: 168),
  ];

  // -- lifecycle -------------------------------------------------------------

  @override
  void initState() {
    super.initState();
    _visible = {};
    _fetchHistory();
  }

  // -- data ------------------------------------------------------------------

  Future<void> _fetchHistory() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final raw = await widget.apiService.getSensorsHistory(hours: _hours);

      final available = raw['available'] as bool? ?? false;
      if (!available) {
        setState(() {
          _loading = false;
          _error =
              'lm-sensors is not available on this device. '
              'Make sure the lm-sensors package is installed and '
              'lm-sensors.timer is running.';
        });
        return;
      }

      final rawReadings = raw['readings'] as List<dynamic>? ?? [];
      final readings = <_Reading>[];

      for (final r in rawReadings) {
        final map = r as Map<String, dynamic>;
        final ts = DateTime.tryParse(map['timestamp'] as String? ?? '');
        if (ts == null) continue;

        final sensorsRaw = map['sensors'] as Map<String, dynamic>? ?? {};
        final temps = <String, Map<String, double>>{};

        for (final chipEntry in sensorsRaw.entries) {
          final chipName = chipEntry.key;
          final chipData = chipEntry.value as Map<String, dynamic>? ?? {};
          final sensorMap = <String, double>{};

          for (final sensorEntry in chipData.entries) {
            final sensorLabel = sensorEntry.key;
            final sensorValues =
                sensorEntry.value as Map<String, dynamic>? ?? {};
            final inputVal = sensorValues['temp_input'];
            if (inputVal != null) {
              sensorMap[sensorLabel] = (inputVal as num).toDouble();
            }
          }

          if (sensorMap.isNotEmpty) {
            temps[chipName] = sensorMap;
          }
        }

        if (temps.isNotEmpty) {
          readings.add(_Reading(timestamp: ts, temperatures: temps));
        }
      }

      // Sort oldest-first (API guarantees this, but be defensive)
      readings.sort((a, b) => a.timestamp.compareTo(b.timestamp));

      final series = _buildSeries(readings);
      final allKeys = series.map((s) => s.displayName).toSet();

      setState(() {
        _readings = readings;
        _series = series;
        // Preserve visibility toggles for series that still exist;
        // new series default to visible.
        final preserved = _visible.intersection(allKeys);
        _visible = preserved.isEmpty
            ? Set.of(allKeys)
            : preserved.union(allKeys.difference(_visible));
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _loading = false;
        _error = 'Failed to load sensor history.';
      });
    }
  }

  List<_Series> _buildSeries(List<_Reading> readings) {
    if (readings.isEmpty) return [];

    // Pin the x-axis origin to (now - _hours) so the chart always covers
    // the full requested window, regardless of when the first reading arrived.
    _originMs = DateTime.now()
        .subtract(Duration(hours: _hours))
        .millisecondsSinceEpoch
        .toDouble();

    // Collect all (chip, label) pairs in stable order
    final keys = <(String, String)>[];
    for (final r in readings) {
      for (final chip in r.temperatures.keys) {
        for (final label in r.temperatures[chip]!.keys) {
          final key = (chip, label);
          if (!keys.contains(key)) keys.add(key);
        }
      }
    }

    final result = <_Series>[];
    for (var i = 0; i < keys.length; i++) {
      final (chip, label) = keys[i];
      final color = _palette[i % _palette.length];
      final spots = <FlSpot>[];

      for (final r in readings) {
        final val = r.temperatures[chip]?[label];
        if (val == null) continue;
        final xMin = (r.timestamp.millisecondsSinceEpoch - _originMs) / 60000.0;
        // Only include readings that fall within the requested window
        // (clamp slightly to avoid floating-point edge surprises).
        if (xMin < -1 || xMin > _hours * 60.0 + 1) continue;
        spots.add(FlSpot(xMin.clamp(0.0, _hours * 60.0), val));
      }

      if (spots.isNotEmpty) {
        result.add(
          _Series(chip: chip, label: label, color: color, spots: spots),
        );
      }
    }
    return result;
  }

  // -- helpers ---------------------------------------------------------------

  String _formatXAxis(double xMin) {
    final dt = DateTime.fromMillisecondsSinceEpoch(
      (_originMs + xMin * 60000).round(),
    );
    return DateFormat('HH:mm').format(dt);
  }

  double get _yMin {
    double? v;
    for (final s in _series) {
      if (!_visible.contains(s.displayName)) continue;
      for (final sp in s.spots) {
        v = v == null ? sp.y : (sp.y < v ? sp.y : v);
      }
    }
    return ((v ?? 20) - 5).floorToDouble();
  }

  double get _yMax {
    double? v;
    for (final s in _series) {
      if (!_visible.contains(s.displayName)) continue;
      for (final sp in s.spots) {
        v = v == null ? sp.y : (sp.y > v ? sp.y : v);
      }
    }
    return ((v ?? 60) + 5).ceilToDouble();
  }

  // -- build -----------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Temperature History'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh',
            onPressed: _loading ? null : _fetchHistory,
          ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildSpanSelector(),
          Expanded(child: _buildBody()),
        ],
      ),
    );
  }

  Widget _buildSpanSelector() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: _spans.map((opt) {
            final selected = opt.hours == _hours;
            return Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ChoiceChip(
                label: Text(opt.label),
                selected: selected,
                onSelected: (_) {
                  if (!selected) {
                    setState(() => _hours = opt.hours);
                    _fetchHistory();
                  }
                },
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.thermostat_outlined,
                size: 64,
                color: Colors.grey,
              ),
              const SizedBox(height: 16),
              Text(
                _error!,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _fetchHistory,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (_readings.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.thermostat_outlined, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              'No sensor data in the last $_hours hour${_hours == 1 ? '' : 's'}.\n'
              'Data is collected every 5 minutes by lm-sensors.timer.',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [_buildChart(), const SizedBox(height: 16), _buildLegend()],
      ),
    );
  }

  Widget _buildChart() {
    final visibleSeries = _series
        .where((s) => _visible.contains(s.displayName))
        .toList();

    if (visibleSeries.isEmpty) {
      return const SizedBox(
        height: 300,
        child: Center(child: Text('Select at least one series in the legend.')),
      );
    }

    // x-axis interval: aim for ~6 labels across the span
    final totalMinutes = _hours * 60.0;
    final xInterval = (totalMinutes / 6).ceilToDouble();

    return SizedBox(
      height: 300,
      child: LineChart(
        LineChartData(
          minY: _yMin,
          maxY: _yMax,
          clipData: const FlClipData.all(),
          minX: 0,
          maxX: totalMinutes,
          gridData: FlGridData(
            show: true,
            drawVerticalLine: true,
            horizontalInterval: 10,
            verticalInterval: xInterval,
            getDrawingHorizontalLine: (_) => FlLine(
              color: Colors.grey.withValues(alpha: 0.2),
              strokeWidth: 1,
            ),
            getDrawingVerticalLine: (_) => FlLine(
              color: Colors.grey.withValues(alpha: 0.2),
              strokeWidth: 1,
            ),
          ),
          borderData: FlBorderData(
            show: true,
            border: Border.all(color: Colors.grey.withValues(alpha: 0.4)),
          ),
          titlesData: FlTitlesData(
            leftTitles: AxisTitles(
              axisNameWidget: const Text('°C', style: TextStyle(fontSize: 12)),
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 40,
                interval: 10,
                getTitlesWidget: (value, meta) => Text(
                  '${value.toInt()}',
                  style: const TextStyle(fontSize: 10),
                ),
              ),
            ),
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                reservedSize: 28,
                interval: xInterval,
                getTitlesWidget: (value, meta) {
                  // Suppress labels too close to the edges to avoid overlap
                  if (value < 0 || value > totalMinutes) {
                    return const SizedBox.shrink();
                  }
                  return Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      _formatXAxis(value),
                      style: const TextStyle(fontSize: 10),
                    ),
                  );
                },
              ),
            ),
            rightTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
            topTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false),
            ),
          ),
          lineTouchData: LineTouchData(
            touchTooltipData: LineTouchTooltipData(
              getTooltipItems: (touchedSpots) {
                return touchedSpots.map((spot) {
                  final s = visibleSeries[spot.barIndex];
                  return LineTooltipItem(
                    '${s.label}\n${spot.y.toStringAsFixed(1)}°C',
                    TextStyle(color: s.color, fontSize: 11),
                  );
                }).toList();
              },
            ),
            handleBuiltInTouches: true,
          ),
          lineBarsData: visibleSeries.map((s) {
            return LineChartBarData(
              spots: s.spots,
              color: s.color,
              barWidth: 2,
              dotData: FlDotData(show: s.spots.length <= 20),
              belowBarData: BarAreaData(show: false),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildLegend() {
    return Wrap(
      spacing: 8,
      runSpacing: 4,
      children: _series.map((s) {
        final on = _visible.contains(s.displayName);
        return FilterChip(
          avatar: CircleAvatar(
            backgroundColor: on ? s.color : Colors.grey.shade400,
            radius: 6,
          ),
          label: Text(s.displayName, style: const TextStyle(fontSize: 12)),
          selected: on,
          showCheckmark: false,
          onSelected: (val) {
            setState(() {
              if (val) {
                _visible.add(s.displayName);
              } else {
                _visible.remove(s.displayName);
              }
            });
          },
        );
      }).toList(),
    );
  }
}

// ---------------------------------------------------------------------------
// Small value type for the span selector
// ---------------------------------------------------------------------------

class _SpanOption {
  final String label;
  final int hours;

  const _SpanOption({required this.label, required this.hours});
}
