class Settings {
  final double yoloMinSize;
  final double yoloConfThresh;
  final int yoloMaxDets;
  final String yoloModelFilename;
  final String classifierModelFilename;
  final String deterrentSoundFile;
  final double fileStabilizationExtraWait;
  final bool playSound;

  Settings({
    required this.yoloMinSize,
    required this.yoloConfThresh,
    required this.yoloMaxDets,
    required this.yoloModelFilename,
    required this.classifierModelFilename,
    required this.deterrentSoundFile,
    required this.fileStabilizationExtraWait,
    required this.playSound,
  });

  factory Settings.fromJson(Map<String, dynamic> json) {
    return Settings(
      yoloMinSize: (json['YOLO-min-size'] as num?)?.toDouble() ?? 0.01,
      yoloConfThresh: (json['YOLO-conf-thresh'] as num?)?.toDouble() ?? 0.25,
      yoloMaxDets: json['YOLO-max-dets'] as int? ?? 10,
      yoloModelFilename: json['YOLO-model-filename'] as String? ?? '',
      classifierModelFilename:
          json['classifier-model-filename'] as String? ?? '',
      deterrentSoundFile: json['deterrent-sound-file'] as String? ?? '',
      fileStabilizationExtraWait:
          (json['file-stabilization-extra-wait'] as num?)?.toDouble() ?? 2.0,
      playSound: json['play-sound'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'YOLO-min-size': yoloMinSize,
      'YOLO-conf-thresh': yoloConfThresh,
      'YOLO-max-dets': yoloMaxDets,
      'YOLO-model-filename': yoloModelFilename,
      'classifier-model-filename': classifierModelFilename,
      'deterrent-sound-file': deterrentSoundFile,
      'file-stabilization-extra-wait': fileStabilizationExtraWait,
      'play-sound': playSound,
    };
  }

  Settings copyWith({
    double? yoloMinSize,
    double? yoloConfThresh,
    int? yoloMaxDets,
    String? yoloModelFilename,
    String? classifierModelFilename,
    String? deterrentSoundFile,
    double? fileStabilizationExtraWait,
    bool? playSound,
  }) {
    return Settings(
      yoloMinSize: yoloMinSize ?? this.yoloMinSize,
      yoloConfThresh: yoloConfThresh ?? this.yoloConfThresh,
      yoloMaxDets: yoloMaxDets ?? this.yoloMaxDets,
      yoloModelFilename: yoloModelFilename ?? this.yoloModelFilename,
      classifierModelFilename:
          classifierModelFilename ?? this.classifierModelFilename,
      deterrentSoundFile: deterrentSoundFile ?? this.deterrentSoundFile,
      fileStabilizationExtraWait:
          fileStabilizationExtraWait ?? this.fileStabilizationExtraWait,
      playSound: playSound ?? this.playSound,
    );
  }
}
