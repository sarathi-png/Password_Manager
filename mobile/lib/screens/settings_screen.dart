import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../api.dart';
import '../models.dart';
import '../theme.dart';

class SettingsScreen extends StatefulWidget {
  final ApiClient api;
  final VaultUser user;
  final VoidCallback onLogout;

  const SettingsScreen({super.key, required this.api, required this.user, required this.onLogout});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _serverCtrl;
  late VaultUser _user;

  @override
  void initState() {
    super.initState();
    _serverCtrl = TextEditingController(text: widget.api.baseUrl);
    _user = widget.user;
  }

  @override
  void dispose() {
    _serverCtrl.dispose();
    super.dispose();
  }

  Future<void> _saveServer() async {
    final url = _serverCtrl.text.trim();
    if (url.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Server address cannot be empty')));
      return;
    }
    await widget.api.saveSession(url);
    HapticFeedback.selectionClick();
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Server address saved')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.background),
        child: SafeArea(
          child: ListView(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
            children: [
              Text('Settings', style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 4),
              Text('Account and connection', style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface1,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.border),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 46,
                      height: 46,
                      decoration: const BoxDecoration(gradient: AppGradients.accent, shape: BoxShape.circle),
                      alignment: Alignment.center,
                      child: Text(
                        _user.username.isEmpty ? '?' : _user.username.substring(0, 1).toUpperCase(),
                        style: GoogleFonts.inter(fontSize: 19, fontWeight: FontWeight.w700, color: AppColors.bg),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(_user.username, style: Theme.of(context).textTheme.titleLarge),
                          const SizedBox(height: 2),
                          Text(
                            '${_user.role} · read-only access',
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: AppColors.accent2,
                              letterSpacing: 0.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface1,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Server', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 4),
                    Text('Where the vault lives', style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 14),
                    TextField(
                      controller: _serverCtrl,
                      keyboardType: TextInputType.url,
                      decoration: const InputDecoration(
                        hintText: 'https://vault.example.com',
                        prefixIcon: Icon(Icons.dns_outlined, size: 20),
                      ),
                    ),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: OutlinedButton(onPressed: _saveServer, child: const Text('Save')),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface1,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Security', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 4),
                    Text('Credentials are encrypted at rest on the server and only decrypted when viewed.', style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        const Icon(Icons.lock_outline_rounded, size: 18, color: AppColors.success),
                        const SizedBox(width: 8),
                        Text('AES-256-GCM encryption', style: Theme.of(context).textTheme.bodyMedium),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        const Icon(Icons.visibility_off_outlined, size: 18, color: AppColors.success),
                        const SizedBox(width: 8),
                        Text('No write access from this app', style: Theme.of(context).textTheme.bodyMedium),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppColors.surface1,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: AppColors.border),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Smart Search', style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 4),
                    Text('Include decrypted passwords in full-text search results (opt-in).', style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 14),
                    StatefulBuilder(
                      builder: (context, setState) => SwitchListTile(
                        title: Text('Include passwords in smart search', style: Theme.of(context).textTheme.bodyMedium),
                        subtitle: Text('When enabled, smart search matches against password content', style: Theme.of(context).textTheme.bodySmall),
                        value: _user.searchIncludePassword,
                        onChanged: (val) async {
                          try {
                            await widget.api.updateUserSettings(searchIncludePassword: val);
                            setState(() => _user = widget.api.user!);
                            HapticFeedback.selectionClick();
                          } catch (e) {
                            if (!mounted) return;
                            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
                          }
                        },
                        activeThumbColor: AppColors.accent2,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              FilledButton.icon(
                onPressed: () => _confirmLogout(),
                style: FilledButton.styleFrom(
                  backgroundColor: AppColors.danger.withValues(alpha: 0.14),
                  foregroundColor: AppColors.danger,
                ),
                icon: const Icon(Icons.logout_rounded, size: 18),
                label: const Text('Sign out'),
              ),
              const SizedBox(height: 20),
              Center(
                child: Text(
                  'Vault mobile · v1.0.0',
                  style: GoogleFonts.inter(fontSize: 11.5, color: AppColors.text3),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _confirmLogout() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.overlay,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Text('Sign out?', style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.w600)),
        content: Text('You will need to log in again to view the vault.', style: Theme.of(context).textTheme.bodyMedium),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(backgroundColor: AppColors.danger),
            child: const Text('Sign out'),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      await widget.api.clearSession();
      widget.onLogout();
    }
  }
}