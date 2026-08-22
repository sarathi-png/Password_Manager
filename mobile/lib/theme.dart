import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppColors {
  static const Color bg = Color(0xFF0B0E14);
  static const Color surface1 = Color(0xFF12151D);
  static const Color surface2 = Color(0xFF1A1F2A);
  static const Color overlay = Color(0xFF222835);
  static const Color border = Color(0x1217171F);
  static const Color borderStrong = Color(0x1FFFFFFF);

  static const Color accent1 = Color(0xFF8B5CF6);
  static const Color accent2 = Color(0xFF22D3EE);

  static const Color text1 = Color(0xFFF2F4F8);
  static const Color text2 = Color(0xFF9CA3AF);
  static const Color text3 = Color(0xFF6B7280);

  static const Color success = Color(0xFF34D399);
  static const Color warning = Color(0xFFFBBF24);
  static const Color danger = Color(0xFFF87171);
}

class AppGradients {
  static const LinearGradient accent = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [AppColors.accent1, AppColors.accent2],
  );

  static const LinearGradient background = LinearGradient(
    begin: Alignment.topRight,
    end: Alignment.bottomLeft,
    colors: [
      Color(0x1F8B5CF6),
      AppColors.bg,
      AppColors.bg,
      Color(0x1422D3EE),
    ],
    stops: [0.0, 0.35, 0.75, 1.0],
  );
}

class AppTheme {
  static ThemeData get dark {
    final base = ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: const ColorScheme.dark(
        primary: AppColors.accent1,
        secondary: AppColors.accent2,
        surface: AppColors.surface1,
        onSurface: AppColors.text1,
        error: AppColors.danger,
      ),
      scaffoldBackgroundColor: AppColors.bg,
    );

    return base.copyWith(
      textTheme: GoogleFonts.interTextTheme(base.textTheme).copyWith(
        displayLarge: GoogleFonts.fraunces(
          fontSize: 44,
          fontWeight: FontWeight.w500,
          color: AppColors.text1,
          height: 1.05,
        ),
        displayMedium: GoogleFonts.fraunces(
          fontSize: 30,
          fontWeight: FontWeight.w500,
          color: AppColors.text1,
          height: 1.1,
        ),
        headlineSmall: GoogleFonts.fraunces(
          fontSize: 22,
          fontWeight: FontWeight.w500,
          color: AppColors.text1,
        ),
        titleLarge: GoogleFonts.inter(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: AppColors.text1,
        ),
        bodyLarge: GoogleFonts.inter(fontSize: 16, color: AppColors.text1),
        bodyMedium: GoogleFonts.inter(fontSize: 14.5, color: AppColors.text2),
        bodySmall: GoogleFonts.inter(fontSize: 12.5, color: AppColors.text3),
        labelLarge: GoogleFonts.inter(fontSize: 14.5, fontWeight: FontWeight.w600),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.bg,
        elevation: 0,
        centerTitle: false,
        surfaceTintColor: Colors.transparent,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.surface1,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.accent1, width: 1.4),
        ),
        hintStyle: const TextStyle(color: AppColors.text3),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.accent1,
          foregroundColor: Colors.white,
          minimumSize: const Size(0, 50),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: GoogleFonts.inter(fontSize: 15.5, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.text1,
          side: const BorderSide(color: AppColors.borderStrong),
          minimumSize: const Size(0, 46),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: AppColors.surface1,
        indicatorColor: AppColors.accent1.withValues(alpha: 0.18),
        height: 68,
        labelTextStyle: WidgetStateProperty.all(
          GoogleFonts.inter(fontSize: 11.5, fontWeight: FontWeight.w600),
        ),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          final selected = states.contains(WidgetState.selected);
          return IconThemeData(
            color: selected ? AppColors.accent2 : AppColors.text3,
          );
        }),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: AppColors.overlay,
        contentTextStyle: GoogleFonts.inter(fontSize: 14, color: AppColors.text1),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      dividerTheme: const DividerThemeData(color: AppColors.border),
      progressIndicatorTheme: const ProgressIndicatorThemeData(color: AppColors.accent2),
    );
  }
}

const List<String> kCategories = [
  'email',
  'banking',
  'social',
  'shopping',
  'work',
  'entertainment',
  'other',
];

Color categoryColor(String category) {
  switch (category) {
    case 'email':
      return AppColors.accent2;
    case 'banking':
      return AppColors.warning;
    case 'social':
      return AppColors.accent1;
    case 'shopping':
      return AppColors.success;
    case 'work':
      return AppColors.accent1;
    case 'entertainment':
      return AppColors.accent2;
    default:
      return AppColors.text3;
  }
}
