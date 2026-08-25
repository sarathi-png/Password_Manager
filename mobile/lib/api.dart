import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'models.dart';

class ApiException implements Exception {
  final String message;
  final int statusCode;
  ApiException(this.message, [this.statusCode = 0]);

  @override
  String toString() => message;
}

class ApiClient {
  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'vault_token';
  static const _serverKey = 'vault_server';
  static const _userKey = 'vault_user';
  // Build-time override: flutter build apk --dart-define=API_BASE_URL=http://192.168.1.10:8000
  static const String defaultServer = String.fromEnvironment('API_BASE_URL', defaultValue: 'https://vault-lcgd.onrender.com');

  String baseUrl = defaultServer;
  String? _token;
  VaultUser? user;

  Future<void> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_serverKey);
    baseUrl = (saved == null || saved.isEmpty) ? defaultServer : saved;
    _token = await _storage.read(key: _tokenKey);
    final cachedUser = prefs.getString(_userKey);
    if (cachedUser != null) {
      try {
        user = VaultUser.fromJson(jsonDecode(cachedUser) as Map<String, dynamic>);
      } catch (_) {
        user = null;
      }
    }
  }

  Future<void> saveSession(String baseUrl) async {
    this.baseUrl = baseUrl;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_serverKey, baseUrl);
    await _persistAuth(prefs);
  }

  Future<void> _persistAuth(SharedPreferences prefs) async {
    if (_token != null) {
      await _storage.write(key: _tokenKey, value: _token);
    } else {
      await _storage.delete(key: _tokenKey);
    }
    if (user != null) {
      await prefs.setString(_userKey, jsonEncode(user!.toJson()));
    } else {
      await prefs.remove(_userKey);
    }
  }

  Future<void> clearSession() async {
    _token = null;
    user = null;
    await _storage.delete(key: _tokenKey);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_userKey);
  }

  bool get isLoggedIn => _token != null;

  Uri _uri(String path) {
    final normalized = baseUrl.endsWith('/') ? baseUrl.substring(0, baseUrl.length - 1) : baseUrl;
    return Uri.parse('$normalized$path');
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  dynamic _decode(http.Response resp) {
    if (resp.body.isEmpty) return null;
    try {
      return jsonDecode(resp.body);
    } catch (_) {
      throw ApiException('Invalid server response');
    }
  }

  void _check(http.Response resp) {
    if (resp.statusCode == 401) {
      throw ApiException('Session expired — please log in again', 401);
    }
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      String detail = 'Request failed (${resp.statusCode})';
      try {
        final body = jsonDecode(resp.body);
        if (body is Map && body['detail'] != null) {
          detail = body['detail'] is String ? body['detail'] : jsonEncode(body['detail']);
        }
      } catch (_) {}
      throw ApiException(detail, resp.statusCode);
    }
  }

  Future<VaultUser> login(String username, String password) async {
    final resp = await http.post(
      _uri('/api/auth/login'),
      headers: _headers,
      body: jsonEncode({'username': username, 'password': password}),
    ).timeout(const Duration(seconds: 60));
    _check(resp);
    final body = _decode(resp) as Map<String, dynamic>;
    _token = body['access_token'] as String;
    user = await me();
    await _persistAuth(await SharedPreferences.getInstance());
    return user!;
  }

  Future<VaultUser> me() async {
    final resp = await http.get(_uri('/api/auth/me'), headers: _headers).timeout(const Duration(seconds: 60));
    _check(resp);
    user = VaultUser.fromJson(_decode(resp) as Map<String, dynamic>);
    return user!;
  }

  Future<List<VaultEntry>> listEntries({String query = '', String category = '', int? districtId, int? blockId, bool? isDuplicate, String? tag, bool? isFavorite, bool? isPinned, String sort = 'title', String searchMode = 'basic', bool includePassword = false, int? profileId}) async {
    final params = <String, String>{
      if (query.isNotEmpty) 'q': query,
      if (searchMode != 'basic') 'search_mode': searchMode,
      if (includePassword) 'include_password': 'true',
      if (category.isNotEmpty) 'category': category,
      if (districtId != null) 'district_id': districtId.toString(),
      if (blockId != null) 'block_id': blockId.toString(),
      if (isDuplicate != null) 'is_duplicate': isDuplicate.toString(),
      if (tag != null && tag.isNotEmpty) 'tag': tag,
      if (isFavorite != null) 'is_favorite': isFavorite.toString(),
      if (isPinned != null) 'is_pinned': isPinned.toString(),
      if (sort != 'title') 'sort': sort,
      if (profileId != null) 'profile_id': profileId.toString(),
    };
    final uri = _uri('/api/entries').replace(queryParameters: params.isEmpty ? null : params);
    final resp = await http.get(uri, headers: _headers).timeout(const Duration(seconds: 60));
    _check(resp);
    final list = _decode(resp) as List<dynamic>;
    return list.map((e) => VaultEntry.fromSummary(e as Map<String, dynamic>)).toList();
  }

  Future<VaultEntry> getEntry(int id) async {
    final resp = await http.get(_uri('/api/entries/$id'), headers: _headers).timeout(const Duration(seconds: 60));
    _check(resp);
    return VaultEntry.fromDetail(_decode(resp) as Map<String, dynamic>);
  }

  // Private per-user tags & favorites (works for employee read-only as well)
  Future<List<String>> addTag(int entryId, String tag) async {
    final resp = await http.post(_uri('/api/entries/$entryId/tags'), headers: _headers, body: jsonEncode({'tag': tag})).timeout(const Duration(seconds: 60));
    _check(resp);
    final list = _decode(resp) as List<dynamic>;
    return list.map((e) => e.toString()).toList();
  }

  Future<List<String>> removeTag(int entryId, String tag) async {
    final resp = await http.delete(_uri('/api/entries/$entryId/tags/$tag'), headers: _headers).timeout(const Duration(seconds: 60));
    _check(resp);
    final list = _decode(resp) as List<dynamic>;
    return list.map((e) => e.toString()).toList();
  }

  Future<Map<String, dynamic>> setMeta(int entryId, {bool? isFavorite, bool? isPinned}) async {
    final body = <String, dynamic>{};
    if (isFavorite != null) body['is_favorite'] = isFavorite;
    if (isPinned != null) body['is_pinned'] = isPinned;
    final resp = await http.put(_uri('/api/entries/$entryId/meta'), headers: _headers, body: jsonEncode(body)).timeout(const Duration(seconds: 60));
    _check(resp);
    return _decode(resp) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> listDistricts() async {
    final resp = await http.get(_uri('/api/districts'), headers: _headers).timeout(const Duration(seconds: 60));
    _check(resp);
    final list = _decode(resp) as List<dynamic>;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<List<Map<String, dynamic>>> listBlocks({int? districtId}) async {
    final uri = _uri('/api/blocks').replace(queryParameters: districtId != null ? {'district_id': districtId.toString()} : null);
    final resp = await http.get(uri, headers: _headers).timeout(const Duration(seconds: 60));
    _check(resp);
    final list = _decode(resp) as List<dynamic>;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<List<Map<String, dynamic>>> listGroups({
    String query = '',
    int? districtId,
    int? blockId,
    String searchMode = 'basic',
    int? profileId,
    String category = '',
    bool? isDuplicate,
    bool? isFavorite,
    String? tag,
  }) async {
    final params = <String, String>{
      if (query.isNotEmpty) 'q': query,
      if (searchMode != 'basic') 'search_mode': searchMode,
      if (districtId != null) 'district_id': districtId.toString(),
      if (blockId != null) 'block_id': blockId.toString(),
      if (profileId != null) 'profile_id': profileId.toString(),
      if (category.isNotEmpty) 'category': category,
      if (isDuplicate != null) 'is_duplicate': isDuplicate.toString(),
      if (isFavorite != null) 'is_favorite': isFavorite.toString(),
      if (tag != null && tag.isNotEmpty) 'tag': tag,
    };
    final uri = _uri('/api/entries/groups').replace(queryParameters: params.isEmpty ? null : params);
    final resp = await http.get(uri, headers: _headers).timeout(const Duration(seconds: 60));
    _check(resp);
    final list = _decode(resp) as List<dynamic>;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<List<Map<String, dynamic>>> listCategories() async {
    final resp = await http.get(_uri('/api/categories'), headers: _headers).timeout(const Duration(seconds: 60));
    _check(resp);
    final list = _decode(resp) as List<dynamic>;
    return list.map((e) => e as Map<String, dynamic>).toList();
  }

  Future<Map<String, dynamic>> setGlobalCategory(int entryId, int categoryId, {int? subcategoryId}) async {
    final body = <String, dynamic>{'category_id': categoryId};
    if (subcategoryId != null) body['subcategory_id'] = subcategoryId;
    final resp = await http.put(_uri('/api/entries/$entryId/category'), headers: _headers, body: jsonEncode(body)).timeout(const Duration(seconds: 60));
    _check(resp);
    return _decode(resp) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> setMyCategory(int entryId, int categoryId, {int? subcategoryId}) async {
    final body = <String, dynamic>{'category_id': categoryId};
    if (subcategoryId != null) body['subcategory_id'] = subcategoryId;
    final resp = await http.put(_uri('/api/entries/$entryId/my-category'), headers: _headers, body: jsonEncode(body)).timeout(const Duration(seconds: 60));
    _check(resp);
    return _decode(resp) as Map<String, dynamic>;
  }

  Future<void> updateUserSettings({bool? searchIncludePassword}) async {
    final body = <String, dynamic>{};
    if (searchIncludePassword != null) body['search_include_password'] = searchIncludePassword;
    if (body.isEmpty) return;
    final resp = await http.put(_uri('/api/users/me'), headers: _headers, body: jsonEncode(body)).timeout(const Duration(seconds: 60));
    _check(resp);
    final data = _decode(resp) as Map<String, dynamic>;
    user = VaultUser.fromJson(data);
  }

  // --- Profiles ---

  int? currentProfileId;

  Future<List<VaultProfile>> listProfiles() async {
    final resp = await http.get(_uri('/api/profiles'), headers: _headers).timeout(const Duration(seconds: 60));
    _check(resp);
    final list = _decode(resp) as List;
    return list.map((e) => VaultProfile.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<VaultProfile> createProfile(String name, {String avatarUrl = ''}) async {
    final resp = await http.post(_uri('/api/profiles'), headers: _headers, body: jsonEncode({'name': name, 'avatar_url': avatarUrl})).timeout(const Duration(seconds: 60));
    _check(resp);
    return VaultProfile.fromJson(_decode(resp) as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> selectProfile(int profileId, {String? pin}) async {
    final body = <String, dynamic>{};
    if (pin != null) body['pin'] = pin;
    final resp = await http.post(_uri('/api/profiles/$profileId/select'), headers: _headers, body: jsonEncode(body)).timeout(const Duration(seconds: 60));
    _check(resp);
    final data = _decode(resp) as Map<String, dynamic>;
    currentProfileId = profileId;
    return data;
  }

  Future<void> setProfilePin(int profileId, String pin) async {
    final resp = await http.post(_uri('/api/profiles/$profileId/pin'), headers: _headers, body: jsonEncode({'pin': pin})).timeout(const Duration(seconds: 60));
    _check(resp);
  }

  Future<List<String>> listAvatars() async {
    final resp = await http.get(_uri('/api/profiles/avatars'), headers: _headers).timeout(const Duration(seconds: 60));
    _check(resp);
    final data = _decode(resp) as Map<String, dynamic>;
    return (data['avatars'] as List).map((e) => e.toString()).toList();
  }
}
