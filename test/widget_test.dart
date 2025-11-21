// This is a basic Flutter widget test.
//
// To perform an interaction with a widget in your test, use the WidgetTester
// utility in the flutter_test package. For example, you can send tap and scroll
// gestures. You can also use WidgetTester to find child widgets in the widget
// tree, read text, and verify that the values of widget properties are correct.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:pumaguard_ui/main.dart';

void main() {
  testWidgets('PumaGuard app smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const PumaGuardApp());

    // Verify that the app title is present
    expect(find.text('PumaGuard'), findsOneWidget);

    // Verify that the pets icon is present
    expect(find.byIcon(Icons.pets), findsOneWidget);
  });
}
