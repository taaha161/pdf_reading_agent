import 'dart:convert';
import 'dart:html' as html;

void downloadCsv(String csvContent) {
  final bytes = utf8.encode(csvContent);
  final base64 = base64Encode(bytes);
  final dataUrl = 'data:text/csv;base64,$base64';
  final anchor = html.AnchorElement()
    ..href = dataUrl
    ..download = 'statement.csv';
  anchor.click();
}
