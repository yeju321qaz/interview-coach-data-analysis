'use strict';
// Local-only review: no network calls, no embedded interview source data.
let dataset=null, current=0, results={}, storageWarning='';
const $=id=>document.getElementById(id);
const fields=['human_star_applicable','question_answer_match','transcript_audio_match','human_quality_status','evidence_notes','audio_listened'];
function key(){return 'interview_review48_v1:'+($('reviewer').value.trim()||'anonymous');}
function persist(){try{localStorage.setItem(key(),JSON.stringify(results));}catch(e){storageWarning='자동 저장 불가: CSV로 내보내세요.';}}
function restore(){try{results=JSON.parse(localStorage.getItem(key())||'{}');}catch(e){results={};}render();}
function selectedTypes(){return [...document.querySelectorAll('input[name="human_type"]:checked')].map(e=>e.value);}
function capture(){if(!dataset)return;const row=dataset.rows[current];const old=results[row.id]||{};
 const state={...old,review_set_id:dataset.set_id,id:row.id,reviewer_id:$('reviewer').value.trim(),human_question_type:selectedTypes().join('|'),status:'draft',updated_at:new Date().toISOString()};
 fields.forEach(f=>state[f]=$(f).type==='checkbox'?$(f).checked:$(f).value);results[row.id]=state;persist();summary();}
function valid(r,row){if(!r||!r.reviewer_id||!r.human_question_type||!r.human_star_applicable||!r.question_answer_match||!r.transcript_audio_match||!r.human_quality_status||!r.evidence_notes.trim())return false;
 if(row.audio_pair_available==='True')return r.transcript_audio_match!=='not_available'&&(r.audio_listened===true||r.audio_listened==='true');
 return r.transcript_audio_match==='not_available';}
function summary(){if(!dataset)return;const complete=dataset.rows.filter(row=>results[row.id]?.status==='reviewed_single'&&valid(results[row.id],row));
 let agree=0;complete.forEach(row=>{const auto=row.rule_question_types.split('|').sort().join('|');const gold=results[row.id].human_question_type.split('|').sort().join('|');agree+=auto===gold;});
 $('progress').textContent=`${current+1} / ${dataset.rows.length} · 단일 검수 완료 ${complete.length} · 유형 완전 일치 ${agree}/${complete.length}${complete.length?' ('+(100*agree/complete.length).toFixed(1)+'%)':''} · 합의 정답 아님 ${storageWarning}`;
 $('row_status').textContent=results[dataset.rows[current].id]?.status==='reviewed_single'&&valid(results[dataset.rows[current].id],dataset.rows[current])?'단일 검수 완료':'미검수 또는 작성 중';}
function render(){if(!dataset)return;$('workspace').hidden=false;const row=dataset.rows[current],r=results[row.id]||{};
 $('sample_id').textContent=row.id; $('question').textContent=row.q_text;$('answer').textContent=row.a_text;
 $('stratum').textContent='음성: '+(row.audio_pair_available==='True'?'있음':'없음');
 $('automatic').textContent='선정 층: '+row.selection_stratum+' / 자동 유형: '+row.rule_question_types+' / STAR: '+row.star_suitability_candidate+' / 품질 플래그: '+(row.quality_flags||'없음');
 $('automatic_details').open=false;
 const types=$('types');types.replaceChildren();dataset.types.forEach(t=>{const l=document.createElement('label'),i=document.createElement('input');i.type='checkbox';i.name='human_type';i.value=t;i.checked=(r.human_question_type||'').split('|').includes(t);i.addEventListener('change',capture);l.append(i,document.createTextNode(' '+t));types.append(l);});
 fields.forEach(f=>{if($(f).type==='checkbox')$(f).checked=r[f]===true||r[f]==='true';else $(f).value=r[f]||'';});
 $('audio_listened').disabled=row.audio_pair_available!=='True';
 const raw=row.answer_audio_path.replaceAll('\\','/');const safe=/^data\/[\w\u3131-\uD79D.\-/]+\.wav$/u.test(raw)&&!raw.includes('..')&&!raw.includes('|');
 const audio=$('audio');audio.pause();if(safe){audio.src='../'+raw;audio.hidden=false;$('audio_note').textContent='로컬 WAV를 재생하고 전사와 비교하세요.';}else{audio.removeAttribute('src');audio.hidden=true;$('audio_note').textContent='로컬 음성 없음: 음성 일치 항목을 ‘음성 없음’으로 선택하세요.';}
 $('message').textContent='';summary();}
