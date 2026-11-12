"""Give fragment-based reports an explicit UTF-8 HTML5 document envelope."""
from pathlib import Path
import re
def ensure_document(text):
    if re.search(r'<!doctype\s+html',text,re.I) and re.search(r'<meta\s+charset=["\x27]?utf-8',text,re.I):return text
    position=text.find('<div class="wrap">')
    if position<0:raise ValueError('Expected report wrapper not found')
    head=text[:position];body=text[position:]
    head=re.sub(r'<!--.*?-->','',head,flags=re.S)
    marker='<!-- presentation-refinement-v1 -->\n' if 'presentation-refinement-v1' in text else ''
    return '<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'+head+'\n</head>\n<body>\n'+marker+body+'\n</body>\n</html>\n'
if __name__=='__main__':
    root=Path(__file__).resolve().parent
    for rel in ['report/index.html','report/integrated_standalone.html']:
        p=root/rel;s=p.read_text(encoding='utf-8');p.write_text(ensure_document(s),encoding='utf-8')
    print('Explicit HTML5, UTF-8 and mobile viewport added')
