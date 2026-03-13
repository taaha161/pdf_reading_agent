import 'package:flutter/foundation.dart';

/// Holds API base URL, optional job ID, and optional auth token.
/// On web: can be set from query params (jobId, apiBase) and postMessage (token, or all).
class EmbedConfig extends ChangeNotifier {
  String _apiBase = '';
  String? _jobId;
  String? _token;

  String get apiBase => _apiBase;
  String? get jobId => _jobId;
  String? get token => _token;
  bool get hasApiBase => _apiBase.isNotEmpty;

  void setFromQueryParams() {
    if (!kIsWeb) return;
    _parseQueryParams();
    notifyListeners();
  }

  void _parseQueryParams() {
    try {
      // Uri.base is set by Flutter web. Only read apiBase from URL.
      // jobId and token come from postMessage so the first API call has the token
      // (otherwise we'd load job before postMessage arrives and get 401).
      final uri = Uri.base;
      final params = uri.queryParameters;
      final base = params['apiBase'];
      if (base != null && base.isNotEmpty) _apiBase = base;
    } catch (_) {}
  }

  void setFromMessage(Map<String, dynamic> data) {
    final base = data['apiBase'] as String?;
    if (base != null && base.isNotEmpty) _apiBase = base;
    final job = data['jobId'] as String?;
    _jobId = job;
    final token = data['token'] as String?;
    _token = token;
    notifyListeners();
  }

  void setJobId(String? jobId) {
    if (_jobId == jobId) return;
    _jobId = jobId;
    notifyListeners();
  }
}
