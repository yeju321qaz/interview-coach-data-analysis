"""Download only four public tiny-model assets, with a 90 MB cap."""
import json,urllib.request,hashlib,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
REPO='Systran/faster-whisper-tiny'
FILES=['config.json','model.bin','tokenizer.json','vocabulary.txt']
def main():
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}?blobs=true',timeout=30) as r:meta=json.load(r)
    revision=meta['sha'];items={x['rfilename']:x for x in meta['siblings']}
    total=sum(items[n]['size'] for n in FILES)
    if total>90_000_000:raise RuntimeError('Download exceeds approved tiny-model size cap')
    target=BASE/'models/tiny';target.mkdir(exist_ok=True)
    records=[]
    for name in FILES:
        item=items[name];out=target/name
        if not(out.exists() and out.stat().st_size==item['size']):
            partial=out.with_suffix(out.suffix+'.part')
            req=urllib.request.Request(f'https://huggingface.co/{REPO}/resolve/{revision}/{name}',headers={'User-Agent':'interview-coach-local-validation'})
            with urllib.request.urlopen(req,timeout=60) as response,partial.open('wb') as f:
                received=0
                while data:=response.read(1024*1024):
                    received+=len(data)
                    if received>item['size']:raise RuntimeError('Unexpected download length')
                    f.write(data)
            if partial.stat().st_size!=item['size']:raise RuntimeError('Incomplete model asset')
            partial.rename(out)
        with out.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        expected=item.get('lfs',{}).get('sha256')
        if expected and digest!=expected:raise RuntimeError('Model checksum mismatch')
        records.append({'name':name,'bytes':out.stat().st_size,'sha256':digest,'upstream_lfs_sha256':expected})
        print(name,out.stat().st_size,flush=True)
    (BASE/'model_download.json').write_text(json.dumps({'repo':REPO,'revision':revision,'bytes':total,'files':records,'audio_uploaded':False},indent=2),encoding='utf-8')
if __name__=='__main__':main()
