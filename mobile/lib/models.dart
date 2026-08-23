class VaultUser {
  final int id;
  final String username;
  final String role;
  final int? districtId;
  final int? blockId;
  final String? districtName;
  final String? blockName;

  VaultUser({required this.id, required this.username, required this.role, this.districtId, this.blockId, this.districtName, this.blockName});

  factory VaultUser.fromJson(Map<String, dynamic> json) => VaultUser(
        id: json['id'] as int,
        username: json['username'] as String,
        role: json['role'] as String? ?? 'employee',
        districtId: json['district_id'] as int?,
        blockId: json['block_id'] as int?,
        districtName: json['district_name'] as String?,
        blockName: json['block_name'] as String?,
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
  final int? districtId;
  final int? blockId;
  final String? districtName;
  final String? blockName;
  final bool isDuplicate;
  final List<String> tags;
  final bool isFavorite;
  final bool isPinned;

  VaultEntry({
    required this.id,
    required this.title,
    required this.url,
    required this.username,
    required this.password,
    required this.notes,
    required this.category,
    required this.updatedAt,
    this.districtId,
    this.blockId,
    this.districtName,
    this.blockName,
    this.isDuplicate = false,
    this.tags = const [],
    this.isFavorite = false,
    this.isPinned = false,
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
        districtId: json['district_id'] as int?,
        blockId: json['block_id'] as int?,
        districtName: json['district_name'] as String?,
        blockName: json['block_name'] as String?,
        isDuplicate: json['is_duplicate'] as bool? ?? false,
        tags: (json['tags'] as List?)?.map((e) => e.toString()).toList() ?? [],
        isFavorite: json['is_favorite'] as bool? ?? false,
        isPinned: json['is_pinned'] as bool? ?? false,
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
        districtId: json['district_id'] as int?,
        blockId: json['block_id'] as int?,
        districtName: json['district_name'] as String?,
        blockName: json['block_name'] as String?,
        isDuplicate: json['is_duplicate'] as bool? ?? false,
        tags: (json['tags'] as List?)?.map((e) => e.toString()).toList() ?? [],
        isFavorite: json['is_favorite'] as bool? ?? false,
        isPinned: json['is_pinned'] as bool? ?? false,
      );

  String get host {
    final clean = url.replaceFirst(RegExp(r'^https?://'), '').replaceFirst(RegExp(r'^www\.'), '');
    final slash = clean.indexOf('/');
    return slash == -1 ? clean : clean.substring(0, slash);
  }
}
