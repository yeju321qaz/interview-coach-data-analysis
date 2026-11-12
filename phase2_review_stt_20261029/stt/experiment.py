"""No network/model loading by default. Explicit execution and paid-data gates.

Cloud adapters: paced PCM replay; faster-whisper: offline full-file baseline.
"""
import argparse,csv,json,sys,os,time,wave,hashlib,threading,unicodedata,statistics,importlib.util
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent.parent

def readcsv(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(p,data):Path(p).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def normalize(s):
    return ''.join(c for c in unicodedata.normalize('NFC',s).lower() if not c.isspace() and not unicodedata.category(c).startswith('P'))
def edit_alignment(ref,hyp):
    # DP with deterministic tie-breaking; byte traceback keeps memory bounded.
    n,m=len(ref),len(hyp);trace=[bytearray(m+1) for _ in range(n+1)]
    prev=list(range(m+1))
    for j in range(1,m+1):trace[0][j]=2
    for i in range(1,n+1):
        curr=[i]+[0]*m;trace[i][0]=1
        for j in range(1,m+1):
            candidates=(prev[j-1]+(ref[i-1]!=hyp[j-1]),prev[j]+1,curr[j-1]+1)
            direction=min(range(3),key=lambda k:candidates[k]);curr[j]=candidates[direction];trace[i][j]=direction
        prev=curr
    i,j=n,m;S=D=I=0;matches={}
    while i or j:
        direction=trace[i][j]
        if direction==0:
            i-=1;j-=1
            if ref[i]==hyp[j]:matches[i]=j
            else:S+=1
        elif direction==1:i-=1;D+=1
        else:j-=1;I+=1
    return {'S':S,'D':D,'I':I,'N':n,'edits':S+D+I,'CER':(S+D+I)/n if n else None},matches

def frames(path,t0,events):
    with wave.open(str(path),'rb') as w:
        sent=0;sr=w.getframerate()
        while True:
            data=w.readframes(sr//10)
            if not data:break
            sent+=len(data)//2
            time.sleep(max(0,t0+sent/sr-time.perf_counter()))
            events.append({'type':'audio_sent','audio_end_s':sent/sr,'elapsed_s':time.perf_counter()-t0})
            yield data

def google_run(path,args):
    from google.cloud.speech_v2 import SpeechClient
    from google.cloud.speech_v2.types import cloud_speech as cs
    from google.api_core.client_options import ClientOptions
    client=SpeechClient(client_options=ClientOptions(api_endpoint=f'{args.google_region}-speech.googleapis.com'))
    config=cs.RecognitionConfig(explicit_decoding_config=cs.ExplicitDecodingConfig(encoding=cs.ExplicitDecodingConfig.AudioEncoding.LINEAR16,sample_rate_hertz=16000,audio_channel_count=1),language_codes=['ko-KR'],model='chirp_3')
    streamconfig=cs.StreamingRecognitionConfig(config=config,streaming_features=cs.StreamingRecognitionFeatures(interim_results=True))
    recognizer=f'projects/{os.environ["GOOGLE_CLOUD_PROJECT"]}/locations/{args.google_region}/recognizers/_'
    events=[];t0=time.perf_counter();final=[]
    def requests():
        yield cs.StreamingRecognizeRequest(recognizer=recognizer,streaming_config=streamconfig)
        for block in frames(path,t0,events):yield cs.StreamingRecognizeRequest(audio=block)
    for response in client.streaming_recognize(requests=requests(),timeout=240):
        for r in response.results:
            if not r.alternatives:continue
            text=r.alternatives[0].transcript
            end=r.result_end_offset.total_seconds();elapsed=time.perf_counter()-t0
            events.append({'type':'final' if r.is_final else 'partial','text':text,'audio_end_s':end,'elapsed_s':elapsed,'final_delay_s':elapsed-end if r.is_final else None})
            if r.is_final:final.append(text)
    return ' '.join(final),events,time.perf_counter()-t0

def azure_run(path,args):
    import azure.cognitiveservices.speech as sdk
    config=sdk.SpeechConfig(subscription=os.environ['AZURE_SPEECH_KEY'],region=os.environ['AZURE_SPEECH_REGION'])
    config.speech_recognition_language='ko-KR'
    config.set_profanity(sdk.ProfanityOption.Raw)
    push=sdk.audio.PushAudioInputStream(stream_format=sdk.audio.AudioStreamFormat(samples_per_second=16000,bits_per_sample=16,channels=1))
    recognizer=sdk.SpeechRecognizer(speech_config=config,audio_config=sdk.audio.AudioConfig(stream=push))
    events=[];final=[];errors=[];done=threading.Event();t0=time.perf_counter()
    def callback(event,is_final):
        r=event.result
        if is_final and r.reason!=sdk.ResultReason.RecognizedSpeech:return
        elapsed=time.perf_counter()-t0;end=(r.offset+r.duration)/10_000_000
        events.append({'type':'final' if is_final else 'partial','text':r.text,'audio_end_s':end,'elapsed_s':elapsed,'final_delay_s':elapsed-end if is_final else None})
        if is_final:final.append((r.offset,r.text))
    def canceled(e):
        if e.reason==sdk.CancellationReason.Error:errors.append(str(e.error_details))
        done.set()
    recognizer.recognizing.connect(lambda e:callback(e,False));recognizer.recognized.connect(lambda e:callback(e,True))
    recognizer.session_stopped.connect(lambda e:done.set());recognizer.canceled.connect(canceled)
    recognizer.start_continuous_recognition_async().get();t0=time.perf_counter()
    try:
        for block in frames(path,t0,events):
            if done.is_set():raise RuntimeError('Recognizer stopped before all audio was sent')
            push.write(block)
        push.close()
        if not done.wait(45):raise TimeoutError('No end-of-stream completion in 45 seconds')
        if errors:raise RuntimeError('; '.join(errors))
    finally:recognizer.stop_continuous_recognition_async().get()
    return ' '.join(text for _,text in sorted(final)),events,time.perf_counter()-t0

def local_run(path,args,model):
    t0=time.perf_counter()
    segments,_=model.transcribe(str(path),language='ko',beam_size=5,temperature=0,vad_filter=False,condition_on_previous_text=True)
    out=list(segments) # The generator must be consumed before timing stops.
    return ''.join(s.text for s in out),[],time.perf_counter()-t0

def preflight(rows,args):
    for row in rows:
        p=ROOT/row['audio_path']
        with p.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==row['sha256'],row['id']
        with wave.open(str(p),'rb') as w:assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(16000,1,2)
    total=sum(float(r['duration_s']) for r in rows)/60
    return {'state':'DRY_RUN_NO_MODEL_OR_API','files':len(rows),'audio_minutes':total,'provider':args.provider,
        'local_model_directory_exists':bool(args.model_dir and Path(args.model_dir).is_dir()),
        'cloud_permission_required':args.provider!='local','estimated_google_usd_at_0_016_per_min':round(total*.016,4),
        'note':'Google 단가 가정에 따른 비용 예시; 실제 과금·Azure 단가는 실행 전 확인. CER/지연/간투사 성능 미측정.'}

def run(args):
    rows=readcsv(args.manifest)[:args.limit];check=preflight(rows,args);print(json.dumps(check,ensure_ascii=False,indent=2))
    if not args.execute:return
    if sum(float(r['duration_s']) for r in rows)/60>args.max_minutes:raise SystemExit('Audio duration exceeds --max-minutes')
    output=Path(args.output)
    if output.exists():raise SystemExit('Output exists: choose a new run filename')
    model=None
    if args.provider!='local':
        if not(args.allow_paid and args.data_permission_confirmed):raise SystemExit('Cloud requires --allow-paid and --data-permission-confirmed after human approval')
        required=['GOOGLE_CLOUD_PROJECT'] if args.provider=='google' else ['AZURE_SPEECH_KEY','AZURE_SPEECH_REGION']
        if any(not os.environ.get(k) for k in required):raise SystemExit('Missing cloud configuration: '+', '.join(required))
    else:
        if not args.model_dir or not (Path(args.model_dir)/'model.bin').is_file():raise SystemExit('Provide existing converted Whisper model directory; automatic download is disabled')
        from faster_whisper import WhisperModel
        model=WhisperModel(args.model_dir,device=args.device,compute_type='int8' if args.device=='cpu' else 'float16',local_files_only=True)
    output.parent.mkdir(parents=True,exist_ok=True)
    run_id=time.strftime('%Y%m%d_%H%M%S')
    with output.open('x',encoding='utf-8') as f:
        for row in rows:
            item={'id':row['id'],'model':args.provider+'_'+('chirp_3' if args.provider=='google' else 'standard_service' if args.provider=='azure' else Path(args.model_dir).name),
                'run_id':run_id,'audio_sha256':row['sha256'],'mode':'offline_file' if args.provider=='local' else 'paced_streaming_100ms','model_directory':args.model_dir if args.provider=='local' else None,'status':'error'}
            try:
                fn=google_run if args.provider=='google' else azure_run if args.provider=='azure' else None
                text,events,wall=fn(ROOT/row['audio_path'],args) if fn else local_run(ROOT/row['audio_path'],args,model)
                item.update(status='ok',text=text,events=events,wall_s=wall,audio_duration_s=float(row['duration_s']),real_time_factor=wall/float(row['duration_s']))
            except Exception as e:
                item.update(error_type=type(e).__name__,error=str(e))
            f.write(json.dumps(item,ensure_ascii=False)+'\n');f.flush()
            # Stop on errors; avoid silent retry/cost multiplication.
            if item['status']!='ok':raise SystemExit('Stopped after provider error; inspect output')
    dump(str(output)+'.config.json',{'provider':args.provider,'google_region':args.google_region,'device':args.device,'mode':item['mode'],'run_id':run_id,'normalization_version':'nfc_lower_remove_space_punctuation_v1','local_model_load_in_timing':False,'cloud_sdk_versions':{p:package_version(p) for p in ['google-cloud-speech','azure-cognitiveservices-speech','faster-whisper']}})
def package_version(p):
    import importlib.metadata
    try:return importlib.metadata.version(p)
    except importlib.metadata.PackageNotFoundError:return None

def score(args):
    refs={r['id']:r for r in readcsv(args.manifest)}
    predictions=[json.loads(l) for l in Path(args.predictions).read_text(encoding='utf-8').splitlines() if l.strip()]
    spans=readcsv(BASE/'filler_spans.csv');audits=readcsv(BASE/'hyp_filler_audit.csv');out=[];seen=set()
    for p in predictions:
        identity=(p['id'],p['model'])
        if identity in seen:raise ValueError('Duplicate id/model; score one run per file')
        seen.add(identity)
        if p['id'] not in refs:raise ValueError('Unknown prediction id')
        r=refs[p['id']];base={'id':p['id'],'model':p['model'],'status':p.get('status'),'reference_source':args.reference_source}
        if p.get('audio_sha256')!=r['sha256']:raise ValueError('Prediction/reference audio hash mismatch')
        if p.get('status')!='ok':out.append(base);continue
        verified=r['reference_status']=='human_verified' and bool(r['reference_reviewer']) and bool(r['reference_corrected'])
        if args.reference_source=='verified' and not verified:base['status']='reference_unverified';out.append(base);continue
        ref=normalize(r['reference_corrected'] if args.reference_source=='verified' else r['source_reference']);hyp=normalize(p['text'])
        metrics,matches=edit_alignment(ref,hyp)
        if not metrics['N']:raise ValueError('Empty normalized reference')
        annotated=[s for s in spans if s['id']==p['id'] and s['status']=='human_verified' and s['reviewer_id']]
        hits=0
        for s in annotated:
            start,end=int(s['ref_start']),int(s['ref_end'])
            if args.reference_source!='verified':raise ValueError('Filler spans require human-verified reference')
            if not 0<=start<end<=len(ref) or ref[start:end]!=normalize(s['text']):raise ValueError('Invalid filler reference span')
            aligned=[matches.get(i) for i in range(start,end)]
            hits+=all(x is not None for x in aligned) and aligned==list(range(aligned[0],aligned[0]+end-start))
        final_delays=[e['final_delay_s'] for e in p.get('events',[]) if e['type']=='final' and e.get('final_delay_s') is not None]
        base.update(metrics,status='scored',metric_scope='human_verified_reference' if args.reference_source=='verified' else 'provisional_aihub_reference',
            filler_reference_events=len(annotated) if annotated else None,filler_preserved=hits if annotated else None,filler_recall=hits/len(annotated) if annotated else None,
            wall_s=p.get('wall_s'),mode=p.get('mode'),final_delay_p50_s=statistics.median(final_delays) if final_delays else None,
            final_delay_p90_s=percentile(final_delays,.9) if final_delays else None)
        # Precision requires a separate exhaustive human audit of predicted filler events.
        ha=[v for v in audits if v['id']==p['id'] and v['model']==p['model'] and v['status']=='human_verified' and v['reviewer_id'] and v['is_filler']=='true']
        base['filler_precision_audit_rows']=len(ha);base['filler_precision']=None
        out.append(base)
    summary=[]
    for model in sorted({p['model'] for p in predictions}):
        rr=[r for r in out if r['model']==model];scored=[r for r in rr if r['status']=='scored'];n=sum(r['N'] for r in scored)
        summary.append({'model':model,'manifest_files':len(refs),'prediction_files':len(rr),'missing_predictions':len(refs)-len(rr),'status_counts':dict(__import__('collections').Counter(r['status'] for r in rr)),
            'scored_files':len(scored),'micro_CER':sum(r['edits'] for r in scored)/n if n else None,'macro_CER':statistics.mean(r['CER'] for r in scored) if scored else None,'reference_source':args.reference_source,
            'note':'Not a final benchmark if references unverified, files missing, or runs failed. Filler precision requires exhaustive manual hypothesis annotation; not automatically inferred.'})
    target=Path(args.output)
    if target.exists():raise SystemExit('Choose a new output filename')
    dump(target,{'summary':summary,'per_file':out});print(json.dumps(summary,ensure_ascii=False,indent=2))
def percentile(values,p):
    if not values:return None
    s=sorted(values);x=(len(s)-1)*p;i=int(x);return s[i]+(s[min(i+1,len(s)-1)]-s[i])*(x-i)
def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run');r.add_argument('--provider',choices=['local','google','azure'],default='local');r.add_argument('--manifest',default=str(BASE/'manifest12.csv'));r.add_argument('--limit',type=int,default=12)
    r.add_argument('--execute',action='store_true');r.add_argument('--allow-paid',action='store_true');r.add_argument('--data-permission-confirmed',action='store_true');r.add_argument('--max-minutes',type=float,default=15)
    r.add_argument('--model-dir');r.add_argument('--device',choices=['cpu','cuda'],default='cpu');r.add_argument('--google-region',default='us');r.add_argument('--output',default=str(BASE/'predictions.jsonl'))
    s=sub.add_parser('score');s.add_argument('--manifest',default=str(BASE/'manifest12.csv'));s.add_argument('--predictions',required=True);s.add_argument('--reference-source',choices=['verified','aihub'],default='verified');s.add_argument('--output',required=True)
    args=p.parse_args()
    if getattr(args,'limit',1)<=0:raise SystemExit('--limit must be positive')
    (run if args.command=='run' else score)(args)
if __name__=='__main__':main()
