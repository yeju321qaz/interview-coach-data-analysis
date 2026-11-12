"""Compare stored and rerun outputs, accounting for parallel segment row order."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'verification_20261029'
sys.path.insert(0,str(BASE/'packages'))
import numpy as np
import pandas as pd

def digest(p): return hashlib.file_digest(p.open('rb'),'sha256').hexdigest()

def main():
    rows=[]
    for old in sorted((ROOT/'outputs').glob('*')):
        if old.suffix=='.png': continue
        new=BASE/'reproduced'/old.name
        if not new.exists():
            rows.append(dict(file=old.name,status='未実行'.replace('未実行','미실행'))); continue
        if digest(old)==digest(new):
            rows.append(dict(file=old.name,status='바이트 일치')); continue
        if old.suffix=='.csv':
            a=pd.read_csv(old); b=pd.read_csv(new)
            if old.name=='segments.csv':
                a=a.sort_values(list(a.columns)).reset_index(drop=True)
                b=b.sort_values(list(b.columns)).reset_index(drop=True)
            if a.shape!=b.shape or list(a.columns)!=list(b.columns):
                rows.append(dict(file=old.name,status='스키마 또는 행수 불일치',old_shape=str(a.shape),new_shape=str(b.shape))); continue
            mismatches={}; maxdiff=0.0
            for c in a:
                if pd.api.types.is_numeric_dtype(a[c]) and pd.api.types.is_numeric_dtype(b[c]):
                    eq=np.isclose(a[c],b[c],rtol=1e-9,atol=1e-9,equal_nan=True)
                    dif=np.abs(a[c].to_numpy(dtype=float)-b[c].to_numpy(dtype=float))
                    if np.isfinite(dif).any(): maxdiff=max(maxdiff,float(np.nanmax(dif)))
                else: eq=a[c].fillna('').astype(str).to_numpy()==b[c].fillna('').astype(str).to_numpy()
                if not eq.all(): mismatches[c]=int((~eq).sum())
            rows.append(dict(file=old.name,status='불일치' if mismatches else '수치·내용 일치(행순서/직렬화 차이)',rows=len(a),mismatches=mismatches,max_abs_diff=maxdiff))
        elif old.suffix=='.jsonl':
            a=[json.loads(x) for x in old.read_text(encoding='utf-8').splitlines()]
            b=[json.loads(x) for x in new.read_text(encoding='utf-8').splitlines()]
            rows.append(dict(file=old.name,status='JSON 내용 일치' if a==b else '불일치'))
        else:
            rows.append(dict(file=old.name,status='줄바꿈 제외 일치' if old.read_text(encoding='utf-8')==new.read_text(encoding='utf-8') else '불일치'))
    (BASE/'comparison.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(rows,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
