"""Actual CPU-only tiny ASR; compare decoding settings, not different models."""
import os,sys,time,json,csv,re,hashlib,importlib.util,importlib.metadata,platform,wave,argparse
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(BASE/'packages'))
os.environ['HF_HUB_OFFLINE']='1';os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
import numpy as np
from faster_whisper import WhisperModel
spec=importlib.util.spec_from_file_location('metrics',ROOT/'phase2_review_stt_20261029/stt/experiment.py')
metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-name',default='');args=parser.parse_args()
    if args.run_name and not re.fullmatch(r'[A-Za-z0-9_-]+',args.run_name):raise SystemExit('Invalid run name')
    outdir=BASE/'results' if not args.run_name else BASE/'results/runs'/args.run_name
    outdir.mkdir(parents=True,exist_ok=True)
    output=outdir/'local_stt_predictions_run1.jsonl'
    if output.exists():raise SystemExit('Results already exist; do not overwrite actual run')
    with (ROOT/'phase2_review_stt_20261029/stt/manifest12.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    load_start=time.perf_counter();model=WhisperModel(str(BASE/'models/tiny'),device='cpu',compute_type='int8',cpu_threads=4,num_workers=1,local_files_only=True);load_s=time.perf_counter()-load_start
    warm_start=time.perf_counter();list(model.transcribe(np.zeros(16000,dtype=np.float32),language='ko',beam_size=5,vad_filter=False)[0]);warm_s=time.perf_counter()-warm_start
    allrows=[]
    with output.open('x',encoding='utf-8') as out:
        # Alternate the first decoding configuration to reduce systematic order bias.
        for i,r in enumerate(rows):
            path=ROOT/r['audio_path']
            with path.open('rb') as f:assert hashlib.file_digest(f,'sha256').hexdigest()==r['sha256']
            with wave.open(str(path),'rb') as w:
                assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(16000,1,2)
                waveform=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768.0
            for beam in ([1,5] if i%2==0 else [5,1]):
                t0=time.perf_counter()
                generated,info=model.transcribe(waveform,language='ko',beam_size=beam,best_of=1,temperature=0,vad_filter=False,condition_on_previous_text=True)
                segments=list(generated);wall=time.perf_counter()-t0;text=''.join(s.text for s in segments)
                ref=metrics.normalize(r['source_reference']);hyp=metrics.normalize(text);score,align=metrics.edit_alignment(ref,hyp)
                candidates=list(re.finditer(r'(?<!\S)(어|음)(?=[\s.,!?]|$)',r['source_reference']));kept=0
                for m in candidates:
                    start=len(metrics.normalize(r['source_reference'][:m.start()]));end=start+len(m.group(1))
                    kept+=all(j in align for j in range(start,end))
                rec={'id':r['id'],'model':f'faster_whisper_tiny_int8_beam{beam}','status':'ok','mode':'offline_file',
                    'audio_sha256':r['sha256'],'audio_duration_s':float(r['duration_s']),'beam_size':beam,'wall_s':wall,'real_time_factor':wall/float(r['duration_s']),
                    'text':text,'segments':[{'start_s':s.start,'end_s':s.end,'text':s.text} for s in segments],
                    'reference_source':'unreviewed_aihub','provisional_CER':score,'literal_eo_eum_candidates':len(candidates),'literal_eo_eum_aligned':kept,
                    'not_measured':['human_verified_CER','true_filler_precision_recall','streaming_latency','drift_detection_accuracy']}
                allrows.append(rec);out.write(json.dumps(rec,ensure_ascii=False)+'\n');out.flush()
                print(r['id'],'beam',beam,'wall',round(wall,3),'provisional_CER',round(score['CER'],4),flush=True)
    summary=[]
    for beam in [1,5]:
        rr=[r for r in allrows if r['beam_size']==beam];audio=sum(r['audio_duration_s'] for r in rr);wall=sum(r['wall_s'] for r in rr);n=sum(r['provisional_CER']['N'] for r in rr);edits=sum(r['provisional_CER']['edits'] for r in rr);filler=sum(r['literal_eo_eum_candidates'] for r in rr)
        summary.append({'model':f'tiny_int8_beam{beam}','files':len(rr),'audio_minutes':audio/60,'decode_seconds':wall,'overall_real_time_factor':wall/audio,
                        'provisional_micro_CER':edits/n,'provisional_macro_CER':sum(r['provisional_CER']['CER'] for r in rr)/len(rr),
                        'literal_eo_eum_candidates':filler,'literal_eo_eum_aligned':sum(r['literal_eo_eum_aligned'] for r in rr),
                        'literal_eo_eum_alignment_ratio':sum(r['literal_eo_eum_aligned'] for r in rr)/filler if filler else None})
    environment={'python':sys.version,'platform':platform.platform(),'processor':platform.processor(),'device':'cpu','threads':4,'compute_type':'int8','language':'ko','temperature':0,'best_of':1,'vad_filter':False,'condition_on_previous_text':True,
                 'load_seconds':load_s,'synthetic_silence_warmup_seconds':warm_s,'audio_loading':'standard-library wave + PCM16 to float32, outside decode timing; bypass PyAV 19 metadata_errors incompatibility','configuration_order':'beam1 first on even-indexed files, beam5 first on odd-indexed files','repetitions_per_setting_per_file':1,
                 'packages':{p:importlib.metadata.version(p) for p in ['numpy','faster-whisper','ctranslate2','av','tokenizers','onnxruntime','huggingface-hub']},'paid_api_calls':0,'audio_uploaded':False}
    (outdir/'stt_summary.json').write_text(json.dumps({'summary':summary,'scope':'Actual local inference; one tiny model with two decoding settings. AIHub reference is unreviewed. Not a model-family comparison or real-time benchmark.','environment':environment},ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE',json.dumps(summary,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
