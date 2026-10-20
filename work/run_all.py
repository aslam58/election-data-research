"""Run from the extracted archive root. Uses cached sources; no network required."""
import os,subprocess,sys
from pathlib import Path
Path('outputs').mkdir(exist_ok=True)
os.environ.setdefault('MPLCONFIGDIR',str(Path('work/mpl').resolve()))
for script in ['build_data.py','analyze.py','extras.py','final_figures.py','package_sources.py','report.py']:
 print('Running',script,flush=True)
 subprocess.run([sys.executable,str(Path('work')/script)],check=True)
