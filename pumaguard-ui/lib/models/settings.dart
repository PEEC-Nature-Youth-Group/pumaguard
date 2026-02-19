import 'camera.dart';
import 'plug.dart';

class Settings {
  final double yoloMinSize;
  final double yoloConfThresh;
  final int yoloMaxDets;
  final String yoloModelFilename;
  final String classifierModelFilename;
  final List<String> deterrentSoundFiles;
  final double fileStabilizationExtraWait;
  final bool playSound;
  final int volume;
  final List<Camera> cameras;
  final List<Plug> plugs;
  final bool cameraAutoRemoveEnabled;
  final int cameraAutoRemoveHours;

  Settings({
    required this.yoloMinSize,
    required this.yoloConfThresh,
    required this.yoloMaxDets,
    required this.yoloModelFilename,
    required this.classifierModelFilename,
    required this.deterrentSoundFiles,
    required this.fileStabilizationExtraWait,
    required this.playSound,
    required this.volume,
    required this.cameras,
    required this.plugs,
    required this.cameraAutoRemoveEnabled,
    required this.cameraAutoRemoveHours,
  });

  factory Settings.fromJson(Map<String, dynamic> json) {
    // Parse cameras list
    List<Camera> camerasList = [];
    if (json['cameras'] is List) {
      camerasList = (json['cameras'] as List)
          .map(
            (cameraJson) => Camera.fromJson(cameraJson as Map<String, dynamic>),
          )
          .toList();
    }

    // Parse plugs list
    List<Plug> plugsList = [];
    if (json['plugs'] is List) {
      plugsList = (json['plugs'] as List)
          .map((plugJson) => Plug.fromJson(plugJson as Map<String, dynamic>))
          .toList();
    }

    // Parse deterrent sound files list (with backwards compatibility)
    List<String> soundFilesList = [];
    if (json['deterrent-sound-files'] is List) {
      soundFilesList = (json['deterrent-sound-files'] as List)
          .map((e) => e.toString())
          .toList();
    } else if (json['deterrent-sound-file'] is String) {
      // Backwards compatibility: convert single file to list
      final singleFile = json['deterrent-sound-file'] as String;
      if (singleFile.isNotEmpty) {
        soundFilesList = [singleFile];
      }
    }
    // Ensure at least one sound file
    if (soundFilesList.isEmpty) {
      soundFilesList = [''];
    }

    return Settings(
      yoloMinSize: (json['YOLO-min-size'] as num?)?.toDouble() ?? 0.01,
      yoloConfThresh: (json['YOLO-conf-thresh'] as num?)?.toDouble() ?? 0.25,
      yoloMaxDets: json['YOLO-max-dets'] as int? ?? 10,
      yoloModelFilename: json['YOLO-model-filename'] as String? ?? '',
      classifierModelFilename:
          json['classifier-model-filename'] as String? ?? '',
      deterrentSoundFiles: soundFilesList,
      fileStabilizationExtraWait:
          (json['file-stabilization-extra-wait'] as num?)?.toDouble() ?? 2.0,
      playSound: json['play-sound'] as bool? ?? false,
      volume: json['volume'] as int? ?? 80,
      cameras: camerasList,
      plugs: plugsList,
      cameraAutoRemoveEnabled:
          json['camera-auto-remove-enabled'] as bool? ?? false,
      cameraAutoRemoveHours: json['camera-auto-remove-hours'] as int? ?? 24,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'YOLO-min-size': yoloMinSize,
      'YOLO-conf-thresh': yoloConfThresh,
      'YOLO-max-dets': yoloMaxDets,
      'YOLO-model-filename': yoloModelFilename,
      'classifier-model-filename': classifierModelFilename,
      'deterrent-sound-files': deterrentSoundFiles,
      'file-stabilization-extra-wait': fileStabilizationExtraWait,
      'play-sound': playSound,
      'volume': volume,
      'cameras': cameras.map((camera) => camera.toJson()).toList(),
      'plugs': plugs.map((plug) => plug.toJson()).toList(),
      'camera-auto-remove-enabled': cameraAutoRemoveEnabled,
      'camera-auto-remove-hours': cameraAutoRemoveHours,
    };
  }

  Settings copyWith({
    double? yoloMinSize,
    double? yoloConfThresh,
    int? yoloMaxDets,
    String? yoloModelFilename,
    String? classifierModelFilename,
    List<String>? deterrentSoundFiles,
    double? fileStabilizationExtraWait,
    bool? playSound,
    int? volume,
    List<Camera>? cameras,
    List<Plug>? plugs,
    bool? cameraAutoRemoveEnabled,
    int? cameraAutoRemoveHours,
  }) {
    return Settings(
      yoloMinSize: yoloMinSize ?? this.yoloMinSize,
      yoloConfThresh: yoloConfThresh ?? this.yoloConfThresh,
      yoloMaxDets: yoloMaxDets ?? this.yoloMaxDets,
      yoloModelFilename: yoloModelFilename ?? this.yoloModelFilename,
      classifierModelFilename:
          classifierModelFilename ?? this.classifierModelFilename,
      deterrentSoundFiles: deterrentSoundFiles ?? this.deterrentSoundFiles,
      fileStabilizationExtraWait:
          fileStabilizationExtraWait ?? this.fileStabilizationExtraWait,
      playSound: playSound ?? this.playSound,
      volume: volume ?? this.volume,
      cameras: cameras ?? this.cameras,
      plugs: plugs ?? this.plugs,
      cameraAutoRemoveEnabled:
          cameraAutoRemoveEnabled ?? this.cameraAutoRemoveEnabled,
      cameraAutoRemoveHours:
          cameraAutoRemoveHours ?? this.cameraAutoRemoveHours,
    );
  }
}
