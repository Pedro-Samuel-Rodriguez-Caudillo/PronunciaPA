import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/recorder_provider.dart';
import '../providers/api_provider.dart';
import '../providers/preferences_provider.dart';
import '../theme/app_theme.dart';

class RecorderWidget extends ConsumerWidget {
  final String? referenceText;
  const RecorderWidget({super.key, this.referenceText});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recorderState = ref.watch(recorderProvider);
    final recorderNotifier = ref.read(recorderProvider.notifier);
    final apiState = ref.watch(apiNotifierProvider);
    final apiNotifier = ref.read(apiNotifierProvider.notifier);
    final prefs = ref.watch(preferencesProvider);
    final isRecording = recorderState.isRecording;
    final isBusy = apiState.isLoading;
    final compareMode = prefs.comparisonMode;
    final theme = Theme.of(context);
    final glass = theme.extension<AppGlassTheme>();
    final iconColor = isRecording ? Colors.white : theme.colorScheme.onSurface;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTap: () async {
            if (isBusy) {
              return;
            }
            if (isRecording) {
              final path = await recorderNotifier.stopRecording();
              await apiNotifier.processAudio(
                path,
                referenceText: referenceText,
                lang: prefs.lang,
                evaluationLevel: prefs.mode.name,
                mode: compareMode,
                quick: false,
              );
              return;
            }
            await recorderNotifier.startRecording();
          },
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 240),
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              gradient: (!isRecording && !isBusy) ? AppTheme.primaryGradient : null,
              color: isRecording
                  ? AppTheme.error
                  : (isBusy ? theme.colorScheme.surfaceContainerHighest : null),
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: isRecording
                      ? AppTheme.error.withOpacity(0.35)
                      : AppTheme.primaryStart.withOpacity(0.35),
                  blurRadius: isRecording ? 28 : 24,
                  spreadRadius: isRecording ? 2 : 0,
                ),
              ],
            ),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 240),
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                color: isRecording
                    ? AppTheme.error
                    : (glass?.surfaceStrong ?? theme.colorScheme.surface),
                shape: BoxShape.circle,
                border: Border.all(
                  color: glass?.borderStrong ?? theme.colorScheme.outline,
                  width: 1.2,
                ),
              ),
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 200),
                child: isBusy
                    ? SizedBox(
                        width: 40,
                        height: 40,
                        child: CircularProgressIndicator(
                          strokeWidth: 3,
                          valueColor: AlwaysStoppedAnimation<Color>(iconColor),
                        ),
                      )
                    : Icon(
                        isRecording ? Icons.stop : Icons.mic,
                        key: ValueKey<bool>(isRecording),
                        color: iconColor,
                        size: 48,
                      ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Text(
          isBusy
              ? 'Processing...'
              : (isRecording ? 'Tap to stop' : 'Tap to record'),
          style: theme.textTheme.bodyLarge,
        ),
      ],
    );
  }
}
