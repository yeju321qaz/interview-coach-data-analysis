import fs from 'node:fs/promises';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {marked} from 'file:///C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/marked/lib/marked.esm.js';
const base=path.dirname(fileURLToPath(import.meta.url)),root=path.dirname(base);
const css=(await fs.readFile(path.join(base,'backup/index.html'),'utf8')).match(/<style>([\s\S]*?)<\/style>/)[1];
const body=marked.parse(await fs.readFile(path.join(base,'web_content.md'),'utf8'));
await fs.writeFile(path.join(root,'report/phase2.html'),`<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>사람 검수·STT 비교 준비</title><style>${css}\nmain table{width:100%;display:block;overflow:auto;border-collapse:collapse;font-size:13px}main td,main th{padding:8px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}main pre{overflow:auto}main h2{margin-top:40px}@media(max-width:760px){.wrap{display:block}nav.toc{position:static}}</style></head><body><div class="wrap"><nav class="toc"><div class="label">PHASE 2</div><p><a href="index.html#phase2">기존 분석으로</a></p><p><a href="review.html">검수 화면</a></p></nav><main>${body}</main></div></body></html>`);
console.log('Built phase2.html');
