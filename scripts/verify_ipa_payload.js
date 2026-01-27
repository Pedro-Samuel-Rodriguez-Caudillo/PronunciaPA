const fs = require('node:fs');

const path = process.argv[2] || 'outputs/ipa_practice_es_s.json';
const raw = fs.readFileSync(path, 'utf8');
const payload = JSON.parse(raw);

const kind = payload?.kind;
if (!kind) {
  throw new Error('IPA payload missing kind');
}

const items = Array.isArray(payload.items) ? payload.items : [];
const examples = Array.isArray(payload.examples) ? payload.examples : [];
const total = items.length || examples.length;

console.log(`kind=${kind} total=${total}`);
if (payload.sound?.ipa) {
  console.log(`sound=${payload.sound.ipa}`);
}
if (items[0]?.text) {
  console.log(`first=${items[0].text}`);
} else if (examples[0]?.text) {
  console.log(`first=${examples[0].text}`);
}
