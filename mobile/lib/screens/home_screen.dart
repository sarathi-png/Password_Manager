import 'dart:async';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../api.dart';
import '../models.dart';
import '../theme.dart';
import 'detail_sheet.dart';

class HomeScreen extends StatefulWidget {
  final ApiClient api;

  const HomeScreen({super.key, required this.api});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _searchCtrl = TextEditingController();
  final _tagCtrl = TextEditingController();
  List<VaultEntry> _entries = [];
  List<Map<String, dynamic>> _categories = []; // API-fetched categories
  bool _loading = true;
  String? _error;
  String _category = '';
  bool _showDup = false;
  bool _showFav = false;
  bool _showPinned = false;
  String _sort = 'title'; // title | recent | favorite
  bool _grouped = true;
  String _searchMode = 'basic'; // basic | smart
  bool _includePassword = false;
  List<Map<String, dynamic>> _groups = [];
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchCtrl.dispose();
    _tagCtrl.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      // Fetch categories if not already loaded
      if (_categories.isEmpty) {
        _categories = await widget.api.listCategories();
      }
      final entries = await widget.api.listEntries(
        query: _searchCtrl.text.trim(),
        category: _category,
        tag: _tagCtrl.text.trim().isEmpty ? null : _tagCtrl.text.trim(),
        isDuplicate: _showDup ? true : null,
        isFavorite: _showFav ? true : null,
        isPinned: _showPinned ? true : null,
        sort: _sort,
        searchMode: _searchMode,
        includePassword: _includePassword,
        profileId: widget.api.currentProfileId,
      );
      List<Map<String, dynamic>> groups = [];
      if (_grouped) {
        try {
          groups = await widget.api.listGroups(
            query: _searchCtrl.text.trim(),
            searchMode: _searchMode,
            profileId: widget.api.currentProfileId,
            category: _category,
            isDuplicate: _showDup ? true : null,
            isFavorite: _showFav ? true : null,
            tag: _tagCtrl.text.trim().isEmpty ? null : _tagCtrl.text.trim(),
          );
        } catch (_) {
          groups = [];
        }
      }
      if (!mounted) return;
      setState(() {
        _entries = entries;
        _groups = groups;
        _loading = false;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.message;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _error = 'Cannot reach the server';
        _loading = false;
      });
    }
  }

  void _onSearchChanged(String _) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), _load);
  }

  void _selectCategory(String category) {
    setState(() => _category = _category == category ? '' : category);
    _load();
  }

  Future<void> _openEntry(VaultEntry entry) async {
    try {
      final detail = await widget.api.getEntry(entry.id);
      if (!mounted) return;
      await showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        barrierColor: Colors.black.withValues(alpha: 0.6),
        builder: (_) => DetailSheet(api: widget.api, entry: detail, onChanged: _load),
      );
      // refresh to get updated tags/fav after sheet closed
      if (mounted) _load();
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    }
  }

  Future<void> _openGroup(String domain) async {
    try {
      final entries = await widget.api.listEntries(query: domain);
      // filter client-side to just this domain's registrable
      final filtered = entries.where((e) => (e.registrableDomain == domain) || e.host.contains(domain)).toList();
      if (!mounted) return;
      await showModalBottomSheet(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => Container(
          decoration: const BoxDecoration(color: AppColors.surface1, borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
          padding: const EdgeInsets.all(16),
          child: SafeArea(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(width: 36, height: 4, decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4))),
                const SizedBox(height: 12),
                Text(displayNameForDomain(domain), style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600)),
                Text('$domain · ${filtered.length} entries', style: GoogleFonts.inter(fontSize: 12, color: AppColors.text3)),
                const SizedBox(height: 12),
                Flexible(
                  child: ListView.builder(
                    shrinkWrap: true,
                    itemCount: filtered.length,
                    itemBuilder: (_, i) => ListTile(
                      title: Text(filtered[i].title, style: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600)),
                      subtitle: Text(filtered[i].username.isNotEmpty ? filtered[i].username : filtered[i].host, style: GoogleFonts.inter(fontSize: 12, color: AppColors.text3)),
                      trailing: const Icon(Icons.chevron_right, size: 18),
                      onTap: () {
                        Navigator.pop(context);
                        _openEntry(filtered[i]);
                      },
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed to load group: $e')));
    }
  }

  Future<void> _promptGroupCategory(Map<String, dynamic> group) async {
    final domain = group['registrable_domain'] as String;
    // simple prompt: choose global vs my
    final isAdmin = widget.api.user?.role == 'admin';
    final cats = await widget.api.listCategories();
    // flatten
    final flat = <Map<String, dynamic>>[];
    for (final c in cats) {
      flat.add(c);
      final children = c['children'] as List? ?? [];
      for (final ch in children) flat.add(ch as Map<String, dynamic>);
    }
    if (!mounted) return;
    final selected = await showDialog<int>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.overlay,
        title: Text('Set category for $domain', style: GoogleFonts.inter(fontSize: 14)),
        content: SizedBox(
          width: double.maxFinite,
          height: 300,
          child: ListView(
            children: flat.map((c) => ListTile(
              title: Text(c['name'] as String),
              subtitle: c['parent_id'] != null ? const Text('subcategory', style: TextStyle(fontSize: 11)) : null,
              onTap: () => Navigator.pop(ctx, c['id'] as int),
            )).toList(),
          ),
        ),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel'))],
      ),
    );
    if (selected == null) return;
    try {
      final ids = (group['entry_ids'] as List).cast<int>();
      if (isAdmin) {
        for (final id in ids) {
          await widget.api.setGlobalCategory(id, selected);
        }
      } else {
        for (final id in ids) {
          await widget.api.setMyCategory(id, selected);
        }
      }
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(isAdmin ? 'Global category updated' : 'My category saved (private)')));
      _load();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Failed: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final user = widget.api.user;
    final scopeLabel = user?.blockName != null
        ? '${user!.districtName ?? ""} › ${user.blockName}'
        : user?.districtName ?? (user?.role == 'admin' ? 'Admin' : 'Workspace');
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: AppGradients.background),
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 0),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('The Vault', style: Theme.of(context).textTheme.headlineSmall),
                          Text(
                            '${_entries.length} credential${_entries.length == 1 ? '' : 's'} · $scopeLabel · read-only',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        gradient: AppGradients.accent,
                        borderRadius: BorderRadius.circular(13),
                        boxShadow: [
                          BoxShadow(
                            color: AppColors.accent1.withValues(alpha: 0.3),
                            blurRadius: 16,
                            offset: const Offset(0, 6),
                          ),
                        ],
                      ),
                      alignment: Alignment.center,
                      child: const Icon(Icons.shield_rounded, size: 22, color: AppColors.bg),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _searchCtrl,
                        onChanged: _onSearchChanged,
                        textInputAction: TextInputAction.search,
                        decoration: const InputDecoration(
                          hintText: 'Search name, URL, tag…',
                          prefixIcon: Icon(Icons.search, color: AppColors.text3),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 110,
                      child: TextField(
                        controller: _tagCtrl,
                        onChanged: _onSearchChanged,
                        decoration: const InputDecoration(
                          hintText: 'Tag',
                          prefixIcon: Icon(Icons.label_outline, size: 18, color: AppColors.text3),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              // Smart filters
              SizedBox(
                height: 38,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  children: [
                    _SmartChip(label: 'Favorites', selected: _showFav, icon: Icons.star_rounded, onTap: () { setState(() => _showFav = !_showFav); _load(); }),
                    _SmartChip(label: 'Pinned', selected: _showPinned, icon: Icons.push_pin, onTap: () { setState(() => _showPinned = !_showPinned); _load(); }),
                    _SmartChip(label: 'Duplicates', selected: _showDup, icon: Icons.copy_rounded, onTap: () { setState(() => _showDup = !_showDup); _load(); }),
                    _SmartChip(
                        label: 'Smart Search',
                        selected: _searchMode == 'smart',
                        icon: Icons.psychology_rounded,
                        onTap: () { setState(() => _searchMode = _searchMode == 'basic' ? 'smart' : 'basic'); _load(); }),
                    _SmartChip(
                        label: _sort == 'title' ? 'Sort: Title' : _sort == 'recent' ? 'Sort: Recent' : 'Sort: Pinned',
                        selected: _sort != 'title',
                        icon: Icons.sort_rounded,
                        onTap: () {
                          setState(() => _sort = _sort == 'title' ? 'recent' : _sort == 'recent' ? 'favorite' : 'title');
                          _load();
                        }),
                    if (_category.isNotEmpty || _showFav || _showDup || _showPinned || _tagCtrl.text.isNotEmpty)
                      _SmartChip(
                          label: 'Clear',
                          selected: false,
                          icon: Icons.clear_rounded,
                          onTap: () {
                            setState(() {
                              _category = '';
                              _showFav = false;
                              _showDup = false;
                              _showPinned = false;
                              _tagCtrl.clear();
                              _searchCtrl.clear();
                              _sort = 'title';
                              _searchMode = 'basic';
                            });
                            _load();
                          }),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 2),
                child: Row(
                  children: [
                    const Icon(Icons.folder_special_rounded, size: 16, color: AppColors.text3),
                    const SizedBox(width: 6),
                    Text('Grouped by host', style: GoogleFonts.inter(fontSize: 12.5, color: AppColors.text3)),
                    const Spacer(),
                    Switch(value: _grouped, onChanged: (v) { setState(() => _grouped = v); _load(); }, materialTapTargetSize: MaterialTapTargetSize.shrinkWrap),
                  ],
                ),
              ),
              SizedBox(
                height: 40,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  children: [
                    _CategoryChip(label: 'All', selected: _category.isEmpty, onTap: () => _selectCategory('')),
                    // Flatten categories (including subcategories) for filter chips
                    for (final c in _categories)
                      for (final cat in [c, ...(c['children'] as List? ?? [])])
                        _CategoryChip(label: cat['name'] as String, selected: _category == cat['name'], onTap: () => _selectCategory(cat['name'] as String)),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Expanded(child: _buildBody()),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return ListView.builder(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
        itemCount: 6,
        itemBuilder: (_, _) => const _SkeletonCard(),
      );
    }
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_rounded, size: 44, color: AppColors.text3),
              const SizedBox(height: 12),
              Text(_error!, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 16),
              OutlinedButton.icon(
                onPressed: _load,
                icon: const Icon(Icons.refresh, size: 18),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }
    if (_grouped) {
      if (_groups.isEmpty) {
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.folder_off_rounded, size: 44, color: AppColors.text3),
              const SizedBox(height: 12),
              Text('No groups', style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 4),
              Text('Try different search or switch to flat', style: Theme.of(context).textTheme.bodySmall),
            ],
          ),
        );
      }
      return RefreshIndicator(
        onRefresh: _load,
        color: AppColors.accent2,
        backgroundColor: AppColors.surface2,
        child: ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
          itemCount: _groups.length,
          separatorBuilder: (_, _) => const SizedBox(height: 10),
          itemBuilder: (context, index) {
            final g = _groups[index];
            return _GroupCard(
              domain: g['registrable_domain'] as String? ?? '',
              displayName: g['display_name'] as String? ?? '',
              count: g['count'] as int? ?? 0,
              category: g['effective_category'] as String? ?? 'Other',
              exactHosts: (g['exact_hosts'] as List?)?.map((e) => e.toString()).toList() ?? [],
              onTap: () => _openGroup(g['registrable_domain'] as String),
              onSetCategory: () => _promptGroupCategory(g),
            );
          },
        ),
      );
    }
    if (_entries.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.search_off_rounded, size: 44, color: AppColors.text3),
            const SizedBox(height: 12),
            Text('No entries found', style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 4),
            Text('Try smart search: name, tag or category', style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: _load,
      color: AppColors.accent2,
      backgroundColor: AppColors.surface2,
      child: ListView.separated(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 24),
        itemCount: _entries.length,
        separatorBuilder: (_, _) => const SizedBox(height: 10),
        itemBuilder: (context, index) => _EntryCard(
          entry: _entries[index],
          onTap: () => _openEntry(_entries[index]),
        ),
      ),
    );
  }
}

