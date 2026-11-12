import fs from 'node:fs/promises';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {marked} from 'file:///C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/marked/lib/marked.esm.js';
const base=path.dirname(fileURLToPath(import.meta.url)),root=path.dirname(base);
const before=await fs.readFile(path.join(base,'backup/index.html'),'utf8');
const stt=JSON.parse(await fs.readFile(path.join(base,'results/stt_summary.json'),'utf8'));
const pair=JSON.parse(await fs.readFile(path.join(base,'results/intent_baseline_summary.json'),'utf8'));
const md=await fs.readFile(path.join(base,'통합_결과보고서.md'),'utf8');
const impl=await fs.readFile(path.join(base,'구현_및_평가범위.md'),'utf8');
const guide=await fs.readFile(path.join(base,'Claude_Artifact_반영안내.md'),'utf8');
function render(s){return marked.parse(s).replaceAll('<table>','<div class="tbl"><table>').replaceAll('</table>','</table></div>').replaceAll('src="results/','src="../phase3_integrated_20261029/results/');}
const pct=n=>(100*n).toFixed(2)+'%';
const sttRows=stt.summary.map((r,i)=>`<tr><td>같은 tiny · beam ${i===0?1:5}</td><td>${r.files}</td><td>${pct(r.provisional_micro_CER)}</td><td>${pct(r.provisional_macro_CER)}</td><td>${r.decode_seconds.toFixed(2)}초</td><td>${r.overall_real_time_factor.toFixed(4)}</td></tr>`).join('');
const additions=`
<section id="integrated"><div class="sec-tag">LATEST · 2026-10-29 · 통합 현황</div><h2>중간발표: 실제 수행과 계획을 구분하기</h2>
<p>기존 분석·검증·수집 계획을 보존하고 무료 로컬 모델 실행 근거를 추가했습니다. <b>48개 사람 검수는 보류</b>하며, 검수 완료와 신규 녹음은 모두 0건입니다. 아래 옛 단계 기록의 ‘STT 미실행’은 당시 상태이며 최신 로컬 실행은 이 섹션을 기준으로 봅니다.</p>
<div class="tbl"><table><tr><th>항목</th><th>현재 상태</th></tr><tr><td>기존 분석·재현</td><td>76,105건 분석 / 음성 1,198쌍 / 네 분석 재실행 완료</td></tr><tr><td>품질·검수</td><td>자동 통과 후보 75,983건 / 사람 검수 보류</td></tr><tr><td>이번 실제 실행</td><td>tiny 12파일 × 2설정 / 질문 그룹 분리 기준선</td></tr><tr><td>앞으로 수집·평가</td><td>80건 녹음·시간 정답·의미 질문군·실시간 이탈 성능 미확보</td></tr></table></div>
<p><a href="#stt-local">실제 STT 실행</a> · <a href="#intent-prototype">이탈 감지 구현 검토</a> · <a href="#artifact-sync">Claude Artifact 반영</a></p>
<details><summary>통합 보고서 전문: 완료/부족/모델 결과/수집 계획</summary>${render(md)}</details></section>
<section id="stt-local"><div class="sec-tag">EXECUTED · LOCAL STT</div><h2>무료 로컬 STT 시험 — 같은 tiny 모델의 두 설정</h2>
<p>6개 하위셋의 12개 WAV·약 14.47분을 CPU 4스레드 INT8로 처리했습니다. 음성 외부 전송과 유료 API 호출은 0건입니다. 모델 자산은 약 78.2MB이며 런타임과 함께 별도 폴더에 저장했습니다.</p>
<div class="caution"><b>임시 참고치</b> · CER는 사람이 검수하지 않은 AI Hub 전사 기준입니다. 아래 값은 최종 한국어 정확도·서로 다른 모델의 우열·실시간 지연을 뜻하지 않습니다.</div>
<div class="tbl"><table><tr><th>디코딩 설정</th><th>파일</th><th>임시 micro CER</th><th>임시 macro CER</th><th>디코딩 합</th><th>RTF</th></tr>${sttRows}</table></div>
<figure class="chart"><figcaption>실제 실행 결과와 파일별 편차</figcaption><img src="../phase3_integrated_20261029/results/stt_comparison.png" style="display:block;width:100%;height:auto" alt="같은 tiny 모델에서 beam1 임시 CER 21.12%, beam5 14.30%, 미검수 AI Hub 전사 기준"></figure>
<p>‘어/음’ 표기 후보 34개는 두 설정에서 문자 정렬상 보존 0개였습니다. 이는 실제 간투사 정답 Recall이 아닌 자동 후보 점검치입니다. 클라우드 Google Chirp 3와 Azure Speech는 후보·실행 코드만 준비했고 여전히 미실행입니다.</p></section>
<section id="intent-prototype"><div class="sec-tag">EXECUTED BASELINE / PLANNED SEMANTICS</div><h2>질문 이탈: 어휘 기준선과 실제 목표의 차이</h2>
<p>Training 답변 2,000개로 어휘와 작은 분류기를 학습하고, 고유 질문이 겹치지 않는 개발 400개·테스트 400개를 분리했습니다. 테스트 800쌍의 <b>질문 쌍 구분 AUC ${pair.test_pair_auc.toFixed(4)}</b>이며 코사인 단독은 ${pair.test_cosine_auc.toFixed(4)}입니다. 추가 분류기의 개선 근거는 이번 AUC에서 확인하지 못했습니다.</p>
<div class="caution"><b>실제 이탈 정확도 아님</b> · 원래 질문과 같은 유형의 다른 질문을 구분한 자동 과제입니다. 이탈·복귀·알림 정답, 화자 독립성, 실시간 지연은 검증하지 않았습니다.</div>
<div class="apply"><div class="t">구현 흐름</div><p>사용자 음성 → 온라인 VAD·STT → 안정된 전사·간투사 보존 → 질문 핵심 항목+누적 문맥 → 관련/이탈 후보/근거 부족 → 연속 구간·cooldown → 실시간 알림 / 종료 후 STAR·유창성 리포트</p></div>
<p>final 여부·최소 발화량·연속 N구간·cooldown 상태기계와 tiny 전사의 오프라인 재생 코드는 실행했습니다. 의미 모델·실시간 전송·알림 성능은 앞으로 수행할 계획입니다. 기존 80건 녹음 계획은 유지합니다.</p>
<details><summary>데이터 매핑·구현 상세·남은 평가</summary>${render(impl)}</details></section>
<section id="artifact-sync"><div class="sec-tag">LOCAL HTML / CLAUDE ARTIFACT</div><h2>현재 HTML은 원격 Artifact와 자동 동기화하지 않습니다</h2>
<p>지금 수정한 대상은 PC의 독립 HTML입니다. 원격 Artifact 링크/원본이 없어 그 버전은 확인하지 못했으며 Claude에 업로드·수정·게시하지 않았습니다.</p>
<p><a href="integrated_standalone.html">통합 단일 HTML 열기 / 전달용</a> · <a href="../phase3_integrated_20261029/통합_결과보고서.md">통합 보고서 원문</a> · <a href="../phase3_integrated_20261029/README.md">재현 명령·파일 안내</a></p>
<details><summary>기존 Claude Artifact에 반영하는 방법·요청문</summary>${render(guide)}</details></section>
`;
let page=before.replace('</header>','</header>\n'+additions);
page=page.replace('</style>','</style><style>#integrated,#stt-local,#intent-prototype,#artifact-sync{overflow-wrap:anywhere;max-width:100%;overflow-x:hidden}#integrated pre,#intent-prototype pre,#artifact-sync pre{overflow:auto}section[id^="appendix-"]{overflow-wrap:anywhere;overflow-x:auto;max-width:100%}</style>');
page=page.replace('<li><a href="#summary">핵심 결론</a></li>','<li><a href="#integrated">최신 통합 현황</a></li><li><a href="#stt-local">실제 무료 STT 시험</a></li><li><a href="#intent-prototype">이탈 구현·평가 범위</a></li><li><a href="#artifact-sync">Claude Artifact 반영</a></li>\n<li><a href="#summary">기존 분석 핵심 결론</a></li>');
page=page.replace('<section id="phase2">','<section id="phase2"><p class="small">이전 2단계 기록입니다. 최신 로컬 STT 실행은 상단 통합 현황을 참고하세요. 사람 검수는 현재 보류합니다.</p>');
await fs.writeFile(path.join(root,'report/index.html'),page);
// Standalone export embeds reports and images, without interview transcript files or audio.
let standalone=page.replace(/<link[^>]+>/g,'');
let appendix='';
for(const [file,id,label] of [['verification.html','appendix-verification','1단계 상세 보고서'],['phase2.html','appendix-phase2','2단계 상세 보고서']]){
 const old=await fs.readFile(path.join(root,'report',file),'utf8');const body=old.match(/<main>([\s\S]*?)<\/main>/)?.[1]||'';
 appendix+=`<section id="${id}"><div class="sec-tag">보존된 이전 단계 기록</div><h2>${label}</h2>${body}</section>`;
 standalone=standalone.replaceAll(`href="${file}"`,`href="#${id}"`);
}
standalone=standalone.replace('  </main>',appendix+'  </main>');
standalone=standalone.replace(/<img([^>]*?)src="([^"]+)"([^>]*?)>/g,(whole,pre,src,post)=>{
 if(src.startsWith('data:'))return whole;
 const f=path.resolve(root,'report',src);return fsSyncExists(f)?`<img${pre}src="data:image/png;base64,${readSync(f)}"${post}>`:whole;
});
function fsSyncExists(p){try{fsSync.accessSync(p);return true;}catch{return false;}}
function readSync(p){return fsSync.readFileSync(p).toString('base64');}
import fsSync from 'node:fs';
standalone=standalone.replace(/href="(?!https?:|#|data:)([^"]+)"/g,(full,rel)=>rel==='integrated_standalone.html'?'href="#integrated"':rel==='review.html'?'href="#phase2"':'href="#artifact-sync"');
await fs.writeFile(path.join(root,'report/integrated_standalone.html'),standalone);
console.log('Integrated into index.html; standalone export created');
// Preserve presentation interpretation on every regeneration, without model runs.
const {spawnSync}=await import('node:child_process');
const edit=spawnSync('C:/Users/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',[path.join(root,'refine_report_for_presentation.py')],{cwd:root,encoding:'utf8'});
if(edit.status!==0)throw new Error(edit.stderr||'Presentation editorial pass failed');
console.log(edit.stdout.trim());
