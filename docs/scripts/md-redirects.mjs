// Writes an nginx map that sends old Markdown URLs to the live pages.
// Search engines still request URLs such as /how-to/how-to/vault.md and
// /explanation/tutorials/argocd.md. Each page gets an exact rule first and
// then a rule that matches only its file name in any folder.
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const dist = process.argv[2] ?? 'dist';
const out = process.argv[3] ?? 'nginx/md-redirects.conf';
const sectionOrder = ['tutorials', 'how-to', 'explanation', 'reference'];

const pages = [];
const walk = (dir, parts) => {
	for (const name of readdirSync(dir)) {
		const full = join(dir, name);
		if (!statSync(full).isDirectory() || name.startsWith('_')) continue;
		if (readdirSync(full).includes('index.html')) {
			const html = readFileSync(join(full, 'index.html'), 'utf8');
			const refresh = html.match(/http-equiv="refresh" content="\d+;url=([^"]+)"/);
			pages.push({ parts: [...parts, name], target: refresh ? refresh[1] : `/${[...parts, name].join('/')}/` });
		}
		walk(full, [...parts, name]);
	}
};
walk(dist, []);

const rank = ({ parts }) => {
	const i = sectionOrder.indexOf(parts[0]);
	return i === -1 ? sectionOrder.length : i;
};
pages.sort((a, b) => rank(a) - rank(b) || a.parts.join('/').localeCompare(b.parts.join('/')));

const esc = (s) => s.replace(/[.+-]/g, '\\$&');
const lines = ['map $uri $md_redirect {', '\tdefault "";', '\t~^/index\\.md$ /;'];
for (const { parts, target } of pages) lines.push(`\t~^/${parts.map(esc).join('/')}(/index)?\\.md$ ${target};`);
const seen = new Set();
for (const { parts, target } of pages) {
	const slug = parts[parts.length - 1];
	if (seen.has(slug)) continue;
	seen.add(slug);
	lines.push(`\t~^/(.+/)?${esc(slug)}(/index)?\\.md$ ${target};`);
}
lines.push('}', '');
writeFileSync(out, lines.join('\n'));
console.log(`md-redirects: ${pages.length} pages -> ${out}`);
