import 'dart:io';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../presentation/providers/recorder_provider.dart';
import 'debug_log_store.dart';

/// Wraps the application widget tree and, in debug builds, injects a
/// floating debug button in the bottom-right corner.
///
/// When tapped, it opens a draggable bottom sheet with two tabs:
///   • HTTP — all captured network calls
///   • Events — provider state changes, audio reports, etc.
///
/// In release builds this widget is a transparent passthrough.
class DebugOverlay extends StatelessWidget {
  final Widget child;

  const DebugOverlay({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode) return child;
    return Stack(
      fit: StackFit.expand,
      children: [
        child,
        // Positioned must be a direct child of Stack — not inside a StatelessWidget.
        Positioned(
          bottom: 80,
          right: 12,
          child: _DebugFab(onTap: () => _openDebugPanel(context)),
        ),
      ],
    );
  }

  static void _openDebugPanel(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => const _DebugPanel(),
    );
  }
}

// ── Floating action button ────────────────────────────────────────────────────

class _DebugFab extends StatelessWidget {
  final VoidCallback onTap;
  const _DebugFab({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            color: Colors.black.withOpacity(0.75),
            shape: BoxShape.circle,
            border: Border.all(color: Colors.greenAccent, width: 1.5),
          ),
          child: const Icon(Icons.bug_report, color: Colors.greenAccent, size: 24),
        ),
      ),
    );
  }
}

// ── Bottom-sheet panel ────────────────────────────────────────────────────────

