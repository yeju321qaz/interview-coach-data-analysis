import csv,json,argparse,collections
from pathlib import Path
BASE=Path(__file__).resolve().parent
def read(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',default=str(BASE/'recording_plan_80_v2.csv'));p.add_argument('--family-map');p.add_argument('--output',default=str(BASE/'split_check.json'));args=p.parse_args()
    rows=read(args.plan);map_rows=read(args.family_map) if args.family_map else []
    mapping={r['question_family_id']:r['semantic_family_id'] for r in map_rows}
    if args.family_map:
        expected={r.get('actual_question_family_id') or r['question_family_id'] for r in rows}
        if set(mapping)!=expected or len(map_rows)!=len(mapping):raise ValueError('Map must include every family exactly once')
        if any(not r['semantic_family_id'] or not r['reviewer_1'] or not r['reviewer_2'] for r in map_rows):raise ValueError('Each semantic mapping requires two reviewers and a nonempty final family')
    parent={}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    def union(a,b):parent[find(a)]=find(b)
    for r in rows:
        speaker=r.get('actual_speaker_id') or r['speaker_id'];fid=r.get('actual_question_family_id') or r['question_family_id']
        union('s:'+speaker,'q:'+mapping.get(fid,fid))
    splits=collections.defaultdict(set)
    for r in rows:
        speaker=r.get('actual_speaker_id') or r['speaker_id'];splits[find('s:'+speaker)].add(r['split'])
    leaks=[{'component':k,'splits':sorted(v)} for k,v in splits.items() if len(v)>1]
    counts=collections.Counter((r['split'],r['scenario_target']) for r in rows)
    positions=collections.Counter((r['split'],r['scenario_target'],str(r['collection_order'])) for r in rows)
    result={'state':'FAIL' if leaks else 'ID_LEVEL_PASS','rows':len(rows),'speaker_count':len({r['speaker_id'] for r in rows}),
       'planned_family_count':len({r['question_family_id'] for r in rows}),'cross_split_components':leaks,
       'semantic_family_review':'mapping_applied_but_human_completeness_must_be_checked' if args.family_map else 'PENDING_NO_SEMANTIC_MAPPING',
       'actual_identity_verification':'PENDING' if any(not r.get('actual_speaker_id') for r in rows) else 'recorded_not_independently_verified',
       'split_type_counts':[{'split':s,'type':t,'n':n} for (s,t),n in sorted(counts.items())],
       'position_counts':[{'split':s,'type':t,'position':pos,'n':n} for (s,t,pos),n in sorted(positions.items())],
       'warning':'ID-level pass does not establish semantic independence or participant identity. All 80 rows are uncollected.'}
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k not in ['position_counts','split_type_counts']},ensure_ascii=False,indent=2))
    if leaks:raise SystemExit(1)
if __name__=='__main__':main()
