import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Returns background and foreground colors for a category chip to match the React results table.
(Border?, Color, Color) getCategoryChipStyle(String? category) {
  if (category == null || category.isEmpty) {
    return (
      Border.all(color: AppTheme.border),
      AppTheme.textMuted,
      AppTheme.bg,
    );
  }
  final v = category.toLowerCase();
  if (v.contains('income') || v.contains('salary')) {
    return (null, AppTheme.success, const Color(0x2622C55E)); // success-muted
  }
  if (v.contains('grocery') || v.contains('food') || v.contains('dining') || v.contains('drink')) {
    return (Border.all(color: const Color(0x99FB923C)), const Color(0xFFC05621), const Color(0x1FFB923C));
  }
  if (v.contains('rent') || v.contains('housing') || v.contains('mortgage')) {
    return (Border.all(color: const Color(0x803B82F6)), const Color(0xFF1D4ED8), const Color(0x1F3B82F6));
  }
  if (v.contains('travel') || v.contains('flight') || v.contains('transport') || v.contains('gas')) {
    return (Border.all(color: const Color(0x800EA5E9)), const Color(0xFF0369A1), const Color(0x1F0EA5E9));
  }
  if (v.contains('entertain')) {
    return (Border.all(color: const Color(0x80A855F7)), const Color(0xFF6D28D9), const Color(0x1FA855F7));
  }
  if (v.contains('subscription')) {
    return (Border.all(color: const Color(0x8014B8A6)), const Color(0xFF0F766E), const Color(0x2614B8A6));
  }
  if (v.contains('shopping') || v.contains('store') || v.contains('retail')) {
    return (Border.all(color: const Color(0x80F59E0B)), const Color(0xFFB45309), const Color(0x26F59E0B));
  }
  if (v.contains('utilit') || v.contains('bill') || v.contains('electric') || v.contains('water')) {
    return (Border.all(color: const Color(0x8064748B)), const Color(0xFF475569), const Color(0x2664748B));
  }
  if (v.contains('health') || v.contains('medical') || v.contains('pharmacy')) {
    return (Border.all(color: const Color(0x66F43F5E)), const Color(0xFFBE123C), const Color(0x1FF43F5E));
  }
  if (v.contains('software') || v.contains('saas') || v.contains('internet')) {
    return (Border.all(color: const Color(0x808B5CF6)), const Color(0xFF5B21B6), const Color(0x268B5CF6));
  }
  // default / fallback
  return (Border.all(color: AppTheme.primary.withValues(alpha: 0.35)), AppTheme.primary, AppTheme.primarySubtle);
}

class CategoryChip extends StatelessWidget {
  const CategoryChip({super.key, required this.category});

  final String category;

  @override
  Widget build(BuildContext context) {
    final (border, fg, bg) = getCategoryChipStyle(category);
    final label = category.isEmpty ? 'Uncategorized' : category;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        border: border,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w500,
          color: fg,
        ),
      ),
    );
  }
}
