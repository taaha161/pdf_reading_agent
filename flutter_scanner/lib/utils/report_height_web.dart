import 'dart:convert';
import 'dart:html' as html;

void reportContentHeight(double height) {
  try {
    final payload = jsonEncode({'type': 'resize', 'height': height.round()});
    html.window.parent?.postMessage(payload, '*');
  } catch (_) {}
}
