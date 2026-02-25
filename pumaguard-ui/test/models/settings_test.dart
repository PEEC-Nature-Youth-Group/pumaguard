// Unit tests for Settings model
// Tests JSON serialization, deserialization, copyWith, and nested objects

import 'package:flutter_test/flutter_test.dart';
import 'package:pumaguard_ui/models/settings.dart';
import 'package:pumaguard_ui/models/camera.dart';
import 'package:pumaguard_ui/models/plug.dart';

void main() {
  group('Settings Model Tests', () {
    group('Constructor', () {
      test('creates Settings with all fields', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'bb:cc:dd:ee:ff:00',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        final settings = Settings(
          yoloMinSize: 0.02,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: 'yolov8s_101425.pt',
          classifierModelFilename: 'colorbw_111325.h5',
          pumaThreshold: 0.5,
          deterrentSoundFiles: ['alarm.wav'],
          fileStabilizationExtraWait: 2.0,
          playSound: true,
          volume: 80,
          cameras: [camera],
          plugs: [plug],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        expect(settings.yoloMinSize, 0.02);
        expect(settings.yoloConfThresh, 0.25);
        expect(settings.yoloMaxDets, 10);
        expect(settings.yoloModelFilename, 'yolov8s_101425.pt');
        expect(settings.classifierModelFilename, 'colorbw_111325.h5');
        expect(settings.deterrentSoundFiles, ['alarm.wav']);
        expect(settings.fileStabilizationExtraWait, 2.0);
        expect(settings.playSound, true);
        expect(settings.volume, 80);
        expect(settings.cameras.length, 1);
        expect(settings.plugs.length, 1);
      });

      test('creates Settings with empty lists', () {
        final settings = Settings(
          yoloMinSize: 0.01,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: '',
          classifierModelFilename: '',
          pumaThreshold: 0.5,
          deterrentSoundFiles: [''],
          fileStabilizationExtraWait: 2.0,
          playSound: false,
          volume: 80,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        expect(settings.cameras.isEmpty, true);
        expect(settings.plugs.isEmpty, true);
      });

      test('creates Settings with multiple cameras and plugs', () {
        final cameras = [
          Camera(
            hostname: 'Camera1',
            ipAddress: '192.168.52.100',
            macAddress: 'aa:bb:cc:dd:ee:01',
            lastSeen: '2024-01-15T10:30:00Z',
            status: 'connected',
          ),
          Camera(
            hostname: 'Camera2',
            ipAddress: '192.168.52.101',
            macAddress: 'aa:bb:cc:dd:ee:02',
            lastSeen: '2024-01-15T10:30:00Z',
            status: 'connected',
          ),
        ];

        final plugs = [
          Plug(
            hostname: 'Plug1',
            ipAddress: '192.168.52.200',
            macAddress: 'bb:cc:dd:ee:ff:01',
            lastSeen: '2024-01-15T10:30:00Z',
            status: 'connected',
            mode: 'off',
          ),
          Plug(
            hostname: 'Plug2',
            ipAddress: '192.168.52.201',
            macAddress: 'bb:cc:dd:ee:ff:02',
            lastSeen: '2024-01-15T10:30:00Z',
            status: 'connected',
            mode: 'automatic',
          ),
        ];

        final settings = Settings(
          yoloMinSize: 0.02,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: 'yolov8s.pt',
          classifierModelFilename: 'classifier.h5',
          pumaThreshold: 0.5,
          deterrentSoundFiles: ['sound.wav'],
          fileStabilizationExtraWait: 2.0,
          playSound: true,
          volume: 80,
          cameras: cameras,
          plugs: plugs,
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        expect(settings.cameras.length, 2);
        expect(settings.plugs.length, 2);
        expect(settings.cameras[0].hostname, 'Camera1');
        expect(settings.plugs[0].hostname, 'Plug1');
      });
    });

    group('fromJson', () {
      test('parses complete JSON correctly', () {
        final json = {
          'YOLO-min-size': 0.02,
          'YOLO-conf-thresh': 0.25,
          'YOLO-max-dets': 10,
          'YOLO-model-filename': 'yolov8s_101425.pt',
          'classifier-model-filename': 'colorbw_111325.h5',
          'deterrent-sound-files': ['alarm.wav'],
          'file-stabilization-extra-wait': 2.0,
          'play-sound': true,
          'volume': 80,
          'cameras': [
            {
              'hostname': 'TestCamera',
              'ip_address': '192.168.52.100',
              'mac_address': 'aa:bb:cc:dd:ee:ff',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'connected',
            },
          ],
          'plugs': [
            {
              'hostname': 'TestPlug',
              'ip_address': '192.168.52.200',
              'mac_address': 'bb:cc:dd:ee:ff:00',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'connected',
            },
          ],
        };

        final settings = Settings.fromJson(json);

        expect(settings.yoloMinSize, 0.02);
        expect(settings.yoloConfThresh, 0.25);
        expect(settings.yoloMaxDets, 10);
        expect(settings.yoloModelFilename, 'yolov8s_101425.pt');
        expect(settings.classifierModelFilename, 'colorbw_111325.h5');
        expect(settings.deterrentSoundFiles, ['alarm.wav']);
        expect(settings.fileStabilizationExtraWait, 2.0);
        expect(settings.playSound, true);
        expect(settings.volume, 80);
        expect(settings.cameras.length, 1);
        expect(settings.cameras[0].hostname, 'TestCamera');
        expect(settings.plugs.length, 1);
        expect(settings.plugs[0].hostname, 'TestPlug');
        expect(settings.deviceAutoRemoveEnabled, false);
        expect(settings.deviceAutoRemoveHours, 24);
      });

      test('handles device-auto-remove-enabled from JSON', () {
        final json = {
          'device-auto-remove-enabled': true,
          'device-auto-remove-hours': 48,
        };

        final settings = Settings.fromJson(json);

        expect(settings.deviceAutoRemoveEnabled, true);
        expect(settings.deviceAutoRemoveHours, 48);
      });

      test('handles null device auto-remove values with defaults', () {
        final json = {
          'device-auto-remove-enabled': null,
          'device-auto-remove-hours': null,
        };

        final settings = Settings.fromJson(json);

        expect(settings.deviceAutoRemoveEnabled, false);
        expect(settings.deviceAutoRemoveHours, 24);
      });

      test('handles backward compatibility with camera-auto-remove names', () {
        final json = {
          'camera-auto-remove-enabled': true,
          'camera-auto-remove-hours': 36,
        };

        final settings = Settings.fromJson(json);

        expect(settings.deviceAutoRemoveEnabled, true);
        expect(settings.deviceAutoRemoveHours, 36);
      });

      test('handles null values with defaults', () {
        final json = {
          'YOLO-min-size': null,
          'YOLO-conf-thresh': null,
          'YOLO-max-dets': null,
          'YOLO-model-filename': null,
          'classifier-model-filename': null,
          'deterrent-sound-file': null,
          'file-stabilization-extra-wait': null,
          'play-sound': null,
          'volume': null,
          'cameras': null,
          'plugs': null,
        };

        final settings = Settings.fromJson(json);

        expect(settings.yoloMinSize, 0.01);
        expect(settings.yoloConfThresh, 0.25);
        expect(settings.yoloMaxDets, 10);
        expect(settings.yoloModelFilename, '');
        expect(settings.classifierModelFilename, '');
        expect(settings.deterrentSoundFiles, ['']);
        expect(settings.fileStabilizationExtraWait, 2.0);
        expect(settings.playSound, false);
        expect(settings.volume, 80);
        expect(settings.cameras.isEmpty, true);
        expect(settings.plugs.isEmpty, true);
      });

      test('handles missing fields with defaults', () {
        final json = <String, dynamic>{};

        final settings = Settings.fromJson(json);

        expect(settings.yoloMinSize, 0.01);
        expect(settings.yoloConfThresh, 0.25);
        expect(settings.yoloMaxDets, 10);
        expect(settings.yoloModelFilename, '');
        expect(settings.classifierModelFilename, '');
        expect(settings.deterrentSoundFiles, ['']);
        expect(settings.fileStabilizationExtraWait, 2.0);
        expect(settings.playSound, false);
        expect(settings.volume, 80);
        expect(settings.cameras.isEmpty, true);
        expect(settings.plugs.isEmpty, true);
      });

      test('handles partial JSON with some fields missing', () {
        final json = {
          'YOLO-min-size': 0.03,
          'YOLO-conf-thresh': 0.5,
          'play-sound': true,
        };

        final settings = Settings.fromJson(json);

        expect(settings.yoloMinSize, 0.03);
        expect(settings.yoloConfThresh, 0.5);
        expect(settings.playSound, true);
        expect(settings.yoloMaxDets, 10); // default
        expect(settings.volume, 80); // default
      });

      test('handles integer values for double fields', () {
        final json = {
          'YOLO-min-size': 1,
          'YOLO-conf-thresh': 0,
          'file-stabilization-extra-wait': 3,
        };

        final settings = Settings.fromJson(json);

        expect(settings.yoloMinSize, 1.0);
        expect(settings.yoloConfThresh, 0.0);
        expect(settings.fileStabilizationExtraWait, 3.0);
      });

      test('handles empty cameras list', () {
        final json = {'cameras': [], 'plugs': []};

        final settings = Settings.fromJson(json);

        expect(settings.cameras.isEmpty, true);
        expect(settings.plugs.isEmpty, true);
      });

      test('handles multiple cameras and plugs in JSON', () {
        final json = {
          'cameras': [
            {
              'hostname': 'Camera1',
              'ip_address': '192.168.52.100',
              'mac_address': 'aa:bb:cc:dd:ee:01',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'connected',
            },
            {
              'hostname': 'Camera2',
              'ip_address': '192.168.52.101',
              'mac_address': 'aa:bb:cc:dd:ee:02',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'disconnected',
            },
          ],
          'plugs': [
            {
              'hostname': 'Plug1',
              'ip_address': '192.168.52.200',
              'mac_address': 'bb:cc:dd:ee:ff:01',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'connected',
            },
          ],
        };

        final settings = Settings.fromJson(json);

        expect(settings.cameras.length, 2);
        expect(settings.cameras[0].hostname, 'Camera1');
        expect(settings.cameras[1].hostname, 'Camera2');
        expect(settings.cameras[1].status, 'disconnected');
        expect(settings.plugs.length, 1);
        expect(settings.plugs[0].hostname, 'Plug1');
      });

      test('handles non-list value for cameras', () {
        final json = {'cameras': 'not a list', 'plugs': 'also not a list'};

        final settings = Settings.fromJson(json);

        expect(settings.cameras.isEmpty, true);
        expect(settings.plugs.isEmpty, true);
      });

      test('handles backwards compatibility with single sound file', () {
        final json = {'deterrent-sound-file': 'old_format_sound.wav'};

        final settings = Settings.fromJson(json);

        expect(settings.deterrentSoundFiles, ['old_format_sound.wav']);
      });

      test('handles new format with multiple sound files', () {
        final json = {
          'deterrent-sound-files': ['sound1.mp3', 'sound2.mp3', 'sound3.mp3'],
        };

        final settings = Settings.fromJson(json);

        expect(settings.deterrentSoundFiles.length, 3);
        expect(settings.deterrentSoundFiles[0], 'sound1.mp3');
        expect(settings.deterrentSoundFiles[1], 'sound2.mp3');
        expect(settings.deterrentSoundFiles[2], 'sound3.mp3');
      });

      test('prefers new format over old when both present', () {
        final json = {
          'deterrent-sound-file': 'old_sound.wav',
          'deterrent-sound-files': ['new_sound.mp3'],
        };

        final settings = Settings.fromJson(json);

        expect(settings.deterrentSoundFiles, ['new_sound.mp3']);
      });

      test('ensures at least one sound file when empty', () {
        final json = {'deterrent-sound-files': []};

        final settings = Settings.fromJson(json);

        expect(settings.deterrentSoundFiles, ['']);
      });

      test('handles puma-threshold from JSON', () {
        final json = {'puma-threshold': 0.75};

        final settings = Settings.fromJson(json);

        expect(settings.pumaThreshold, 0.75);
      });

      test('uses default puma-threshold when missing', () {
        final json = <String, dynamic>{};

        final settings = Settings.fromJson(json);

        expect(settings.pumaThreshold, 0.5);
      });

      test('handles null puma-threshold with default', () {
        final json = {'puma-threshold': null};

        final settings = Settings.fromJson(json);

        expect(settings.pumaThreshold, 0.5);
      });

      test('handles integer puma-threshold value', () {
        final json = {'puma-threshold': 1};

        final settings = Settings.fromJson(json);

        expect(settings.pumaThreshold, 1.0);
      });
    });

    group('toJson', () {
      test('converts Settings to JSON correctly', () {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'bb:cc:dd:ee:ff:00',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        final settings = Settings(
          yoloMinSize: 0.02,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: 'yolov8s_101425.pt',
          classifierModelFilename: 'colorbw_111325.h5',
          pumaThreshold: 0.5,
          deterrentSoundFiles: ['alarm.wav'],
          fileStabilizationExtraWait: 2.0,
          playSound: true,
          volume: 80,
          cameras: [camera],
          plugs: [plug],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        final json = settings.toJson();

        expect(json['YOLO-min-size'], 0.02);
        expect(json['YOLO-conf-thresh'], 0.25);
        expect(json['YOLO-max-dets'], 10);
        expect(json['YOLO-model-filename'], 'yolov8s_101425.pt');
        expect(json['classifier-model-filename'], 'colorbw_111325.h5');
        expect(json['deterrent-sound-files'], ['alarm.wav']);
        expect(json['file-stabilization-extra-wait'], 2.0);
        expect(json['play-sound'], true);
        expect(json['volume'], 80);
        expect(json['cameras'], isA<List>());
        expect(json['cameras'].length, 1);
        expect(json['plugs'], isA<List>());
        expect(json['plugs'].length, 1);
        expect(json['device-auto-remove-enabled'], false);
        expect(json['device-auto-remove-hours'], 24);
      });

      test('converts empty lists correctly', () {
        final settings = Settings(
          yoloMinSize: 0.01,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: '',
          classifierModelFilename: '',
          pumaThreshold: 0.5,
          deterrentSoundFiles: [''],
          fileStabilizationExtraWait: 2.0,
          playSound: false,
          volume: 80,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        final json = settings.toJson();

        expect(json['cameras'], isA<List>());
        expect(json['cameras'].isEmpty, true);
        expect(json['plugs'], isA<List>());
        expect(json['plugs'].isEmpty, true);
      });

      test('preserves empty strings in JSON', () {
        final settings = Settings(
          yoloMinSize: 0.01,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: '',
          classifierModelFilename: '',
          pumaThreshold: 0.5,
          deterrentSoundFiles: [''],
          fileStabilizationExtraWait: 2.0,
          playSound: false,
          volume: 80,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        final json = settings.toJson();

        expect(json['YOLO-model-filename'], '');
        expect(json['classifier-model-filename'], '');
        expect(json['deterrent-sound-files'], ['']);
      });

      test('includes device auto-remove fields in JSON', () {
        final settings = Settings(
          yoloMinSize: 0.01,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: '',
          classifierModelFilename: '',
          pumaThreshold: 0.5,
          deterrentSoundFiles: [''],
          fileStabilizationExtraWait: 2.0,
          playSound: false,
          volume: 80,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: true,
          deviceAutoRemoveHours: 48,
        );

        final json = settings.toJson();

        expect(json['device-auto-remove-enabled'], true);
        expect(json['device-auto-remove-hours'], 48);
      });

      test('includes puma-threshold in JSON', () {
        final settings = Settings(
          yoloMinSize: 0.01,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: '',
          classifierModelFilename: '',
          pumaThreshold: 0.65,
          deterrentSoundFiles: [''],
          fileStabilizationExtraWait: 2.0,
          playSound: false,
          volume: 80,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        final json = settings.toJson();

        expect(json['puma-threshold'], 0.65);
      });
    });

    group('JSON Round Trip', () {
      test('fromJson and toJson are inverses', () {
        final originalJson = {
          'YOLO-min-size': 0.02,
          'YOLO-conf-thresh': 0.25,
          'YOLO-max-dets': 10,
          'YOLO-model-filename': 'yolov8s_101425.pt',
          'classifier-model-filename': 'colorbw_111325.h5',
          'puma-threshold': 0.5,
          'deterrent-sound-files': ['alarm.wav'],
          'file-stabilization-extra-wait': 2.0,
          'play-sound': true,
          'volume': 80,
          'cameras': [
            {
              'hostname': 'TestCamera',
              'ip_address': '192.168.52.100',
              'mac_address': 'aa:bb:cc:dd:ee:ff',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'connected',
            },
          ],
          'plugs': [
            {
              'hostname': 'TestPlug',
              'ip_address': '192.168.52.200',
              'mac_address': 'bb:cc:dd:ee:ff:00',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'connected',
            },
          ],
        };

        final settings = Settings.fromJson(originalJson);
        final resultJson = settings.toJson();

        expect(resultJson['YOLO-min-size'], originalJson['YOLO-min-size']);
        expect(
          resultJson['YOLO-conf-thresh'],
          originalJson['YOLO-conf-thresh'],
        );
        expect(resultJson['YOLO-max-dets'], originalJson['YOLO-max-dets']);
        expect(
          resultJson['deterrent-sound-files'],
          originalJson['deterrent-sound-files'],
        );
        expect(
          resultJson['YOLO-conf-thresh'],
          originalJson['YOLO-conf-thresh'],
        );
        expect(resultJson['YOLO-max-dets'], originalJson['YOLO-max-dets']);
        expect(
          resultJson['YOLO-model-filename'],
          originalJson['YOLO-model-filename'],
        );
        expect(
          resultJson['classifier-model-filename'],
          originalJson['classifier-model-filename'],
        );
        expect(
          resultJson['deterrent-sound-file'],
          originalJson['deterrent-sound-file'],
        );
        expect(
          resultJson['file-stabilization-extra-wait'],
          originalJson['file-stabilization-extra-wait'],
        );
        expect(resultJson['play-sound'], originalJson['play-sound']);
        expect(resultJson['volume'], originalJson['volume']);
        expect(resultJson['cameras'].length, 1);
        expect(resultJson['plugs'].length, 1);
      });
    });

    group('copyWith', () {
      late Settings originalSettings;

      setUp(() {
        final camera = Camera(
          hostname: 'TestCamera',
          ipAddress: '192.168.52.100',
          macAddress: 'aa:bb:cc:dd:ee:ff',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
        );

        final plug = Plug(
          hostname: 'TestPlug',
          ipAddress: '192.168.52.200',
          macAddress: 'bb:cc:dd:ee:ff:00',
          lastSeen: '2024-01-15T10:30:00Z',
          status: 'connected',
          mode: 'off',
        );

        originalSettings = Settings(
          yoloMinSize: 0.02,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: 'yolov8s_101425.pt',
          classifierModelFilename: 'colorbw_111325.h5',
          pumaThreshold: 0.5,
          deterrentSoundFiles: ['alarm.wav'],
          fileStabilizationExtraWait: 2.0,
          playSound: true,
          volume: 80,
          cameras: [camera],
          plugs: [plug],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );
      });

      test('returns identical object when no parameters provided', () {
        final newSettings = originalSettings.copyWith();

        expect(newSettings.yoloMinSize, originalSettings.yoloMinSize);
        expect(newSettings.yoloConfThresh, originalSettings.yoloConfThresh);
        expect(newSettings.yoloMaxDets, originalSettings.yoloMaxDets);
        expect(
          newSettings.yoloModelFilename,
          originalSettings.yoloModelFilename,
        );
        expect(
          newSettings.classifierModelFilename,
          originalSettings.classifierModelFilename,
        );
        expect(
          newSettings.deterrentSoundFiles,
          originalSettings.deterrentSoundFiles,
        );
        expect(
          newSettings.fileStabilizationExtraWait,
          originalSettings.fileStabilizationExtraWait,
        );
        expect(newSettings.playSound, originalSettings.playSound);
        expect(newSettings.volume, originalSettings.volume);
        expect(newSettings.cameras.length, originalSettings.cameras.length);
        expect(newSettings.plugs.length, originalSettings.plugs.length);
        expect(
          newSettings.deviceAutoRemoveEnabled,
          originalSettings.deviceAutoRemoveEnabled,
        );
        expect(
          newSettings.deviceAutoRemoveHours,
          originalSettings.deviceAutoRemoveHours,
        );
      });

      test('updates yoloMinSize', () {
        final newSettings = originalSettings.copyWith(yoloMinSize: 0.05);

        expect(newSettings.yoloMinSize, 0.05);
        expect(newSettings.yoloConfThresh, originalSettings.yoloConfThresh);
      });

      test('updates yoloConfThresh', () {
        final newSettings = originalSettings.copyWith(yoloConfThresh: 0.5);

        expect(newSettings.yoloConfThresh, 0.5);
        expect(newSettings.yoloMinSize, originalSettings.yoloMinSize);
      });

      test('updates yoloMaxDets', () {
        final newSettings = originalSettings.copyWith(yoloMaxDets: 20);

        expect(newSettings.yoloMaxDets, 20);
        expect(newSettings.yoloMinSize, originalSettings.yoloMinSize);
      });

      test('updates yoloModelFilename', () {
        final newSettings = originalSettings.copyWith(
          yoloModelFilename: 'new_model.pt',
        );

        expect(newSettings.yoloModelFilename, 'new_model.pt');
        expect(
          newSettings.classifierModelFilename,
          originalSettings.classifierModelFilename,
        );
      });

      test('updates classifierModelFilename', () {
        final newSettings = originalSettings.copyWith(
          classifierModelFilename: 'new_classifier.h5',
        );

        expect(newSettings.classifierModelFilename, 'new_classifier.h5');
        expect(
          newSettings.yoloModelFilename,
          originalSettings.yoloModelFilename,
        );
      });

      test('updates deterrentSoundFiles', () {
        final newSettings = originalSettings.copyWith(
          deterrentSoundFiles: ['new_sound.wav'],
        );

        expect(newSettings.deterrentSoundFiles, ['new_sound.wav']);
        expect(
          newSettings.yoloModelFilename,
          originalSettings.yoloModelFilename,
        );
      });

      test('updates fileStabilizationExtraWait', () {
        final newSettings = originalSettings.copyWith(
          fileStabilizationExtraWait: 5.0,
        );

        expect(newSettings.fileStabilizationExtraWait, 5.0);
        expect(newSettings.yoloMinSize, originalSettings.yoloMinSize);
      });

      test('updates playSound', () {
        final newSettings = originalSettings.copyWith(playSound: false);

        expect(newSettings.playSound, false);
        expect(newSettings.volume, originalSettings.volume);
      });

      test('updates volume', () {
        final newSettings = originalSettings.copyWith(volume: 100);

        expect(newSettings.volume, 100);
        expect(newSettings.playSound, originalSettings.playSound);
      });

      test('updates cameras list', () {
        final newCamera = Camera(
          hostname: 'NewCamera',
          ipAddress: '192.168.52.102',
          macAddress: 'cc:dd:ee:ff:00:11',
          lastSeen: '2024-01-15T11:00:00Z',
          status: 'connected',
        );

        final newSettings = originalSettings.copyWith(cameras: [newCamera]);

        expect(newSettings.cameras.length, 1);
        expect(newSettings.cameras[0].hostname, 'NewCamera');
        expect(newSettings.plugs.length, originalSettings.plugs.length);
      });

      test('updates plugs list', () {
        final newPlug = Plug(
          hostname: 'NewPlug',
          ipAddress: '192.168.52.202',
          macAddress: 'dd:ee:ff:00:11:22',
          lastSeen: '2024-01-15T11:00:00Z',
          status: 'connected',
          mode: 'on',
        );

        final newSettings = originalSettings.copyWith(plugs: [newPlug]);

        expect(newSettings.plugs.length, 1);
        expect(newSettings.plugs[0].hostname, 'NewPlug');
        expect(newSettings.cameras.length, originalSettings.cameras.length);
      });

      test('updates multiple fields at once', () {
        final newSettings = originalSettings.copyWith(
          yoloMinSize: 0.05,
          volume: 90,
          playSound: false,
        );

        expect(newSettings.yoloMinSize, 0.05);
        expect(newSettings.volume, 90);
        expect(newSettings.playSound, false);
        expect(newSettings.yoloConfThresh, originalSettings.yoloConfThresh);
      });

      test('can set cameras to empty list', () {
        final newSettings = originalSettings.copyWith(cameras: []);

        expect(newSettings.cameras.isEmpty, true);
        expect(originalSettings.cameras.length, 1);
      });

      test('can set plugs to empty list', () {
        final newSettings = originalSettings.copyWith(plugs: []);

        expect(newSettings.plugs.isEmpty, true);
        expect(originalSettings.plugs.length, 1);
      });

      test('updates deviceAutoRemoveEnabled', () {
        final newSettings = originalSettings.copyWith(
          deviceAutoRemoveEnabled: true,
        );

        expect(newSettings.deviceAutoRemoveEnabled, true);
        expect(
          newSettings.deviceAutoRemoveHours,
          originalSettings.deviceAutoRemoveHours,
        );
      });

      test('updates deviceAutoRemoveHours', () {
        final newSettings = originalSettings.copyWith(
          deviceAutoRemoveHours: 48,
        );

        expect(newSettings.deviceAutoRemoveHours, 48);
        expect(
          newSettings.deviceAutoRemoveEnabled,
          originalSettings.deviceAutoRemoveEnabled,
        );
      });

      test('updates pumaThreshold', () {
        final newSettings = originalSettings.copyWith(pumaThreshold: 0.75);

        expect(newSettings.pumaThreshold, 0.75);
        expect(newSettings.yoloMinSize, originalSettings.yoloMinSize);
      });

      test('does not modify original object', () {
        final newSettings = originalSettings.copyWith(
          yoloMinSize: 0.99,
          volume: 10,
          playSound: false,
        );

        expect(originalSettings.yoloMinSize, 0.02);
        expect(originalSettings.volume, 80);
        expect(originalSettings.playSound, true);
        expect(newSettings.yoloMinSize, 0.99);
      });
    });

    group('Edge Cases and Special Values', () {
      test('handles zero values', () {
        final settings = Settings(
          yoloMinSize: 0.0,
          yoloConfThresh: 0.0,
          yoloMaxDets: 0,
          yoloModelFilename: '',
          classifierModelFilename: '',
          pumaThreshold: 0.5,
          deterrentSoundFiles: [''],
          fileStabilizationExtraWait: 0.0,
          playSound: false,
          volume: 0,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        expect(settings.yoloMinSize, 0.0);
        expect(settings.yoloConfThresh, 0.0);
        expect(settings.yoloMaxDets, 0);
        expect(settings.fileStabilizationExtraWait, 0.0);
        expect(settings.volume, 0);
      });

      test('handles maximum values', () {
        final settings = Settings(
          yoloMinSize: 1.0,
          yoloConfThresh: 1.0,
          yoloMaxDets: 1000,
          yoloModelFilename: 'model',
          classifierModelFilename: 'classifier',
          pumaThreshold: 0.5,
          deterrentSoundFiles: ['sound'],
          fileStabilizationExtraWait: 999.99,
          playSound: true,
          volume: 100,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        expect(settings.yoloMinSize, 1.0);
        expect(settings.yoloConfThresh, 1.0);
        expect(settings.yoloMaxDets, 1000);
        expect(settings.fileStabilizationExtraWait, 999.99);
        expect(settings.volume, 100);
      });

      test('handles negative values', () {
        final settings = Settings(
          yoloMinSize: -0.5,
          yoloConfThresh: -0.25,
          yoloMaxDets: -10,
          yoloModelFilename: '',
          classifierModelFilename: '',
          pumaThreshold: 0.5,
          deterrentSoundFiles: [''],
          fileStabilizationExtraWait: -1.0,
          playSound: false,
          volume: -10,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        expect(settings.yoloMinSize, -0.5);
        expect(settings.yoloConfThresh, -0.25);
        expect(settings.yoloMaxDets, -10);
        expect(settings.fileStabilizationExtraWait, -1.0);
        expect(settings.volume, -10);
      });

      test('handles very long filenames', () {
        final longFilename = 'a' * 1000;
        final settings = Settings(
          yoloMinSize: 0.01,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: longFilename,
          classifierModelFilename: longFilename,
          pumaThreshold: 0.5,
          deterrentSoundFiles: [longFilename],
          fileStabilizationExtraWait: 2.0,
          playSound: false,
          volume: 80,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        expect(settings.yoloModelFilename.length, 1000);
        expect(settings.classifierModelFilename.length, 1000);
        expect(settings.deterrentSoundFiles[0].length, 1000);
      });

      test('handles filenames with special characters', () {
        final settings = Settings(
          yoloMinSize: 0.01,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: 'model@#\$%^&*.pt',
          classifierModelFilename: 'classifier!@#.h5',
          pumaThreshold: 0.5,
          deterrentSoundFiles: ['sound-file_123.wav'],
          fileStabilizationExtraWait: 2.0,
          playSound: false,
          volume: 80,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        expect(settings.yoloModelFilename, 'model@#\$%^&*.pt');
        expect(settings.classifierModelFilename, 'classifier!@#.h5');
        expect(settings.deterrentSoundFiles, ['sound-file_123.wav']);
      });

      test('handles very precise floating point values', () {
        final settings = Settings(
          yoloMinSize: 0.0123456789,
          yoloConfThresh: 0.9876543210,
          yoloMaxDets: 10,
          yoloModelFilename: '',
          classifierModelFilename: '',
          pumaThreshold: 0.5,
          deterrentSoundFiles: [''],
          fileStabilizationExtraWait: 1.23456789,
          playSound: false,
          volume: 80,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        expect(settings.yoloMinSize, closeTo(0.0123456789, 0.0000000001));
        expect(settings.yoloConfThresh, closeTo(0.9876543210, 0.0000000001));
        expect(
          settings.fileStabilizationExtraWait,
          closeTo(1.23456789, 0.0000000001),
        );
      });
    });

    group('Real-World Scenarios', () {
      test('creates settings from typical API response', () {
        final json = {
          'YOLO-min-size': 0.02,
          'YOLO-conf-thresh': 0.25,
          'YOLO-max-dets': 10,
          'YOLO-model-filename': 'yolov8s_101425.pt',
          'classifier-model-filename': 'colorbw_111325.h5',
          'deterrent-sound-file': '/path/to/sound.wav',
          'file-stabilization-extra-wait': 2.0,
          'play-sound': true,
          'volume': 80,
          'cameras': [
            {
              'hostname': 'Microseven',
              'ip_address': '192.168.52.101',
              'mac_address': 'aa:bb:cc:dd:ee:01',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'connected',
            },
          ],
          'plugs': [
            {
              'hostname': 'KasaPlug',
              'ip_address': '192.168.52.201',
              'mac_address': 'bb:cc:dd:ee:ff:01',
              'last_seen': '2024-01-15T10:30:00Z',
              'status': 'connected',
            },
          ],
        };

        final settings = Settings.fromJson(json);

        expect(settings.yoloMinSize, 0.02);
        expect(settings.cameras[0].hostname, 'Microseven');
        expect(settings.cameras[0].isConnected, true);
        expect(settings.plugs[0].hostname, 'KasaPlug');
        expect(settings.plugs[0].isConnected, true);
      });

      test('updates settings for user configuration change', () {
        final original = Settings(
          yoloMinSize: 0.02,
          yoloConfThresh: 0.25,
          yoloMaxDets: 10,
          yoloModelFilename: 'yolov8s_101425.pt',
          classifierModelFilename: 'colorbw_111325.h5',
          pumaThreshold: 0.5,
          deterrentSoundFiles: ['alarm.wav'],
          fileStabilizationExtraWait: 2.0,
          playSound: false,
          volume: 80,
          cameras: [],
          plugs: [],
          deviceAutoRemoveEnabled: false,
          deviceAutoRemoveHours: 24,
        );

        // User enables sound and adjusts volume
        final updated = original.copyWith(playSound: true, volume: 90);

        expect(updated.playSound, true);
        expect(updated.volume, 90);
        expect(updated.yoloMinSize, original.yoloMinSize);
      });

      test('handles settings with no devices', () {
        final json = {
          'YOLO-min-size': 0.02,
          'YOLO-conf-thresh': 0.25,
          'YOLO-max-dets': 10,
          'cameras': [],
          'plugs': [],
        };

        final settings = Settings.fromJson(json);

        expect(settings.cameras.isEmpty, true);
        expect(settings.plugs.isEmpty, true);
      });
    });
  });
}
