import 'package:flutter_test/flutter_test.dart';

import 'package:flutter_scanner/main.dart';

void main() {
  testWidgets('Scanner app smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const ScannerApp());
    await tester.pumpAndSettle();
    expect(find.textContaining('Waiting for configuration'), findsOneWidget);
  });
}
