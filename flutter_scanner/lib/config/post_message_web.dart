import 'dart:convert';
import 'dart:html' as html;

import 'embed_config.dart';

void startPostMessageListener(EmbedConfig config) {
  html.window.onMessage.listen((event) {
    final data = event.data;
    if (data == null) return;
    try {
      Map<String, dynamic>? map;
      if (data is String) {
        map = jsonDecode(data) as Map<String, dynamic>?;
      } else if (data is Map) {
        map = Map<String, dynamic>.from(data);
      }
      if (map != null) config.setFromMessage(map);
    } catch (_) {}
  });
}
