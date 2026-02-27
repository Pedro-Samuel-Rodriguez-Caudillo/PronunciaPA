import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'presentation/pages/home_page.dart';
import 'presentation/pages/ipa_learn_page.dart';
import 'presentation/pages/ipa_practice_page.dart';
import 'presentation/pages/progress_roadmap_page.dart';
import 'presentation/pages/settings_page.dart';
import 'presentation/providers/preferences_provider.dart';
import 'presentation/theme/app_theme.dart';
import 'core/debug/debug.dart';

void main() {
  // Error handlers that don't require the binding can be set before runZonedGuarded.
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

  // Catch all remaining async errors in the Flutter zone.
  // IMPORTANT: ensureInitialized() must be called inside runZonedGuarded so
  // that the binding and runApp share the same zone — prevents the zone-mismatch
  // warning ("Flutter bindings were initialized in a different zone").
  runZonedGuarded(
    () {
      WidgetsFlutterBinding.ensureInitialized();
      runApp(
        // ignore: prefer_const_constructors
        ProviderScope(
          observers: kDebugMode ? const [DebugProviderObserver()] : const [],
          child: const MyApp(),
        ),
      );
    },
    (error, stack) {
      AppLogger.e('Zone', error.toString(), error: error, stackTrace: stack);
    },
  );
}

class MyApp extends ConsumerWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefs = ref.watch(preferencesProvider);
    final themeMode = prefs.darkMode ? ThemeMode.dark : ThemeMode.light;

    return MaterialApp(
      title: 'PronunciaPA',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: themeMode,
      home: const DebugOverlay(child: MainShell()),
    );
  }
}

/// Main application shell with Material 3 NavigationBar.
/// Each tab is kept alive via IndexedStack so state is preserved.
class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _selectedIndex = 0;

  static const _pages = <Widget>[
    HomePage(),
    IpaLearnPage(),
    IpaPracticePage(),
    ProgressRoadmapPage(),
    SettingsPage(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(
        index: _selectedIndex,
        children: _pages,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) => setState(() => _selectedIndex = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.mic_none),
            selectedIcon: Icon(Icons.mic),
            label: 'Practica',
          ),
          NavigationDestination(
            icon: Icon(Icons.school_outlined),
            selectedIcon: Icon(Icons.school),
            label: 'Aprende',
          ),
          NavigationDestination(
            icon: Icon(Icons.psychology_outlined),
            selectedIcon: Icon(Icons.psychology),
            label: 'Ejercicios',
          ),
          NavigationDestination(
            icon: Icon(Icons.show_chart),
            selectedIcon: Icon(Icons.show_chart),
            label: 'Progreso',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Config',
          ),
        ],
      ),
    );
  }
}