$('dataset_file').addEventListener('change',async e=>{try{const d=JSON.parse(await e.target.files[0].text());if(d.set_id!=='review48_v1'||d.rows.length!==48||new Set(d.rows.map(r=>r.id)).size!==48)throw Error('review_subset48.json 형식이 아닙니다.');dataset=d;current=0;restore();}catch(err){$('message').textContent=err.message;}});
$('reviewer').addEventListener('change',()=>{if(dataset)restore();});
fields.forEach(f=>$(f).addEventListener('input',capture));
$('save_review').addEventListener('click',()=>{capture();const row=dataset.rows[current],r=results[row.id];if(!valid(r,row)){$('message').textContent='검수자 ID, 유형, STAR, 관련성, 전사 일치, 품질 판정과 근거를 모두 입력하세요. 음성이 있으면 청취 확인도 필요합니다.';return;}r.status='reviewed_single';r.reviewed_at=new Date().toISOString();persist();summary();$('message').textContent='단일 검수로 저장했습니다. 두 검수자 합의·최종 정답은 별도 확인이 필요합니다.';});
function move(n){if(!dataset)return;current=(current+n+dataset.rows.length)%dataset.rows.length;render();}
$('prev').onclick=()=>move(-1);$('next').onclick=()=>move(1);
function csvQuote(v){let s=String(v??'');if(/^[=+@-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';}
$('export').onclick=()=>{if(!dataset){$('message').textContent='검수 세트 JSON을 먼저 불러오세요.';return;}
 const cols=['review_set_id','id','selection_stratum','reviewer_id','human_review_status','rule_question_types','human_question_type','type_exact_agreement','star_suitability_candidate','human_star_applicable','question_answer_match','transcript_audio_match','audio_listened','human_quality_status','evidence_notes','updated_at','reviewed_at'];
 const rows=dataset.rows.map(row=>{const r=results[row.id]||{};const complete=r.status==='reviewed_single'&&valid(r,row);return {...row,...r,review_set_id:dataset.set_id,reviewer_id:r.reviewer_id||$('reviewer').value.trim(),human_review_status:complete?'검수완료(단일검수)':r.status?'작성중':'미검수',type_exact_agreement:complete?row.rule_question_types.split('|').sort().join('|')===r.human_question_type.split('|').sort().join('|'):''};});
 const csv='\uFEFF'+[cols,...rows.map(r=>cols.map(c=>r[c]??''))].map(a=>a.map(csvQuote).join(',')).join('\r\n');
 const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));link.download='review48_'+($('reviewer').value.trim().replace(/[^a-zA-Z0-9_-]/g,'_')||'draft')+'.csv';document.body.append(link);link.click();setTimeout(()=>{URL.revokeObjectURL(link.href);link.remove();},60000);};
function parseCSV(s){s=s.replace(/^\uFEFF/,'');let rows=[],row=[],field='',quote=false;for(let i=0;i<s.length;i++){const c=s[i];if(c==='"'){if(quote&&s[i+1]==='"'){field+='"';i++;}else quote=!quote;}else if(c===','&&!quote){row.push(field);field='';}else if((c==='\n'||c==='\r')&&!quote){if(c==='\r'&&s[i+1]==='\n')i++;row.push(field);if(row.some(Boolean))rows.push(row);row=[];field='';}else field+=c;}if(quote)throw Error('CSV 따옴표 오류');if(field||row.length){row.push(field);rows.push(row);}const head=rows.shift();return rows.map(r=>Object.fromEntries(head.map((h,i)=>[h,r[i]||''])));}
$('results_file').addEventListener('change',async e=>{try{if(!dataset)throw Error('검수 세트부터 불러오세요.');const parsed=parseCSV(await e.target.files[0].text());const rid=$('reviewer').value.trim();if(!rid)throw Error('검수자 ID를 먼저 입력하세요.');const imported={};for(const r of parsed){const row=dataset.rows.find(x=>x.id===r.id);if(!row||r.review_set_id!==dataset.set_id||r.reviewer_id!==rid)throw Error('세트·표본·검수자 ID가 일치하지 않습니다.');if(imported[r.id])throw Error('중복 표본 ID');r.status=r.human_review_status==='검수완료(단일검수)'?'reviewed_single':'draft';if(r.status==='reviewed_single'&&!valid(r,row))throw Error('필수 검수값이 없는 완료 행');imported[r.id]=r;}results=imported;persist();render();$('message').textContent='CSV를 복원했습니다.';}catch(err){$('message').textContent=err.message;}});
$('audio').addEventListener('error',()=>{$('audio_note').textContent='음성 경로를 열지 못했습니다. 프로젝트 폴더에서 페이지를 열고 실제 WAV 존재 여부를 확인하세요. 청취 전 완료로 표시하지 마세요.';});
