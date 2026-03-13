import 'download_csv_stub.dart' if (dart.library.html) 'download_csv_web.dart' as impl;

void downloadCsv(String csvContent) {
  impl.downloadCsv(csvContent);
}
