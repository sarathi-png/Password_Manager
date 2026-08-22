import 'package:flutter/material.dart';

import 'api.dart';
import 'models.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/settings_screen.dart';
import 'theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const VaultApp());
}

class VaultApp extends StatefulWidget {
  const VaultApp({super.key});

  @override
  State<VaultApp> createState() => _VaultAppState();
}

class _VaultAppState extends State<VaultApp> {
  final ApiClient _api = ApiClient();
  VaultUser? _user;
  bool _booted = false;

  @override
  void initState() {
    super.initState();
    _bootstrap();
  }

  Future<void> _bootstrap() async {
    await _api.loadSession();
    if (_api.isLoggedIn && _api.baseUrl.isNotEmpty) {
      try {
        _user = await _api.me();
      } on ApiException catch (e) {
        if (e.statusCode == 401) {
          await _api.clearSession();
        }
      } catch (_) {
        // server unreachable — keep session, show login with error path
      }
    }
    if (mounted) setState(() => _booted = true);
  }

  void _onLoggedIn(VaultUser user) {
    setState(() => _user = user);
  }

  void _onLogout() {
    setState(() => _user = null);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Vault',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.dark,
      home: _booted ? _buildRoot() : const _SplashScreen(),
    );
  }

  Widget _buildRoot() {
    if (_user == null) {
      return LoginScreen(api: _api, onLoggedIn: _onLoggedIn);
    }
    return _MainShell(api: _api, user: _user!, onLogout: _onLogout);
  }
}

class _MainShell extends StatefulWidget {
  final ApiClient api;
  final VaultUser user;
  final VoidCallback onLogout;

  const _MainShell({required this.api, required this.user, required this.onLogout});

  @override
  State<_MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<_MainShell> {
  int _index = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _index,
        children: [
          HomeScreen(api: widget.api),
          SettingsScreen(api: widget.api, user: widget.user, onLogout: widget.onLogout),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.shield_outlined),
            selectedIcon: Icon(Icons.shield_rounded),
            label: 'Vault',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings_rounded),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}

class _SplashScreen extends StatelessWidget {
  const _SplashScreen();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.background),
        child: const Center(
          child: SizedBox(
            width: 44,
            height: 44,
            child: CircularProgressIndicator(strokeWidth: 3),
          ),
        ),
      ),
    );
  }
}