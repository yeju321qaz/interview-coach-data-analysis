"""Run unchanged legacy analysis with output paths redirected before module import."""
import os
import sys
import time
import json
import importlib
from pathlib import Path
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'verification_20261029'
sys.path.insert(0, str(BASE / 'packages'))
sys.path.insert(0, str(ROOT / 'src'))
os.environ['MPLCONFIGDIR'] = str(BASE / 'mplconfig')
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'

def main():
    import common
    common.OUT = BASE / 'reproduced'
    common.OUT.mkdir(exist_ok=True)
    if sys.argv[1] == 'environment':
        import importlib.metadata as md
        result = {'python': sys.version, 'executable': sys.executable,
                  'packages': {p: md.version(p) for p in ['numpy','pandas','scipy','scikit-learn','soundfile','matplotlib']}}
        (BASE / 'environment.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(result)
        return
    module = importlib.import_module(sys.argv[1])
    # Bound CPU and memory consumption, without changing analytical calculations.
    if hasattr(module, 'Pool'):
        import multiprocessing
        module.Pool = lambda: multiprocessing.Pool(processes=4)
    start = time.monotonic()
    module.main()
    elapsed = time.monotonic() - start
    with (BASE / 'timings.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'stage': sys.argv[1], 'seconds': elapsed}) + '\n')
    print('ELAPSED_SECONDS', elapsed)

if __name__ == '__main__':
    main()
