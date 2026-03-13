import 'package:flutter/material.dart';

import '../api/client.dart';
import '../state/job_state.dart';
import '../theme/app_theme.dart';
import '../utils/download_csv.dart';
import 'category_chip.dart';

class ResultsTable extends StatelessWidget {
  const ResultsTable({
    super.key,
    required this.jobState,
    this.shrinkWrap = false,
  });

  final JobState jobState;
  final bool shrinkWrap;

  static String _escapeCsv(String s) {
    if (s.contains(',') || s.contains('"') || s.contains('\n')) {
      return '"${s.replaceAll('"', '""')}"';
    }
    return s;
  }

  static String _transactionsToCsv(List<Transaction> transactions) {
    const header = 'date,description,amount,type,category';
    if (transactions.isEmpty) return '$header\n';
    final rows = transactions
        .map((t) => [
              t.date,
              t.description,
              t.amount,
              t.type,
              t.category,
            ].map(_escapeCsv).join(','))
        .join('\n');
    return '$header\n$rows\n';
  }

  static void _triggerDownload(List<Transaction> transactions) {
    final csv = _transactionsToCsv(transactions);
    downloadCsv(csv);
  }

  static String _formatAmount(String type, String amount) {
    final raw = amount.trim();
    if (raw.isEmpty) return '—';
    final isDebit = type.toLowerCase() == 'debit';
    final hasMinus = raw.startsWith('-');
    if (isDebit && !hasMinus) return '-$raw';
    return raw;
  }

