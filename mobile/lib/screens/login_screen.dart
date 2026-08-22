import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../api.dart';
import '../models.dart';
import '../theme.dart';

class LoginScreen extends StatefulWidget {
  final ApiClient api;
  final ValueChanged<VaultUser> onLoggedIn;

  const LoginScreen({super.key, required this.api, required this.onLoggedIn});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _serverCtrl = TextEditingController();
  bool _obscure = true;
  bool _loading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _serverCtrl.text = widget.api.baseUrl;
  }

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    _serverCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final user = await widget.api.login(_usernameCtrl.text.trim(), _passwordCtrl.text);
      await widget.api.saveSession(_serverCtrl.text.trim());
      widget.onLoggedIn(user);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (_) {
      setState(() => _error = 'Cannot reach server — check the address and your connection.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.background),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(28),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Container(
                        width: 62,
                        height: 62,
                        decoration: BoxDecoration(
                          gradient: AppGradients.accent,
                          borderRadius: BorderRadius.circular(18),
                          boxShadow: [
                            BoxShadow(
                              color: AppColors.accent1.withValues(alpha: 0.35),
                              blurRadius: 24,
                              offset: const Offset(0, 8),
                            ),
                          ],
                        ),
                        alignment: Alignment.center,
                        child: const Icon(Icons.shield_rounded, size: 32, color: AppColors.bg),
                      ),
                      const SizedBox(height: 18),
                      Text(
                        'Vault',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.fraunces(fontSize: 38, fontWeight: FontWeight.w500, color: AppColors.text1),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Employee access · read-only vault',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(fontSize: 13.5, color: AppColors.text3),
                      ),
                      const SizedBox(height: 32),
                      if (_error != null) ...[
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: AppColors.danger.withValues(alpha: 0.1),
                            border: Border.all(color: AppColors.danger.withValues(alpha: 0.3)),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Text(_error!, style: GoogleFonts.inter(fontSize: 13.5, color: AppColors.danger)),
                        ),
                        const SizedBox(height: 16),
                      ],
                      TextFormField(
                        controller: _usernameCtrl,
                        textInputAction: TextInputAction.next,
                        autofillHints: const [AutofillHints.username],
                        decoration: const InputDecoration(labelText: 'Username', prefixIcon: Icon(Icons.person_outline)),
                        validator: (v) => (v == null || v.trim().isEmpty) ? 'Enter your username' : null,
                      ),
                      const SizedBox(height: 14),
                      TextFormField(
                        controller: _passwordCtrl,
                        obscureText: _obscure,
                        textInputAction: TextInputAction.done,
                        autofillHints: const [AutofillHints.password],
                        onFieldSubmitted: (_) => _submit(),
                        decoration: InputDecoration(
                          labelText: 'Password',
                          prefixIcon: const Icon(Icons.key_outlined),
                          suffixIcon: IconButton(
                            icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                            onPressed: () => setState(() => _obscure = !_obscure),
                          ),
                        ),
                        validator: (v) => (v == null || v.isEmpty) ? 'Enter your password' : null,
                      ),
                      const SizedBox(height: 14),
                      TextFormField(
                        controller: _serverCtrl,
                        keyboardType: TextInputType.url,
                        decoration: const InputDecoration(
                          labelText: 'Server address',
                          hintText: 'https://vault.example.com',
                          prefixIcon: Icon(Icons.dns_outlined),
                        ),
                      ),
                      const SizedBox(height: 24),
                      FilledButton(
                        onPressed: _loading ? null : _submit,
                        style: FilledButton.styleFrom(
                          backgroundColor: Colors.transparent,
                          foregroundColor: AppColors.bg,
                          shadowColor: Colors.transparent,
                        ).copyWith(
                          backgroundColor: WidgetStateProperty.all(AppColors.accent1),
                          overlayColor: WidgetStateProperty.all(Colors.white.withValues(alpha: 0.1)),
                        ),
                        child: _loading
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(strokeWidth: 2.4, color: Colors.white),
                              )
                            : Text('Unlock vault', style: GoogleFonts.inter(fontSize: 15.5, fontWeight: FontWeight.w700)),
                      ),
                      const SizedBox(height: 18),
                      Text(
                        'Read-only access — password changes are made by your administrator on the web console.',
                        textAlign: TextAlign.center,
                        style: GoogleFonts.inter(fontSize: 12, color: AppColors.text3, height: 1.5),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
