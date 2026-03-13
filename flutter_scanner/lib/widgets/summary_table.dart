import 'package:flutter/material.dart';

import '../state/job_state.dart';
import '../theme/app_theme.dart';

class SummaryTable extends StatelessWidget {
  const SummaryTable({super.key, required this.jobState});

  final JobState jobState;

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: jobState,
      builder: (context, _) {
        final summary = jobState.summaryByCategory;
        final currency = jobState.currency;
        if (summary.isEmpty) return const SizedBox.shrink();
        return Container(
          margin: const EdgeInsets.fromLTRB(20, 16, 20, 0),
          padding: const EdgeInsets.all(20),
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
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Summary by category${currency != null && currency.isNotEmpty ? ' ($currency)' : ''}',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                      color: AppTheme.text,
                    ),
              ),
              const SizedBox(height: 16),
              Container(
                constraints: const BoxConstraints(maxWidth: 360),
                decoration: BoxDecoration(
                  color: AppTheme.bg,
                  border: Border.all(color: AppTheme.border),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Table(
                  columnWidths: const {
                    0: FlexColumnWidth(2),
                    1: FlexColumnWidth(1),
                  },
                  border: TableBorder(
                    horizontalInside: BorderSide(color: AppTheme.border),
                  ),
                  children: [
                    TableRow(
                      decoration: const BoxDecoration(color: AppTheme.primarySubtle),
                      children: [
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          child: Text(
                            'Category',
                            style: TextStyle(
                              fontSize: 15.2,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.text,
                            ),
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          child: Text(
                            'Total',
                            style: TextStyle(
                              fontSize: 15.2,
                              fontWeight: FontWeight.w600,
                              color: AppTheme.text,
                            ),
                            textAlign: TextAlign.right,
                          ),
                        ),
                      ],
                    ),
                    ...List.generate(summary.length, (i) {
                      final s = summary[i];
                      return TableRow(
                        decoration: BoxDecoration(
                          color: i.isEven ? AppTheme.primarySubtle : AppTheme.surface,
                        ),
                        children: [
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            child: Text(s.category, style: const TextStyle(fontSize: 15.2)),
                          ),
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            child: Text(
                              s.total.toStringAsFixed(2),
                              textAlign: TextAlign.right,
                              style: const TextStyle(
                                fontSize: 15.2,
                                fontFeatures: [FontFeature.tabularFigures()],
                              ),
                            ),
                          ),
                        ],
                      );
                    }),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