  static Color _amountColor(String type, String amount) {
    final t = type.toLowerCase();
    final a = amount.trim();
    if (t == 'credit' || a.startsWith('+')) return AppTheme.success;
    if (t == 'debit' || a.startsWith('-')) return AppTheme.error;
    return AppTheme.text;
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: jobState,
      builder: (context, _) {
        if (jobState.loading && jobState.transactions.isEmpty) {
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: CircularProgressIndicator(),
            ),
          );
        }
        if (jobState.error != null && jobState.transactions.isEmpty) {
          return Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  jobState.error!,
                  style: const TextStyle(color: AppTheme.error),
                ),
                const SizedBox(height: 16),
                FilledButton(
                  onPressed: jobState.loadJob,
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }
        final transactions = jobState.transactions;
        final content = Column(
          mainAxisSize: shrinkWrap ? MainAxisSize.min : MainAxisSize.max,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              margin: const EdgeInsets.fromLTRB(20, 0, 20, 16),
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
              decoration: BoxDecoration(
                color: AppTheme.surface,
                border: Border.all(color: AppTheme.border),
                borderRadius: BorderRadius.circular(14),
                boxShadow: const [
                  BoxShadow(
                    color: Color(0x0D000000),
                    blurRadius: 2,
                    offset: Offset(0, 1),
                  ),
                ],
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Transactions',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: AppTheme.text,
                        ),
                  ),
                  if (transactions.isNotEmpty)
                    FilledButton.icon(
                      onPressed: () => _triggerDownload(transactions),
                      style: FilledButton.styleFrom(
                        backgroundColor: AppTheme.primary,
                        foregroundColor: AppTheme.onPrimary,
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                      ),
                      icon: const Icon(Icons.download, size: 18),
                      label: const Text('Download CSV'),
                    ),
                ],
              ),
            ),
            if (transactions.isEmpty)
              Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  'No transactions.',
                  style: TextStyle(color: AppTheme.textMuted, fontSize: 15),
                ),
              )
            else
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Container(
                  decoration: BoxDecoration(
                    color: AppTheme.bg,
                    border: Border.all(color: AppTheme.border),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Table(
                      columnWidths: const {
                        0: FixedColumnWidth(88),
                        1: FixedColumnWidth(200),
                        2: FixedColumnWidth(140),
                        3: FixedColumnWidth(100),
                        4: FixedColumnWidth(90),
                      },
                      border: TableBorder(
                        horizontalInside: BorderSide(color: AppTheme.border),
                        left: BorderSide(color: AppTheme.border),
                        right: BorderSide(color: AppTheme.border),
                      ),
                      defaultColumnWidth: const IntrinsicColumnWidth(),
                      children: [
                        TableRow(
                          decoration: const BoxDecoration(color: AppTheme.primarySubtle),
                          children: [
                            _headerCell('Date'),
                            _headerCell('Description'),
                            _headerCell('Category'),
                            _headerCell('Amount'),
                            _headerCell('Actions', alignRight: true),
                          ],
                        ),
                        ...List.generate(transactions.length, (i) {
                          final t = transactions[i];
                          final amountStr = _formatAmount(t.type, t.amount);
                          final amountColor = _amountColor(t.type, t.amount);
                          return TableRow(
                            decoration: BoxDecoration(
                              color: i.isEven ? AppTheme.primarySubtle : AppTheme.surface,
                            ),
                            children: [
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                                child: Text(
                                  t.date.isEmpty ? '—' : t.date,
                                  style: const TextStyle(fontSize: 13.6, color: AppTheme.textMuted),
                                ),
                              ),
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                                child: Text(
                                  t.description.isEmpty ? '—' : t.description,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
                                ),
                              ),
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                                child: CategoryChip(category: t.category),
                              ),
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                                child: Text(
                                  amountStr,
                                  style: TextStyle(
                                    fontSize: 14,
                                    color: amountColor,
                                    fontFeatures: const [FontFeature.tabularFigures()],
                                  ),
                                ),
                              ),
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                                child: Align(
                                  alignment: Alignment.centerRight,
                                  child: TextButton(
                                    onPressed: () => _openEdit(context, jobState, i),
                                    style: TextButton.styleFrom(
                                      foregroundColor: AppTheme.primary,
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                      minimumSize: Size.zero,
                                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                                    ),
                                    child: const Text('Edit', style: TextStyle(fontSize: 12.8, fontWeight: FontWeight.w600)),
                                  ),
                                ),
                              ),
                            ],
                          );
                        }),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        );
        if (shrinkWrap) return content;
        return Expanded(child: SingleChildScrollView(child: content));
      },
    );
  }

  Widget _headerCell(String label, {bool alignRight = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Align(
        alignment: alignRight ? Alignment.centerRight : Alignment.centerLeft,
        child: Text(
          label,
          style: const TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: AppTheme.textMuted,
          ),
        ),
      ),
    );
  }

  void _openEdit(BuildContext context, JobState jobState, int index) {
    final transactions = jobState.transactions;
    if (index < 0 || index >= transactions.length) return;
    final t = transactions[index];
    final dateController = TextEditingController(text: t.date);
    final descController = TextEditingController(text: t.description);
    final categoryController = TextEditingController(text: t.category);
    final typeController = TextEditingController(text: t.type);
    final amountController = TextEditingController(text: t.amount);

    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Edit transaction'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: dateController,
                decoration: const InputDecoration(
                  labelText: 'Date',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: descController,
                decoration: const InputDecoration(
                  labelText: 'Description',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: categoryController,
                decoration: const InputDecoration(
                  labelText: 'Category',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: typeController,
                decoration: const InputDecoration(
                  labelText: 'Type (credit/debit)',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: amountController,
                decoration: const InputDecoration(
                  labelText: 'Amount',
                  border: OutlineInputBorder(),
                ),
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () async {
              final type = typeController.text.trim().toLowerCase();
              if (type != 'credit' && type != 'debit') {
                ScaffoldMessenger.of(ctx).showSnackBar(
                  const SnackBar(content: Text('Type must be credit or debit')),
                );
                return;
              }
              final amount = amountController.text.trim();
              if (amount.isEmpty) {
                ScaffoldMessenger.of(ctx).showSnackBar(
                  const SnackBar(content: Text('Amount is required')),
                );
                return;
              }
              final updated = List<Transaction>.from(transactions);
              updated[index] = Transaction(
                date: dateController.text.trim(),
                description: descController.text.trim(),
                category: categoryController.text.trim(),
                type: type,
                amount: amount,
              );
              Navigator.of(ctx).pop();
              await jobState.updateTransactions(updated);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }
}
