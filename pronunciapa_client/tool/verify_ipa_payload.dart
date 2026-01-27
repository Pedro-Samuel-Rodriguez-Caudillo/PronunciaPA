import 'dart:io';
import '../lib/domain/entities/ipa_cli.dart';

void main(List<String> args) {
  final path = args.isNotEmpty ? args.first : '../outputs/ipa_practice_es_s.json';
  final file = File(path);
  if (!file.existsSync()) {
    stderr.writeln('File not found: $path');
    exit(1);
  }
  final raw = file.readAsStringSync();
  final payload = parseIpaCliPayload(raw);
  if (payload == null) {
    stderr.writeln('Invalid IPA payload');
    exit(1);
  }
  if (payload is IpaPracticeSetPayload) {
    stdout.writeln('kind=${payload.kind} items=${payload.items.length}');
    if (payload.items.isNotEmpty) {
      stdout.writeln('first=${payload.items.first.text}');
    }
  } else if (payload is IpaExplorePayload) {
    stdout.writeln('kind=${payload.kind} examples=${payload.examples.length}');
    if (payload.examples.isNotEmpty) {
      stdout.writeln('first=${payload.examples.first.text}');
    }
  } else {
    stdout.writeln('kind=${payload.kind}');
  }
}
