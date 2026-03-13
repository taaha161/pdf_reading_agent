import 'dart:convert';

import 'package:http/http.dart' as http;

class Transaction {
  final String date;
  final String description;
  final String amount;
  final String type;
  final String category;

  Transaction({
    required this.date,
    required this.description,
    required this.amount,
    required this.type,
    required this.category,
  });

  factory Transaction.fromJson(Map<String, dynamic> json) {
    return Transaction(
      date: json['date'] as String? ?? '',
      description: json['description'] as String? ?? '',
      amount: json['amount'] as String? ?? '',
      type: json['type'] as String? ?? 'debit',
      category: json['category'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'date': date,
        'description': description,
        'amount': amount,
        'type': type,
        'category': category,
      };
}

class CategorySummary {
  final String category;
  final double total;

  CategorySummary({required this.category, required this.total});

  factory CategorySummary.fromJson(Map<String, dynamic> json) {
    return CategorySummary(
      category: json['category'] as String? ?? '',
      total: (json['total'] as num?)?.toDouble() ?? 0,
    );
  }
}

class JobDetail {
  final String jobId;
  final List<Transaction> transactions;
  final List<CategorySummary> summaryByCategory;
  final String? currency;
  final String? dataStatus;
  final String? conversionMode;

  JobDetail({
    required this.jobId,
    required this.transactions,
    required this.summaryByCategory,
    this.currency,
    this.dataStatus,
    this.conversionMode,
  });
}

class ValidateMessageResponse {
  final String type;
  final String content;

  ValidateMessageResponse({required this.type, required this.content});
}

class ValidateTransactionsUpdatedResponse {
  final String type;
  final List<Transaction> transactions;
  final List<CategorySummary> summaryByCategory;
  final String message;

  ValidateTransactionsUpdatedResponse({
    required this.type,
    required this.transactions,
    required this.summaryByCategory,
    required this.message,
  });
}

class ApiClient {
  final String baseUrl;
  final String? authToken;

  ApiClient({required this.baseUrl, this.authToken});

  Map<String, String> get _headers {
    final h = <String, String>{
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (authToken != null && authToken!.isNotEmpty) {
      h['Authorization'] = 'Bearer $authToken';
    }
    return h;
  }

  Future<JobDetail> getJob(String jobId) async {
    final uri = Uri.parse('$baseUrl/api/jobs/$jobId');
    final res = await http.get(uri, headers: _headers);
    if (res.statusCode != 200) {
      throw ApiException(
          res.statusCode, res.body.isNotEmpty ? res.body : 'Job not found');
    }
    final json = jsonDecode(res.body) as Map<String, dynamic>;
    final transactions = (json['transactions'] as List<dynamic>?)
            ?.map((e) => Transaction.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [];
    final summary = (json['summary_by_category'] as List<dynamic>?)
            ?.map((e) =>
                CategorySummary.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [];
    return JobDetail(
      jobId: json['job_id'] as String? ?? jobId,
      transactions: transactions,
      summaryByCategory: summary,
      currency: json['currency'] as String?,
      dataStatus: json['data_status'] as String?,
      conversionMode: json['conversion_mode'] as String?,
    );
  }

  Future<JobDetail> updateJobTransactions(
      String jobId, List<Transaction> transactions) async {
    final uri = Uri.parse('$baseUrl/api/jobs/$jobId');
    final body = jsonEncode({
      'transactions': transactions.map((t) => t.toJson()).toList(),
    });
    final res = await http.patch(uri, headers: _headers, body: body);
    if (res.statusCode != 200) {
      throw ApiException(
          res.statusCode, res.body.isNotEmpty ? res.body : 'Update failed');
    }
    final json = jsonDecode(res.body) as Map<String, dynamic>;
    final txs = (json['transactions'] as List<dynamic>?)
            ?.map((e) => Transaction.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [];
    final summary = (json['summary_by_category'] as List<dynamic>?)
            ?.map((e) =>
                CategorySummary.fromJson(e as Map<String, dynamic>))
            .toList() ??
        [];
    return JobDetail(
      jobId: json['job_id'] as String? ?? jobId,
      transactions: txs,
      summaryByCategory: summary,
      currency: json['currency'] as String?,
      dataStatus: json['data_status'] as String?,
      conversionMode: json['conversion_mode'] as String?,
    );
  }

  Future<dynamic> validate(String jobId, String message) async {
    final uri = Uri.parse('$baseUrl/api/jobs/$jobId/validate');
    final body = jsonEncode({'message': message});
    final res = await http.post(uri, headers: _headers, body: body);
    if (res.statusCode != 200) {
      throw ApiException(
          res.statusCode, res.body.isNotEmpty ? res.body : 'Validate failed');
    }
    final json = jsonDecode(res.body) as Map<String, dynamic>;
    final type = json['type'] as String? ?? 'message';
    if (type == 'transactions_updated') {
      final txs = (json['transactions'] as List<dynamic>?)
              ?.map((e) => Transaction.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];
      final summary = (json['summary_by_category'] as List<dynamic>?)
              ?.map((e) =>
                  CategorySummary.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [];
      return ValidateTransactionsUpdatedResponse(
        type: type,
        transactions: txs,
        summaryByCategory: summary,
        message: json['message'] as String? ?? 'Updated.',
      );
    }
    return ValidateMessageResponse(
      type: type,
      content: json['content'] as String? ?? '',
    );
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String body;

  ApiException(this.statusCode, this.body);

  @override
  String toString() => 'ApiException($statusCode): $body';
}
