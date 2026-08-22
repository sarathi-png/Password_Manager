class VaultUser {
  final int id;
  final String username;
  final String role;

  VaultUser({required this.id, required this.username, required this.role});

  factory VaultUser.fromJson(Map<String, dynamic> json) => VaultUser(
        id: json['id'] as int,
        username: json['username'] as String,
        role: json['role'] as String? ?? 'employee',
      );
}

class VaultEntry {
  final int id;
  final String title;
  final String url;
  final String username;
  final String password;
  final String notes;
  final String category;
  final DateTime updatedAt;

  VaultEntry({
    required this.id,
    required this.title,
    required this.url,
    required this.username,
    required this.password,
    required this.notes,
    required this.category,
    required this.updatedAt,
  });

  factory VaultEntry.fromSummary(Map<String, dynamic> json) => VaultEntry(
        id: json['id'] as int,
        title: json['title'] as String? ?? '',
        url: json['url'] as String? ?? '',
        username: '',
        password: '',
        notes: '',
        category: json['category'] as String? ?? 'other',
        updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ?? DateTime.now(),
      );

  factory VaultEntry.fromDetail(Map<String, dynamic> json) => VaultEntry(
        id: json['id'] as int,
        title: json['title'] as String? ?? '',
        url: json['url'] as String? ?? '',
        username: json['username'] as String? ?? '',
        password: json['password'] as String? ?? '',
        notes: json['notes'] as String? ?? '',
        category: json['category'] as String? ?? 'other',
        updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ?? DateTime.now(),
      );

  String get host {
    final clean = url.replaceFirst(RegExp(r'^https?://'), '').replaceFirst(RegExp(r'^www\.'), '');
    final slash = clean.indexOf('/');
    return slash == -1 ? clean : clean.substring(0, slash);
  }
}
