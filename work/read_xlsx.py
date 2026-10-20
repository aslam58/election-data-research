from zipfile import ZipFile
from lxml import etree as E
import re,pandas as pd
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def sheets(path):
 with ZipFile(path) as z:
  strings=[]
  if 'xl/sharedStrings.xml' in z.namelist():
   strings=[''.join(x.itertext()) for x in E.fromstring(z.read('xl/sharedStrings.xml'))]
  out=[]
  for f in sorted([x for x in z.namelist() if re.match(r'xl/worksheets/sheet\d+.xml$',x)],key=lambda x:int(re.search(r'(\d+)\.xml',x)[1])):
   rows=[]
   for row in E.fromstring(z.read(f)).findall('.//s:sheetData/s:row',NS):
    vals={}
    for c in row:
     ref=c.get('r');letters=re.match('[A-Z]+',ref)[0];idx=0
     for a in letters:idx=idx*26+ord(a)-64
     v=c.find('s:v',NS);v=v.text if v is not None else None
     if c.get('t')=='s' and v is not None:v=strings[int(v)]
     elif c.get('t')=='inlineStr':v=''.join(c.find('s:is',NS).itertext())
     elif v is not None:
      try:v=float(v);v=int(v) if v.is_integer() else v
      except ValueError:pass
     vals[idx-1]=v
    rows.append(vals)
   out.append(pd.DataFrame(rows))
  return out
if __name__=='__main__':
 import sys
 s=sheets(sys.argv[1]);print(len(s));print(s[0].to_string(index=False,header=False,max_colwidth=70))