class _SmartChip extends StatelessWidget {
  final String label;
  final bool selected;
  final IconData icon;
  final VoidCallback onTap;
  const _SmartChip({required this.label, required this.selected, required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 12),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            color: selected ? AppColors.accent1.withValues(alpha: 0.18) : AppColors.surface1,
            border: Border.all(color: selected ? AppColors.accent1 : AppColors.borderStrong),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 14, color: selected ? AppColors.accent2 : AppColors.text3),
              const SizedBox(width: 4),
              Text(label, style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w600, color: selected ? AppColors.text1 : AppColors.text2)),
            ],
          ),
        ),
      ),
    );
  }
}

class _CategoryChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _CategoryChip({required this.label, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: GestureDetector(
        onTap: onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          padding: const EdgeInsets.symmetric(horizontal: 14),
          alignment: Alignment.center,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: selected ? AppColors.accent1.withValues(alpha: 0.6) : AppColors.borderStrong,
            ),
            gradient: selected
                ? const LinearGradient(colors: [Color(0x408B5CF6), Color(0x2622D3EE)])
                : null,
            color: selected ? null : AppColors.surface1,
          ),
          child: Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 12.5,
              fontWeight: FontWeight.w600,
              color: selected ? AppColors.text1 : AppColors.text2,
            ),
          ),
        ),
      ),
    );
  }
}

