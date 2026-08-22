import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../models.dart';
import '../theme.dart';

class DetailSheet extends StatefulWidget {
  final VaultEntry entry;

  const DetailSheet({super.key, required this.entry});

  @override
  State<DetailSheet> createState() => _DetailSheetState();
}

class _DetailSheetState extends State<DetailSheet> {
  bool _revealed = false;

  Future<void> _copy(String text, String label) async {
    await Clipboard.setData(ClipboardData(text: text));
    HapticFeedback.mediumImpact();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$label copied')));
  }

  @override
  Widget build(BuildContext context) {
    final entry = widget.entry;
    final accent = categoryColor(entry.category);
    final strength = _strength(entry.password);

    return Container(
      decoration: BoxDecoration(
        color: AppColors.overlay.withValues(alpha: 0.82),
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
          child: SafeArea(
            top: false,
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(24, 12, 24, 28),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Center(
                    child: Container(
                      width: 44,
                      height: 4,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                  const SizedBox(height: 22),
                  Row(
                    children: [
                      Container(
                        width: 54,
                        height: 54,
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [accent.withValues(alpha: 0.3), accent.withValues(alpha: 0.1)],
                          ),
                          borderRadius: BorderRadius.circular(15),
                          border: Border.all(color: accent.withValues(alpha: 0.4)),
                        ),
                        alignment: Alignment.center,
                        child: Text(
                          entry.title.isNotEmpty ? entry.title[0].toUpperCase() : '?',
                          style: GoogleFonts.inter(fontSize: 21, fontWeight: FontWeight.w700, color: accent),
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(entry.title, style: Theme.of(context).textTheme.titleLarge),
                            const SizedBox(height: 2),
                            Text(entry.host.isEmpty ? '—' : entry.host, style: Theme.of(context).textTheme.bodySmall),
                          ],
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: accent.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(999),
                        ),
                        child: Text(
                          entry.category,
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w700,
                            color: accent,
                            letterSpacing: 0.4,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 24),
                  _SecretField(
                    label: 'Username',
                    icon: Icons.person_outline,
                    value: entry.username.isEmpty ? '—' : entry.username,
                    onCopy: () => _copy(entry.username, 'Username'),
                  ),
                  const SizedBox(height: 14),
                  _SecretField(
                    label: 'Password',
                    icon: Icons.key_outlined,
                    value: entry.password,
                    obscured: !_revealed,
                    onToggle: () {
                      HapticFeedback.selectionClick();
                      setState(() => _revealed = !_revealed);
                    },
                    onCopy: () => _copy(entry.password, 'Password'),
                  ),
                  if (entry.password.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(4),
                      child: LinearProgressIndicator(
                        value: strength.pct / 100,
                        minHeight: 4,
                        backgroundColor: Colors.white.withValues(alpha: 0.08),
                        valueColor: AlwaysStoppedAnimation(strength.color),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${strength.label} password',
                      style: GoogleFonts.inter(fontSize: 11.5, color: strength.color, fontWeight: FontWeight.w600),
                    ),
                  ],
                  if (entry.notes.isNotEmpty) ...[
                    const SizedBox(height: 18),
                    Text('Notes', style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 6),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: AppColors.surface1.withValues(alpha: 0.7),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppColors.border),
                      ),
                      child: Text(
                        entry.notes,
                        style: GoogleFonts.inter(fontSize: 14, color: AppColors.text2, height: 1.5),
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  Center(
                    child: Text(
                      'Read-only · managed by your administrator',
                      style: GoogleFonts.inter(fontSize: 11.5, color: AppColors.text3),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _SecretField extends StatelessWidget {
  final String label;
  final IconData icon;
  final String value;
  final bool obscured;
  final VoidCallback? onToggle;
  final VoidCallback? onCopy;

  const _SecretField({
    required this.label,
    required this.icon,
    required this.value,
    this.obscured = false,
    this.onToggle,
    this.onCopy,
  });

  @override
  Widget build(BuildContext context) {
    final display = obscured ? '•' * value.length.clamp(8, 18) : value;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface1.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 15, color: AppColors.text3),
              const SizedBox(width: 6),
              Text(
                label,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppColors.text3,
                  letterSpacing: 0.8,
                ),
              ),
              const Spacer(),
              if (onToggle != null)
                IconButton(
                  visualDensity: VisualDensity.compact,
                  icon: Icon(
                    obscured ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                    size: 18,
                    color: AppColors.text2,
                  ),
                  onPressed: onToggle,
                ),
              IconButton(
                visualDensity: VisualDensity.compact,
                icon: const Icon(Icons.copy_rounded, size: 18, color: AppColors.text2),
                onPressed: onCopy,
              ),
            ],
          ),
          const SizedBox(height: 4),
          SelectableText(
            display,
            style: GoogleFonts.inter(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: obscured ? AppColors.text3 : AppColors.text1,
              letterSpacing: obscured ? 2 : 0,
            ),
          ),
        ],
      ),
    );
  }
}

({String label, Color color, int pct}) _strength(String pw) {
  var score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 14) score++;
  if (RegExp(r'[A-Z]').hasMatch(pw) && RegExp(r'[a-z]').hasMatch(pw)) score++;
  if (RegExp(r'\d').hasMatch(pw)) score++;
  if (RegExp(r'[^A-Za-z0-9]').hasMatch(pw)) score++;
  if (score <= 1) return (label: 'Weak', color: AppColors.danger, pct: 25);
  if (score <= 3) return (label: 'Fair', color: AppColors.warning, pct: 55);
  if (score == 4) return (label: 'Good', color: AppColors.accent2, pct: 80);
  return (label: 'Strong', color: AppColors.success, pct: 100);
}