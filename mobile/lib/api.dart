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

  String baseUrl = '';
  String? _token;
  VaultUser? user;

  Future<void> loadSession() async {
    final prefs = await SharedPreferences.getInstance();
    baseUrl = prefs.getString(_serverKey) ?? '';
    _token = await _storage.read(key: _tokenKey);
  }

  Future<void> saveSession(String baseUrl) async {
    this.baseUrl = baseUrl;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_serverKey, baseUrl);
    if (_token != null) {
      await _storage.write(key: _tokenKey, value: _token);
    }
  }

  Future<void> clearSession() async {
    _token = null;
    user = null;
    await _storage.delete(key: _tokenKey);
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
    ).timeout(const Duration(seconds: 15));
    _check(resp);
    final body = _decode(resp) as Map<String, dynamic>;
    _token = body['access_token'] as String;
    user = await me();
    return user!;
  }

  Future<VaultUser> me() async {
    final resp = await http.get(_uri('/api/auth/me'), headers: _headers).timeout(const Duration(seconds: 15));
    _check(resp);
    user = VaultUser.fromJson(_decode(resp) as Map<String, dynamic>);
    return user!;
  }

  Future<List<VaultEntry>> listEntries({String query = '', String category = ''}) async {
    final params = <String, String>{
      if (query.isNotEmpty) 'q': query,
      if (category.isNotEmpty) 'category': category,
    };
    final uri = _uri('/api/entries').replace(queryParameters: params.isEmpty ? null : params);
    final resp = await http.get(uri, headers: _headers).timeout(const Duration(seconds: 20));
    _check(resp);
    final list = _decode(resp) as List<dynamic>;
    return list.map((e) => VaultEntry.fromSummary(e as Map<String, dynamic>)).toList();
  }

  Future<VaultEntry> getEntry(int id) async {
    final resp = await http.get(_uri('/api/entries/$id'), headers: _headers).timeout(const Duration(seconds: 20));
    _check(resp);
    return VaultEntry.fromDetail(_decode(resp) as Map<String, dynamic>);
  }
}
