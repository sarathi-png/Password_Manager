class VaultUser {
  final int id;
  final String username;
  final String role;
  final int? districtId;
  final int? blockId;
  final String? districtName;
  final String? blockName;
  final bool searchIncludePassword;

  VaultUser({required this.id, required this.username, required this.role, this.districtId, this.blockId, this.districtName, this.blockName, this.searchIncludePassword = false});

  factory VaultUser.fromJson(Map<String, dynamic> json) => VaultUser(
        id: json['id'] as int,
        username: json['username'] as String,
        role: json['role'] as String? ?? 'employee',
        districtId: json['district_id'] as int?,
        blockId: json['block_id'] as int?,
        districtName: json['district_name'] as String?,
        blockName: json['block_name'] as String?,
        searchIncludePassword: json['search_include_password'] as bool? ?? false,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'username': username,
        'role': role,
        'district_id': districtId,
        'block_id': blockId,
        'district_name': districtName,
        'block_name': blockName,
        'search_include_password': searchIncludePassword,
      };
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
  final int? profileId;
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
    this.profileId,
    this.tags = const [],
    this.isFavorite = false,
    this.isPinned = false,
  });

  factory VaultEntry.fromSummary(Map<String, dynamic> json) => VaultEntry(
        id: json['id'] as int,
        title: json['title'] as String? ?? '',
        url: json['url'] as String? ?? '',
        username: json['username'] as String? ?? '',
        password: '',
        notes: '',
        category: json['category'] as String? ?? 'other',
        updatedAt: DateTime.tryParse(json['updated_at'] as String? ?? '') ?? DateTime.now(),
        districtId: json['district_id'] as int?,
        blockId: json['block_id'] as int?,
        districtName: json['district_name'] as String?,
        blockName: json['block_name'] as String?,
        isDuplicate: json['is_duplicate'] as bool? ?? false,
        profileId: json['profile_id'] as int?,
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
        profileId: json['profile_id'] as int?,
        tags: (json['tags'] as List?)?.map((e) => e.toString()).toList() ?? [],
        isFavorite: json['is_favorite'] as bool? ?? false,
        isPinned: json['is_pinned'] as bool? ?? false,
      );

  String get host {
    final clean = url.replaceFirst(RegExp(r'^https?://'), '').replaceFirst(RegExp(r'^www\.'), '');
    final slash = clean.indexOf('/');
    return slash == -1 ? clean : clean.substring(0, slash);
  }

  String get registrableDomain {
    final h = host;
    if (h.isEmpty || RegExp(r'^\d+\.\d+\.\d+\.\d+$').hasMatch(h)) return h;
    final labels = h.split('.');
    if (labels.length <= 2) return h;
    final lastTwo = labels.sublist(labels.length - 2).join('.');
    if (_multiPartTlds.contains(lastTwo) && labels.length >= 3) {
      return labels.sublist(labels.length - 3).join('.');
    }
    return lastTwo;
  }
}

const _multiPartTlds = {
  'co.uk', 'org.uk', 'ac.uk', 'gov.uk',
  'co.in', 'net.in', 'org.in', 'firm.in', 'gen.in', 'ac.in', 'res.in',
  'com.au', 'net.au', 'org.au', 'edu.au', 'gov.au',
  'co.jp', 'ne.jp', 'or.jp', 'ac.jp', 'go.jp',
  'com.br', 'com.mx', 'com.ar', 'com.cn', 'com.sg', 'co.nz', 'co.za',
};

const _brandNames = {
  'google': 'Google', 'gmail': 'Gmail', 'youtube': 'YouTube', 'facebook': 'Facebook',
  'instagram': 'Instagram', 'whatsapp': 'WhatsApp', 'amazon': 'Amazon', 'flipkart': 'Flipkart',
  'microsoft': 'Microsoft', 'apple': 'Apple', 'linkedin': 'LinkedIn', 'twitter': 'Twitter',
  'netflix': 'Netflix', 'github': 'GitHub', 'paypal': 'PayPal', 'irctc': 'IRCTC', 'sbi': 'SBI',
};

String displayNameForDomain(String reg) {
  if (reg.isEmpty || reg == 'no-host') return reg;
  final labels = reg.split('.').where((l) => l.isNotEmpty).toList();
  if (labels.isEmpty) return reg;
  String core;
  if (labels.length >= 3 && _multiPartTlds.contains('${labels[labels.length - 2]}.${labels.last}')) {
    core = labels[labels.length - 3];
  } else if (labels.length >= 2) {
    core = labels[labels.length - 2];
  } else {
    core = labels.first;
  }
  if (_brandNames.containsKey(core)) return _brandNames[core]!;
  if (core.isEmpty) return reg;
  return core[0].toUpperCase() + core.substring(1);
}


class VaultProfile {
  final int id;
  final String name;
  final String avatarUrl;
  final bool hasPin;
  final int userCount;

  VaultProfile({
    required this.id,
    required this.name,
    this.avatarUrl = '',
    this.hasPin = false,
    this.userCount = 0,
  });

  factory VaultProfile.fromJson(Map<String, dynamic> json) => VaultProfile(
        id: json['id'] as int,
        name: json['name'] as String? ?? '',
        avatarUrl: json['avatar_url'] as String? ?? '',
        hasPin: json['has_pin'] as bool? ?? false,
        userCount: json['user_count'] as int? ?? 0,
      );
}
