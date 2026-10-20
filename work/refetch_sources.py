"""Optional fresh retrieval. Cached source hashes are in outputs/source_registry.csv.
Live sources can change. Download to a separate destination, never overwrite the audit cache.
"""
import csv,pathlib,subprocess
out=pathlib.Path('fresh_sources');out.mkdir(exist_ok=True)
with open('outputs/source_registry.csv') as f:
 for row in csv.DictReader(f):
  target=out/pathlib.Path(row['file']).name
  subprocess.run(['curl','--fail','--location','--max-time','90',row['url'],'--output',str(target)],check=True)
