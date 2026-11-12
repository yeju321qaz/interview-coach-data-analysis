"""Deterministic selection and non-destructive recording-plan revision."""
import csv,json,random,hashlib,wave,sys,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'verification_20261029/packages'))
import pandas as pd
def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def save(p,rows,fields=None):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    rows=read(ROOT/'verification_20261029/review/manual_review.csv')
    rng=random.Random(20261029);rng.shuffle(rows)
    types=list(pd.read_csv(ROOT/'verification_20261029/review/question_type_counts.csv').rule_type)
    chosen=[];used=set()
    def select(typ,n):
        eligible=[r for r in rows if r['id'] not in used and typ in r['rule_question_types'].split('|')]
        # Prefer available audio first, then quality flags, keeping deterministic tie order.
        eligible.sort(key=lambda r:(r['audio_pair_available']!='True',not bool(r['quality_flags'])))
        assert len(eligible)>=n,(typ,len(eligible),n)
        for r in eligible[:n]:
            v=r.copy();v['selection_stratum']=typ;v['review_set_id']='review48_v1'
            v['human_review_status']='미검수'; chosen.append(v);used.add(v['id'])
    for typ in sorted(types,key=lambda t:sum(t in r['rule_question_types'].split('|') for r in rows)):select(typ,3)
    select('미분류',4)
    for typ in ['경험/성과','상황가정/대처','지원동기/입사후포부','직무/전문성']:select(typ,2)
    assert len(chosen)==48
    save(BASE/'review/review_subset48.csv',chosen)
    dataset={'set_id':'review48_v1','description':'기존 275행 중 균형 검수 48행. 사람 검수 미실행. 로컬 전용.', 'types':types+['미분류','기타'], 'rows':chosen}
    (BASE/'review/review_subset48.json').write_text(json.dumps(dataset,ensure_ascii=False,indent=2),encoding='utf-8')
    save(BASE/'review/review_assignment.csv',[{'selection_stratum':t,'assigned_count':sum(r['selection_stratum']==t for r in chosen),'audio_available':sum(r['selection_stratum']==t and r['audio_pair_available']=='True' for r in chosen)} for t in types+['미분류']])
    au=pd.read_csv(ROOT/'outputs/audio_features.csv');au=au[au.kind=='answer']
    lab=pd.read_csv(ROOT/'outputs/labels.csv',usecols=['id','q_text','a_text','a_audio','a_filler_ratio','occupation','gender','experience','split'])
    lab['file']=lab.a_audio.str.split('/').str[-1].str[:-4]
    data=au.merge(lab,on='file',suffixes=('','_label'))
    stt=[]
    for subset,g in data.groupby('subset',sort=True):
        g=g.sort_values(['dur_s','file'])
        for quantile in [.25,.75]:
            row=g.iloc[round((len(g)-1)*quantile)]
            path=next((ROOT/'data').glob(f'*/01.원천데이터/{subset}/{row.file}.wav'))
            with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
            stt.append({'id':row.id,'file':row.file,'audio_path':str(path.relative_to(ROOT)).replace('\\','/'),
                'subset':subset,'duration_s':row.dur_s,'selection_duration_quantile':quantile,'gender':row.gender,'experience':row.experience,
                'occupation':row.occupation,'split':row.split,'filler_ratio_rule':row.a_filler_ratio,'rms_dbfs':row.rms_dbfs,'silence_ratio':row.silence_ratio,
                'sha256':digest,'question':row.q_text,'source_reference':row.a_text,'reference_corrected':'','reference_status':'unreviewed','reference_reviewer':'','notes':''})
    assert len(stt)==12 and len({r['id'] for r in stt})==12
    save(BASE/'stt/manifest12.csv',stt)
    save(BASE/'stt/filler_spans.csv',[],['id','event_id','ref_start','ref_end','text','reviewer_id','status'])
    save(BASE/'stt/hyp_filler_audit.csv',[],['id','model','hyp_start','hyp_end','text','is_filler','matched_reference_event','reviewer_id','status'])
    original=read(ROOT/'verification_20261029/collection/recording_plan_80.csv')
    # Williams design balances each condition's position and immediate predecessor.
    orders=[[0,1,3,2],[1,2,0,3],[2,3,1,0],[3,0,2,1]]
    kinds=['normal','sustained_drift','temporary_drift','star_missing']; revised=[]
    speakers=sorted({r['speaker_id'] for r in original})
    for i,s in enumerate(speakers):
        order=orders[i%4]
        for r in [r.copy() for r in original if r['speaker_id']==s]:
            r['previous_collection_order']=r['collection_order'];r['collection_order']=order.index(kinds.index(r['scenario_target']))+1
            r.update(order_design='Williams_4_v1',order_group=i%4+1,elicitation_mode='scripted_condition',
                observed_drift_origin='',first_exposure=(r['collection_order']==1),previous_answer_access='none',
                inter_trial_break_target_s=120,actual_break_s='',feedback_before_next='none',rehearsal_count='',
                natural_probe_eligible=(r['scenario_target']=='normal'),semantic_family_review_status='pending',
                actual_speaker_id='',actual_question_family_id='',memory_effect_notes='')
            revised.append(r)
    revised.sort(key=lambda r:(r['speaker_id'],r['collection_order']))
    save(BASE/'collection/recording_plan_80_v2.csv',revised)
    result={'review_rows':48,'audio_rows':sum(r['audio_pair_available']=='True' for r in chosen),'quality_flag_rows':sum(bool(r['quality_flags']) for r in chosen),
            'assignment':dict(collections.Counter(r['selection_stratum'] for r in chosen)),
            'stt_rows':12,'stt_minutes':sum(r['duration_s'] for r in stt)/60,
            'stt_subset_counts':dict(collections.Counter(r['subset'] for r in stt)),
            'recordings_planned':80,'recordings_collected':0,'human_review_completed':0}
    (BASE/'selection_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