class _DebugPanel extends StatelessWidget {
  const _DebugPanel();

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.65,
      minChildSize: 0.3,
      maxChildSize: 0.95,
      expand: false,
      builder: (_, controller) => ClipRRect(
        borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
        child: Scaffold(
          backgroundColor: const Color(0xFF121212),
          appBar: AppBar(
            backgroundColor: const Color(0xFF1E1E1E),
            title: const Text(
              'Debug Inspector',
              style: TextStyle(
                color: Colors.greenAccent,
                fontSize: 14,
                fontFamily: 'monospace',
              ),
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.delete_outline, color: Colors.grey),
                tooltip: 'Clear logs',
                onPressed: () {
                  DebugLogStore.instance.clear();
                },
              ),
              IconButton(
                icon: const Icon(Icons.close, color: Colors.grey),
                onPressed: () => Navigator.of(context).pop(),
              ),
            ],
          ),
          body: const DefaultTabController(
            length: 3,
            child: Column(
              children: [
                TabBar(
                  labelColor: Colors.greenAccent,
                  unselectedLabelColor: Colors.grey,
                  indicatorColor: Colors.greenAccent,
                  tabs: [
                    Tab(text: 'HTTP'),
                    Tab(text: 'Events'),
                    Tab(icon: Icon(Icons.headphones, size: 16), text: 'Audio'),
                  ],
                ),
                Expanded(
                  child: TabBarView(
                    children: [
                      _HttpLogList(),
                      _AppLogList(),
                      _AudioDebugTab(),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Audio tab ────────────────────────────────────────────────────────────────

class _AudioDebugTab extends ConsumerStatefulWidget {
  const _AudioDebugTab();

  @override
  ConsumerState<_AudioDebugTab> createState() => _AudioDebugTabState();
}

class _AudioDebugTabState extends ConsumerState<_AudioDebugTab> {
  late final AudioPlayer _player;
  PlayerState _playerState = PlayerState.stopped;

  @override
  void initState() {
    super.initState();
    _player = AudioPlayer();
    _player.onPlayerStateChanged.listen((s) {
      if (mounted) setState(() => _playerState = s);
    });
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  Future<void> _togglePlay(String path) async {
    if (_playerState == PlayerState.playing) {
      await _player.stop();
    } else {
      await _player.play(DeviceFileSource(path));
    }
  }

  @override
  Widget build(BuildContext context) {
    final lastPath = ref.watch(recorderProvider).lastPath;

    if (lastPath == null || !File(lastPath).existsSync()) {
      return const Center(
        child: Text(
          'No audio recorded yet.\nRecord something to enable playback.',
          textAlign: TextAlign.center,
          style: TextStyle(
            color: Colors.grey,
            fontSize: 12,
            fontFamily: 'monospace',
          ),
        ),
      );
    }

    final isPlaying = _playerState == PlayerState.playing;
    final isDone = _playerState == PlayerState.completed;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'LAST ASR AUDIO',
            style: TextStyle(
              color: Colors.greenAccent,
              fontSize: 10,
              fontFamily: 'monospace',
              letterSpacing: 1.5,
            ),
          ),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.05),
              borderRadius: BorderRadius.circular(4),
            ),
            child: SelectableText(
              lastPath,
              style: const TextStyle(
                color: Colors.white54,
                fontSize: 10,
                fontFamily: 'monospace',
              ),
            ),
          ),
          const SizedBox(height: 20),
          Center(
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: isPlaying
                    ? Colors.redAccent.withOpacity(0.15)
                    : Colors.greenAccent.withOpacity(0.12),
                foregroundColor:
                    isPlaying ? Colors.redAccent : Colors.greenAccent,
                side: BorderSide(
                  color: isPlaying ? Colors.redAccent : Colors.greenAccent,
                  width: 1.2,
                ),
                padding: const EdgeInsets.symmetric(
                    horizontal: 28, vertical: 12),
              ),
              icon: Icon(
                isPlaying ? Icons.stop_rounded : Icons.play_arrow_rounded,
                size: 22,
              ),
              label: Text(
                isPlaying ? 'Stop' : 'Play ASR audio',
                style: const TextStyle(
                    fontFamily: 'monospace', fontSize: 13),
              ),
              onPressed: () => _togglePlay(lastPath),
            ),
          ),
          if (isDone)
            const Padding(
              padding: EdgeInsets.only(top: 12),
              child: Center(
                child: Text(
                  '✓ playback complete',
                  style: TextStyle(
                    color: Colors.greenAccent,
                    fontSize: 11,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

// ── HTTP tab ──────────────────────────────────────────────────────────────────

class _HttpLogList extends StatefulWidget {
  const _HttpLogList();

  @override
  State<_HttpLogList> createState() => _HttpLogListState();
}

class _HttpLogListState extends State<_HttpLogList>
    with AutomaticKeepAliveClientMixin {
  List<HttpLogEntry> _entries = [];
  final _scrollController = ScrollController();

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _entries = DebugLogStore.instance.httpEntries;
    DebugLogStore.instance.httpStream.listen((e) {
      if (mounted) setState(() => _entries = e);
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_entries.isEmpty) {
      return const Center(
        child: Text('No HTTP calls captured yet.',
            style: TextStyle(color: Colors.grey)),
      );
    }
    return ListView.separated(
      controller: _scrollController,
      padding: const EdgeInsets.all(8),
      itemCount: _entries.length,
      separatorBuilder: (_, __) =>
          const Divider(color: Colors.white12, height: 1),
      itemBuilder: (_, i) => _HttpTile(entry: _entries[i]),
    );
  }
}

class _HttpTile extends StatelessWidget {
  final HttpLogEntry entry;
  const _HttpTile({required this.entry});

  @override
  Widget build(BuildContext context) {
    final statusColor = entry.isSuccess
        ? Colors.greenAccent
        : entry.isFailure
            ? Colors.redAccent
            : Colors.orangeAccent;
    return ExpansionTile(
      tilePadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 0),
      childrenPadding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
      leading: _Badge(
        label: entry.statusCode?.toString() ?? '✗',
        color: statusColor,
      ),
      title: Text(
        '${entry.method}  ${_shortUrl(entry.url)}',
        style: const TextStyle(
            color: Colors.white70, fontSize: 12, fontFamily: 'monospace'),
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        '${entry.durationMs}ms  •  ${_timeLabel(entry.timestamp)}',
        style: const TextStyle(color: Colors.grey, fontSize: 10),
      ),
      children: [
        if (entry.requestInfo != null)
          _MonoText('REQUEST\n${entry.requestInfo}'),
        if (entry.responseBody != null)
          _MonoText('RESPONSE\n${entry.responseBody}'),
        if (entry.error != null)
          _MonoText('ERROR\n${entry.error}', color: Colors.redAccent),
      ],
    );
  }

  static String _shortUrl(String url) {
    final uri = Uri.tryParse(url);
    if (uri == null) return url;
    return uri.path + (uri.query.isNotEmpty ? '?${uri.query}' : '');
  }

  static String _timeLabel(DateTime dt) =>
      '${dt.hour.toString().padLeft(2, '0')}:'
      '${dt.minute.toString().padLeft(2, '0')}:'
      '${dt.second.toString().padLeft(2, '0')}';
}

// ── Events tab ────────────────────────────────────────────────────────────────

class _AppLogList extends StatefulWidget {
  const _AppLogList();

  @override
  State<_AppLogList> createState() => _AppLogListState();
}

class _AppLogListState extends State<_AppLogList>
    with AutomaticKeepAliveClientMixin {
  List<AppLogEntry> _entries = [];
  final _scrollController = ScrollController();

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _entries = DebugLogStore.instance.appEntries;
    DebugLogStore.instance.appStream.listen((e) {
      if (mounted) setState(() => _entries = e);
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_entries.isEmpty) {
      return const Center(
        child: Text('No events captured yet.',
            style: TextStyle(color: Colors.grey)),
      );
    }
    return ListView.separated(
      controller: _scrollController,
      padding: const EdgeInsets.all(8),
      itemCount: _entries.length,
      separatorBuilder: (_, __) =>
          const Divider(color: Colors.white12, height: 1),
      itemBuilder: (_, i) => _AppLogTile(entry: _entries[i]),
    );
  }
}

class _AppLogTile extends StatelessWidget {
  final AppLogEntry entry;
  const _AppLogTile({required this.entry});

  static Color _levelColor(AppLogLevel l) => switch (l) {
        AppLogLevel.debug => Colors.grey,
        AppLogLevel.info => Colors.lightBlueAccent,
        AppLogLevel.warning => Colors.orangeAccent,
        AppLogLevel.error => Colors.redAccent,
      };

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _Badge(
            label: entry.tag.substring(0, entry.tag.length.clamp(0, 4)),
            color: _levelColor(entry.level),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              entry.message,
              style: TextStyle(
                color: _levelColor(entry.level),
                fontSize: 11,
                fontFamily: 'monospace',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ── Shared helpers ────────────────────────────────────────────────────────────

class _Badge extends StatelessWidget {
  final String label;
  final Color color;
  const _Badge({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        border: Border.all(color: color, width: 1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: TextStyle(
            color: color, fontSize: 10, fontFamily: 'monospace'),
      ),
    );
  }
}

class _MonoText extends StatelessWidget {
  final String text;
  final Color color;
  const _MonoText(this.text, {this.color = Colors.white54});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 4),
      padding: const EdgeInsets.all(6),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.05),
        borderRadius: BorderRadius.circular(4),
      ),
      child: SelectableText(
        text,
        style: TextStyle(
            color: color, fontSize: 10, fontFamily: 'monospace'),
      ),
    );
  }
}
