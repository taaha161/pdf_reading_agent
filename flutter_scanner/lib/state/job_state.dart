import 'package:flutter/foundation.dart';

import '../api/client.dart';

class JobState extends ChangeNotifier {
  JobState({required ApiClient apiClient}) : _apiClient = apiClient;

  ApiClient get apiClient => _apiClient;
  final ApiClient _apiClient;

  String? _jobId;
  List<Transaction> _transactions = [];
  List<CategorySummary> _summaryByCategory = [];
  String? _currency;
  bool _loading = false;
  String? _error;

  String? get jobId => _jobId;
  List<Transaction> get transactions => List.unmodifiable(_transactions);
  List<CategorySummary> get summaryByCategory =>
      List.unmodifiable(_summaryByCategory);
  String? get currency => _currency;
  bool get loading => _loading;
  String? get error => _error;
  bool get hasJob => _jobId != null && _jobId!.isNotEmpty;

  void setJobId(String? jobId) {
    if (_jobId == jobId) return;
    _jobId = jobId;
    _transactions = [];
    _summaryByCategory = [];
    _currency = null;
    _error = null;
    notifyListeners();
    if (jobId != null && jobId.isNotEmpty) {
      loadJob();
    }
  }

  Future<void> loadJob() async {
    final id = _jobId;
    if (id == null || id.isEmpty) return;
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final detail = await _apiClient.getJob(id);
      _transactions = detail.transactions;
      _summaryByCategory = detail.summaryByCategory;
      _currency = detail.currency;
      _error = null;
    } catch (e) {
      _error = e.toString();
      _transactions = [];
      _summaryByCategory = [];
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> updateTransactions(List<Transaction> transactions) async {
    final id = _jobId;
    if (id == null || id.isEmpty) return;
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final detail = await _apiClient.updateJobTransactions(id, transactions);
      _transactions = detail.transactions;
      _summaryByCategory = detail.summaryByCategory;
      _error = null;
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  void setTransactionsFromValidate(
    List<Transaction> transactions,
    List<CategorySummary> summaryByCategory,
  ) {
    _transactions = transactions;
    _summaryByCategory = summaryByCategory;
    _error = null;
    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