class _EntryCard extends StatelessWidget {
  final VaultEntry entry;
  final VoidCallback onTap;

  const _EntryCard({required this.entry, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final initial = entry.title.isNotEmpty ? entry.title[0].toUpperCase() : '?';
    final accent = categoryColor(entry.category);
    return Material(
      color: AppColors.surface1,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: entry.isDuplicate ? AppColors.danger.withValues(alpha: 0.35) : AppColors.border),
            color: entry.isDuplicate ? AppColors.danger.withValues(alpha: 0.04) : null,
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [accent.withValues(alpha: 0.28), accent.withValues(alpha: 0.10)],
                  ),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: accent.withValues(alpha: 0.35)),
                ),
                alignment: Alignment.center,
                child: Text(
                  initial,
                  style: GoogleFonts.inter(fontSize: 17, fontWeight: FontWeight.w700, color: accent),
                ),
              ),
              const SizedBox(width: 13),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Expanded(child: Text(entry.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.text1))),
                      if (entry.isPinned) const Padding(padding: EdgeInsets.only(left:4), child: Icon(Icons.push_pin, size: 14, color: AppColors.accent2)),
                      if (entry.isFavorite) const Padding(padding: EdgeInsets.only(left:2), child: Icon(Icons.star_rounded, size: 16, color: AppColors.warning)),
                      if (entry.isDuplicate) Container(margin: const EdgeInsets.only(left:6), padding: const EdgeInsets.symmetric(horizontal:6, vertical:2), decoration: BoxDecoration(color: AppColors.danger.withValues(alpha:0.12), borderRadius: BorderRadius.circular(6)), child: Text('dup', style: GoogleFonts.inter(fontSize:10, fontWeight: FontWeight.w700, color: AppColors.danger))),
                    ]),
                    const SizedBox(height: 3),
                    Row(children: [
                      Expanded(child: Text(entry.host.isEmpty ? '—' : entry.host, maxLines: 1, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(fontSize: 12.5, color: AppColors.text3))),
                      if (entry.tags.isNotEmpty)
                        Expanded(
                          child: Text(entry.tags.take(2).join(', '), maxLines: 1, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(fontSize: 11, color: AppColors.success)),
                        ),
                    ]),
                    if (entry.districtName != null || entry.blockName != null)
                      Padding(
                        padding: const EdgeInsets.only(top:3),
                        child: Row(children: [
                          if (entry.districtName != null) Container(padding: const EdgeInsets.symmetric(horizontal:6, vertical:2), decoration: BoxDecoration(color: AppColors.accent1.withValues(alpha:0.12), borderRadius: BorderRadius.circular(6)), child: Text(entry.districtName!, style: GoogleFonts.inter(fontSize:10, color: AppColors.accent1))),
                          if (entry.blockName != null) Container(margin: const EdgeInsets.only(left:4), padding: const EdgeInsets.symmetric(horizontal:6, vertical:2), decoration: BoxDecoration(color: AppColors.accent2.withValues(alpha:0.12), borderRadius: BorderRadius.circular(6)), child: Text(entry.blockName!, style: GoogleFonts.inter(fontSize:10, color: AppColors.accent2))),
                        ]),
                      ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  entry.category,
                  style: GoogleFonts.inter(fontSize: 10.5, fontWeight: FontWeight.w700, color: accent, letterSpacing: 0.4),
                ),
              ),
              const SizedBox(width: 4),
              const Icon(Icons.chevron_right_rounded, color: AppColors.text3, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}

