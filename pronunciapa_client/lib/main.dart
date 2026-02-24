import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'presentation/pages/home_page.dart';
import 'presentation/theme/app_theme.dart';
import 'core/debug/debug.dart';

void main() {
  // IMPORTANT: ensureInitialized() must be called in the SAME zone as runApp().
  // Wrapping both inside runZonedGuarded prevents the "Zone mismatch" warning
  // that occurs when bindings are initialized in the root zone but runApp is
  // called from a different (guarded) zone.
  runZonedGuarded(
    () {
      WidgetsFlutterBinding.ensureInitialized();

      // Catch all Flutter framework errors.
      FlutterError.onError = (FlutterErrorDetails details) {
        AppLogger.e(
          'Flutter',
          details.exceptionAsString(),
          error: details.exception,
          stackTrace: details.stack,
        );
        // Still call default handler so the red-screen shows in debug mode.
        FlutterError.presentError(details);
      };

      // Catch uncaught errors on the platform thread (Dart isolate root zone).
      PlatformDispatcher.instance.onError = (error, stack) {
        AppLogger.e('PlatformDispatcher', error.toString(),
            error: error, stackTrace: stack);
        return false; // let the error propagate normally
      };

      // ignore: prefer_const_constructors
      runApp(ProviderScope(
        observers: kDebugMode ? const [DebugProviderObserver()] : const [],
        child: const MyApp(),
      ));
    },
    (error, stack) {
      AppLogger.e('Zone', error.toString(), error: error, stackTrace: stack);
    },
  );
}

/// Provider para el modo del tema
final themeModeProvider = StateProvider<ThemeMode>((ref) => ThemeMode.dark);

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeModeProvider);

    return MaterialApp(
      title: 'PronunciaPA',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: themeMode,
      // DebugOverlay injects the floating debug FAB in debug builds only.
      home: const DebugOverlay(child: HomePage()),
    );
  }
}
