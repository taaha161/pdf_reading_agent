import 'report_height_stub.dart'
    if (dart.library.html) 'report_height_web.dart' as impl;

void reportContentHeight(double height) {
  impl.reportContentHeight(height);
}
