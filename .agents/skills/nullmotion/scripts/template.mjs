#!/usr/bin/env node
// Copy a Null Motion template out as a standalone HyperFrames project you can edit and render.
//
//   node .agents/skills/nullmotion/scripts/template.mjs                  list the templates
//   node .agents/skills/nullmotion/scripts/template.mjs 07-chat-sim      copy to edit/nullmotion/07-chat-sim/
//   node .agents/skills/nullmotion/scripts/template.mjs 07-chat-sim DIR  copy to DIR
//   ... 07-chat-sim --bg '#0b0b0c'                                       and give it a solid background
//
// Inside the app, templates load GSAP and shared assets from one level up, and they name
// the Inter font without loading it. The copy gets its own GSAP, assets and the Inter
// variable font, so it renders the same anywhere. Most templates have a transparent
// background, which an MP4 cannot carry: HyperFrames renders it white, hiding light text.
// --bg sets a solid background for MP4 output. Upstream has no licence: keep copies out
// of git (the default destination, edit/, is gitignored).
import { copyFileSync, cpSync, existsSync, mkdirSync, readdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const skill = path.resolve(path.dirname(realpathSync(fileURLToPath(import.meta.url))), '..');
const root = path.resolve(skill, '../../..');
const app = path.join(root, 'vendor/nullmotion');
const pub = path.join(app, 'public');

const fail = message => { console.error(message); process.exit(1); };
if (!existsSync(pub)) fail('Null Motion is not fetched yet. Run scripts/fetch-nullmotion.sh first.');

const templates = readdirSync(pub).filter(name => /^\d\d-/.test(name) && existsSync(path.join(pub, name, 'index.html'))).sort();
const info = name => {
  const html = readFileSync(path.join(pub, name, 'index.html'), 'utf8');
  const tag = html.match(/<[^>]*data-composition-id[^>]*>/)?.[0] ?? '';
  const attr = key => tag.match(new RegExp(`${key}="([^"]+)"`))?.[1] ?? '?';
  return { size: `${attr('data-width')}x${attr('data-height')}`, duration: attr('data-duration'), title: html.match(/<title>([^<]*)<\/title>/)?.[1] ?? '' };
};

const positional = [];
let bg = null;
for (const args = process.argv.slice(2); args.length;) {
  const arg = args.shift();
  if (arg === '--bg') bg = args.shift() ?? '';
  else if (arg.startsWith('--bg=')) bg = arg.slice(5);
  else positional.push(arg);
}
if (bg !== null && !/^[#\w(),.%\s-]+$/.test(bg)) fail(`--bg needs a CSS colour such as '#0b0b0c' or 'black', not "${bg}".`);
const [id, out] = positional;
if (!id) {
  const catalog = JSON.parse(readFileSync(path.join(app, 'data/template-catalog.json'), 'utf8')).templates;
  for (const name of templates) {
    const { size, duration, title } = info(name);
    const about = catalog.find(template => template.id === name)?.description;
    console.log(`${name.padEnd(25)} ${size.padEnd(10)} ${`${duration}s`.padEnd(4)} ${title}${about ? ` — ${about}` : ''}`);
  }
  process.exit(0);
}
if (!templates.includes(id)) fail(`No template "${id}". Run with no arguments to list them.`);

const dest = path.resolve(out ?? path.join(root, 'edit/nullmotion', id));
if (existsSync(dest) && readdirSync(dest).length) fail(`${dest} already exists and is not empty.`);
cpSync(path.join(pub, id), dest, { recursive: true });

let html = readFileSync(path.join(dest, 'index.html'), 'utf8');
mkdirSync(path.join(dest, 'vendor'), { recursive: true });
copyFileSync(path.join(pub, '_vendor/gsap.min.js'), path.join(dest, 'vendor/gsap.min.js'));
html = html.replaceAll('../_vendor/gsap.min.js', 'vendor/gsap.min.js');
for (const ref of new Set(html.match(/\.\.\/assets\/[\w.-]+/g) ?? [])) {
  mkdirSync(path.join(dest, 'assets'), { recursive: true });
  copyFileSync(path.join(pub, ref.slice(3)), path.join(dest, ref.slice(3)));
}
html = html.replaceAll('../assets/', 'assets/');
mkdirSync(path.join(dest, 'fonts'), { recursive: true });
copyFileSync(path.join(skill, 'fonts/inter-latin-wght-normal.woff2'), path.join(dest, 'fonts/inter-latin-wght-normal.woff2'));
// After the template's own <style>, so an equal-specificity !important here wins.
const background = bg ? ` html, body, #root { background: ${bg} !important; }` : '';
html = html.replace('</head>', `<style>@font-face { font-family: "Inter"; src: url("fonts/inter-latin-wght-normal.woff2") format("woff2"); font-weight: 100 900; font-display: block; }${background}</style>\n</head>`);
writeFileSync(path.join(dest, 'index.html'), html);

const leftover = html.match(/(?:src|href)="\.\.\/[^"]*"/g);
if (leftover) console.warn(`Warning: still points outside the copy: ${leftover.join(', ')}`);
// check-ignore exits 1 for a path inside this repo that git would track (128 = outside the repo).
if (spawnSync('git', ['-C', root, 'check-ignore', '-q', dest]).status === 1) {
  console.warn('Warning: git tracks this folder. This repo is public and Null Motion has no licence: add it to .gitignore before committing.');
}

const { size, duration } = info(id);
const shown = path.relative(process.cwd(), dest) || '.';
const render = `cd ${shown} && npx --yes hyperframes@0.8.114 render .`;
console.log(bg
  ? `Copied ${id} (${size}, ${duration}s) to ${shown} on a ${bg} background.
Edit the text in index.html, then render:
  ${render} -q delivery -o ${id}.mp4`
  : `Copied ${id} (${size}, ${duration}s) to ${shown}, background transparent as designed.
Edit the text in index.html, then render an overlay that keeps the transparency (ProRes 4444):
  ${render} --format mov -o ${id}.mov
An MP4 cannot be transparent and renders on white, hiding light text: for an MP4, copy again with --bg '#0b0b0c'.`);