class _GroupCard extends StatelessWidget {
  final String domain;
  final String displayName;
  final int count;
  final String category;
  final List<String> exactHosts;
  final VoidCallback onTap;
  final VoidCallback onSetCategory;
  const _GroupCard({required this.domain, this.displayName = '', required this.count, required this.category, required this.exactHosts, required this.onTap, required this.onSetCategory});

  @override
  Widget build(BuildContext context) {
    final accent = categoryColor(category);
    final title = displayName.isNotEmpty ? displayName : displayNameForDomain(domain);
    return Material(
      color: AppColors.surface1,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: AppColors.border)),
          child: Row(
            children: [
              Container(width: 44, height: 44, decoration: BoxDecoration(color: accent.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12), border: Border.all(color: accent.withValues(alpha: 0.3))), alignment: Alignment.center, child: Text(title.isNotEmpty ? title[0].toUpperCase() : '?', style: GoogleFonts.inter(fontSize: 19, fontWeight: FontWeight.w800, color: accent))),
              const SizedBox(width: 13),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [Expanded(child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w600, color: AppColors.text1))), Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3), decoration: BoxDecoration(color: accent.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(999)), child: Text('$count', style: GoogleFonts.inter(fontSize: 12, fontWeight: FontWeight.w700, color: accent)))]),
                  const SizedBox(height: 3),
                  Text(domain, maxLines: 1, overflow: TextOverflow.ellipsis, style: GoogleFonts.inter(fontSize: 12, color: AppColors.text3)),
                  const SizedBox(height: 3),
                  Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3), decoration: BoxDecoration(color: accent.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(999)), child: Text(category, style: GoogleFonts.inter(fontSize: 10.5, fontWeight: FontWeight.w700, color: accent, letterSpacing: 0.4))),
                ]),
              ),
              IconButton(icon: const Icon(Icons.edit_outlined, size: 18, color: AppColors.text3), onPressed: onSetCategory, tooltip: 'Set category'),
              const Icon(Icons.chevron_right_rounded, color: AppColors.text3, size: 20),
            ],
          ),
        ),
      ),
    );
  }
}

class _SkeletonCard extends StatelessWidget {
  const _SkeletonCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 74,
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface1,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(color: AppColors.surface2, borderRadius: BorderRadius.circular(12)),
          ),
          const SizedBox(width: 13),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(width: 140, height: 13, decoration: BoxDecoration(color: AppColors.surface2, borderRadius: BorderRadius.circular(6))),
                const SizedBox(height: 8),
                Container(width: 90, height: 10, decoration: BoxDecoration(color: AppColors.surface2, borderRadius: BorderRadius.circular(6))),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
