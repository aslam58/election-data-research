import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
O=Path('outputs');T=O/'tables';F=O/'figures'
a=pd.read_csv(T/'model_fit.csv');b=pd.read_csv(T/'strict_models.csv');rows=[]
for label,s in [('Unadjusted','unadjusted'),('Urban geography','urban_geography')]:
 r=a[a.model.eq('tvk_share_2026__draft_exclusion_pct__'+s)].iloc[0];rows.append((label,r.coefficient,r.ci_low,r.ci_high))
for label,s in [('Full controls (pre-revision)','strict_full'),('Official urban proxies only','official_urban_proxies_only'),('District fixed effects','strict_district_fe'),('District FE, no map-derived density','official_proxies_district_fe')]:
 r=b[(b.outcome=='tvk_share_2026')&(b.exposure=='draft_exclusion_pct')&(b.spec==s)].iloc[0];rows.append((label,r.coef,r.ci_low,r.ci_high))
fig,ax=plt.subplots(figsize=(10,5));y=np.arange(len(rows));z=np.array([r[1:] for r in rows]);ax.errorbar(z[:,0],y,xerr=[z[:,0]-z[:,1],z[:,2]-z[:,0]],fmt='o',color='#277c8e',capsize=4);ax.set_yticks(y,[r[0] for r in rows]);ax.invert_yaxis();ax.axvline(0,color='#888',lw=1);ax.set(xlabel='TVK vote-share pp per 1 pp higher draft exclusion rate (95% CI)',title='Association attenuates after accounting for geography and politics');ax.spines[['right','top']].set_visible(False)
fig.text(.02,.02,'Sources: CEO Tamil Nadu; ECI; TNRD; Census 2011; illustrative boundary geometry. All models n=234; HC3 intervals.',fontsize=8);fig.tight_layout(rect=[0,.06,1,1]);fig.savefig(F/'12_adjustment_coefficients.png',dpi=160,bbox_inches='tight');fig.savefig(F/'12_adjustment_coefficients.svg',bbox_inches='tight');plt.close(fig)
# Include the empty lowest gross-exclusion band explicitly.
f=T/'draft_bands.csv';x=pd.read_csv(f)
if not (x.group=='≤10,000').any():
 row={c:np.nan for c in x.columns};row['group']='≤10,000'
 for c in ['n','tvk_wins','dmk_wins','admk_wins','other_party_wins','dmk_alliance_wins','admk_alliance_wins','other_alliance_wins']:row[c]=0
 pd.concat([pd.DataFrame([row]),x],ignore_index=True).to_csv(f,index=False)
