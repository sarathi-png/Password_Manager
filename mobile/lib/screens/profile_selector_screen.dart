import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../api.dart';
import '../models.dart';
import '../theme.dart';

class ProfileSelectorScreen extends StatefulWidget {
  final ApiClient api;
  final VoidCallback onProfileSelected;

  const ProfileSelectorScreen({super.key, required this.api, required this.onProfileSelected});

  @override
  State<ProfileSelectorScreen> createState() => _ProfileSelectorScreenState();
}

class _ProfileSelectorScreenState extends State<ProfileSelectorScreen> {
  List<VaultProfile> _profiles = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadProfiles();
  }

  Future<void> _loadProfiles() async {
    try {
      final profiles = await widget.api.listProfiles();
      setState(() {
        _profiles = profiles;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _selectProfile(VaultProfile profile) async {
    if (profile.hasPin) {
      // Show PIN dialog
      final pin = await _showPinDialog(profile.name);
      if (pin == null) return;
      try {
        await widget.api.selectProfile(profile.id, pin: pin);
        HapticFeedback.selectionClick();
        widget.onProfileSelected();
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Invalid PIN')));
      }
    } else {
      try {
        await widget.api.selectProfile(profile.id);
        HapticFeedback.selectionClick();
        widget.onProfileSelected();
      } catch (e) {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
      }
    }
  }

  Future<String?> _showPinDialog(String profileName) async {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.overlay,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Text('Enter PIN', style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.w600)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text('Enter PIN for $profileName', style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 12),
            TextField(
              controller: controller,
              keyboardType: TextInputType.number,
              obscureText: true,
              autofocus: true,
              decoration: const InputDecoration(hintText: 'PIN'),
              onSubmitted: (val) => Navigator.pop(context, val),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('OK'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.background),
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 24, 24, 0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Who\'s watching?', style: Theme.of(context).textTheme.headlineSmall),
                    const SizedBox(height: 4),
                    Text('Select a profile to continue', style: Theme.of(context).textTheme.bodySmall),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Expanded(
                child: _loading
                    ? const Center(child: CircularProgressIndicator())
                    : _error != null
                        ? Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text('Error: $_error', style: Theme.of(context).textTheme.bodySmall),
                                const SizedBox(height: 12),
                                OutlinedButton(onPressed: _loadProfiles, child: const Text('Retry')),
                              ],
                            ),
                          )
                        : _profiles.isEmpty
                            ? Center(
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.person_add_outlined, size: 48, color: AppColors.text3),
                                    const SizedBox(height: 12),
                                    Text('No profiles yet', style: Theme.of(context).textTheme.bodyMedium),
                                    const SizedBox(height: 8),
                                    Text('Ask your admin to create a profile', style: Theme.of(context).textTheme.bodySmall),
                                  ],
                                ),
                              )
                            : GridView.builder(
                                padding: const EdgeInsets.symmetric(horizontal: 24),
                                gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisCount: 2,
                                  mainAxisSpacing: 16,
                                  crossAxisSpacing: 16,
                                  childAspectRatio: 0.85,
                                ),
                                itemCount: _profiles.length,
                                itemBuilder: (context, index) {
                                  final profile = _profiles[index];
                                  return _ProfileCard(
                                    profile: profile,
                                    onTap: () => _selectProfile(profile),
                                  );
                                },
                              ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ProfileCard extends StatelessWidget {
  final VaultProfile profile;
  final VoidCallback onTap;

  const _ProfileCard({required this.profile, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.surface1,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: const BoxDecoration(gradient: AppGradients.accent, shape: BoxShape.circle),
              child: profile.avatarUrl.isNotEmpty
                  ? ClipOval(
                      child: Image.network(
                        profile.avatarUrl,
                        width: 64,
                        height: 64,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Icon(Icons.person, color: AppColors.bg),
                      ),
                    )
                  : Icon(Icons.person, color: AppColors.bg),
            ),
            const SizedBox(height: 12),
            Text(
              profile.name,
              style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            if (profile.hasPin)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Icon(Icons.lock_outline, size: 14, color: AppColors.text3),
              ),
          ],
        ),
      ),
    );
  }
}
