import 'package:flutter_test/flutter_test.dart';

import 'package:vault_mobile/models.dart';
import 'package:vault_mobile/theme.dart';

void main() {
  test('VaultEntry.fromSummary parses list payload', () {
    final entry = VaultEntry.fromSummary({
      'id': 7,
      'title': 'Gmail',
      'url': 'https://mail.google.com',
      'category': 'email',
      'updated_at': '2026-08-01T10:00:00Z',
    });
    expect(entry.id, 7);
    expect(entry.title, 'Gmail');
    expect(entry.host, 'mail.google.com');
    expect(entry.category, 'email');
  });

  test('VaultEntry.fromDetail parses full payload', () {
    final entry = VaultEntry.fromDetail({
      'id': 1,
      'title': 'GitHub',
      'url': 'https://github.com/octocat',
      'username': 'octocat',
      'password': 'ghpass',
      'notes': 'work',
      'category': 'work',
      'updated_at': '2026-08-01T10:00:00Z',
    });
    expect(entry.username, 'octocat');
    expect(entry.password, 'ghpass');
    expect(entry.host, 'github.com');
  });

  test('host strips protocol and www', () {
    final entry = VaultEntry.fromSummary({
      'id': 2,
      'title': 'X',
      'url': 'http://www.x.com/home',
      'category': 'social',
      'updated_at': '2026-08-01T10:00:00Z',
    });
    expect(entry.host, 'x.com');
  });

  test('category colors cover all categories', () {
    for (final c in kCategories) {
      expect(categoryColor(c), isNotNull);
    }
  });
}