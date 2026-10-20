import pandas as pd,numpy as np,json,re,warnings
from pathlib import Path
from scipy import stats
import statsmodels.formula.api as smf
import statsmodels.api as sm
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
warnings.filterwarnings('ignore',category=FutureWarning)
O=Path('outputs');T=O/'tables';F=O/'figures';T.mkdir(exist_ok=True);F.mkdir(exist_ok=True)
d=pd.read_csv(O/'constituency_master.csv').sort_values('ac_no').reset_index(drop=True)
geo=json.load(open('work/raw/tn.geojson'));geod={x['properties']['AC_NO']:x for x in geo['features']}
for i,row in d.iterrows():
 g=geod[row.ac_no]['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']];area=0;cent=[]
 for poly in polys:
  for k,ring in enumerate(poly):
   xy=np.array(ring);cent.extend(xy.tolist() if k==0 else []);xx=xy[:,0]*111.32*np.cos(np.deg2rad(xy[:,1].mean()));yy=xy[:,1]*110.574
   area+=(1 if k==0 else -1)*abs(np.dot(xx,np.roll(yy,1))-np.dot(yy,np.roll(xx,1)))/2
 d.loc[i,'area_km2_approx']=area;d.loc[i,'longitude']=np.mean(np.array(cent)[:,0]);d.loc[i,'latitude']=np.mean(np.array(cent)[:,1])
d['log_elector_density']=np.log(d.pre_sir_electorate_reconstructed/d.area_km2_approx)
d['district']=d.district.str.strip();d['previous_party_group']=d.winner_party_2021.where(d.winner_party_2021.isin(['DMK','ADMK','INC','BJP']),'Other')
dmk=['DMK','INC','CPI','CPI(M)','VCK','IUML','DMDK'];admk=['ADMK','BJP','PMK','AMMKMNKZ']
d['winner_alliance_2026']=np.select([d.winner_party_2026.eq('TVK'),d.winner_party_2026.isin(dmk),d.winner_party_2026.isin(admk)],['TVK','DMK+','AIADMK+'],'Other')
def save(df,name,index=False):df.to_csv(T/(name+'.csv'),index=index)
def grouped(col):
 out=[]
 for k,g in d.groupby(col,observed=True):
  out.append({'group':str(k),'n':len(g),'tvk_wins':int(g.tvk_win.sum()),'dmk_wins':sum(g.winner_party_2026=='DMK'),'admk_wins':sum(g.winner_party_2026=='ADMK'),'other_party_wins':sum(~g.winner_party_2026.isin(['TVK','DMK','ADMK'])),'dmk_alliance_wins':sum(g.winner_alliance_2026=='DMK+'),'admk_alliance_wins':sum(g.winner_alliance_2026=='AIADMK+'),'other_alliance_wins':sum(g.winner_alliance_2026=='Other'),'tvk_win_rate_pct':100*g.tvk_win.mean(),'mean_tvk_share':g.tvk_share_2026.mean(),'median_tvk_share':g.tvk_share_2026.median(),'mean_margin':g.margin_2026.mean(),'mean_draft_exclusion_pct':g.draft_exclusion_pct.mean(),'mean_net_reduction_pct':g.net_reduction_pct.mean(),'mean_turnout_2021':g.turnout_2021.mean(),'mean_turnout_2026':g.turnout_2026.mean(),'mean_turnout_change':g.turnout_change.mean()})
 return pd.DataFrame(out)
labels=['≤10,000','10,001–20,000','20,001–30,000','30,001–50,000','50,001–80,000','>80,000']
for col,prefix in [('net_reduction_apr','net'),('draft_exclusions','draft')]:
 d[prefix+'_band']=pd.cut(d[col],[-np.inf,10000,20000,30000,50000,80000,np.inf],labels=labels);save(grouped(prefix+'_band'),prefix+'_bands')
for col,prefix in [('draft_exclusion_pct','draft'),('net_reduction_pct','net')]:
 d[prefix+'_rank']=d[col].rank(method='first',ascending=False).astype(int)
 for q in [5,10]:
  d[prefix+f'_q{q}']=pd.qcut(d[col].rank(method='first'),q,labels=range(1,q+1));save(grouped(prefix+f'_q{q}'),prefix+f'_q{q}')
 d[prefix+'_20_60_20']=np.select([d[prefix+'_q5'].astype(int)==1,d[prefix+'_q5'].astype(int)==5],['Bottom 20%','Top 20%'],'Middle 60%');save(grouped(prefix+'_20_60_20'),prefix+'_20_60_20')
save(grouped('previous_party_group'),'previous_party_performance')
save(d.groupby('previous_party_group').agg(n=('ac_no','size'),mean_draft=('draft_exclusions','mean'),median_draft=('draft_exclusions','median'),mean_net=('net_reduction_apr','mean'),median_net=('net_reduction_apr','median'),mean_draft_pct=('draft_exclusion_pct','mean'),median_draft_pct=('draft_exclusion_pct','median'),mean_net_pct=('net_reduction_pct','mean'),median_net_pct=('net_reduction_pct','median')),'previous_party_deletions',True)
save(grouped('district'),'districts');save(grouped('urban_rural_classification'),'urban_groups')
# Correlations: Pearson Fisher CI, paired percentile bootstrap Spearman CI.
rng=np.random.default_rng(20261006);corr=[]
pairs=[(x,y) for x in ['draft_exclusions','draft_exclusion_pct','net_reduction_apr','net_reduction_pct','net_rebound_pct'] for y in ['tvk_share_2026','dmk_share_2026','admk_share_2026','dmk_alliance_share_2026','admk_alliance_share_2026','turnout_change','margin_2026']]
for x,y in pairs:
 a,b=d[x].to_numpy(),d[y].to_numpy();n=len(a);pr=stats.pearsonr(a,b);ci=pr.confidence_interval(.95);sp=stats.spearmanr(a,b)
 ix=rng.integers(0,n,(3000,n));aa=stats.rankdata(a[ix],axis=1);bb=stats.rankdata(b[ix],axis=1);aa-=aa.mean(axis=1)[:,None];bb-=bb.mean(axis=1)[:,None];boot=(aa*bb).sum(axis=1)/np.sqrt((aa*aa).sum(axis=1)*(bb*bb).sum(axis=1));lo,hi=np.quantile(boot,[.025,.975])
 corr.extend([dict(x=x,y=y,method='Pearson',n=n,r=pr.statistic,ci_low=ci.low,ci_high=ci.high,p=pr.pvalue),dict(x=x,y=y,method='Spearman',n=n,r=sp.statistic,ci_low=lo,ci_high=hi,p=sp.pvalue)])
cor=pd.DataFrame(corr);from statsmodels.stats.multitest import multipletests
cor['p_fdr_bh']=multipletests(cor.p,method='fdr_bh')[1];save(cor,'correlations')
# Main controls are pre-treatment or static. Post-revision turnout and rebound are sensitivity only.
political='dmk_alliance_share_2021 + admk_alliance_share_2021 + margin_pct_2021 + C(previous_party_group)'
urban='urban_proxy + district_urban_pct_2011 + log_elector_density'
base=political+' + log_pre_electorate + turnout_2021 + pre_sir_growth_from_2021_pct + female_pct_apr'
specs={'unadjusted':'','urban_geography':urban,'political_baseline':base,'full':base+' + '+urban,'district_fe':base+' + urban_proxy + log_elector_density + C(district)','post_revision_sensitivity':base+' + urban_proxy + log_elector_density + C(district) + turnout_change + net_rebound_pct'}
coef=[];fits=[];models={}
def fit(formula,data,label,outcome,exposure,kind='OLS',cov='HC3'):
 try:
  if kind=='Logit':m=smf.logit(formula,data=data).fit(disp=False,maxiter=300,cov_type='HC1')
  else:m=smf.ols(formula,data=data).fit(cov_type=cov,cov_kwds={'groups':data.district} if cov=='cluster' else {})
  models[label]=m
  ci=m.conf_int();
  for v in m.params.index:coef.append(dict(model=label,outcome=outcome,exposure=exposure,kind=kind,covariance='HC1' if kind=='Logit' else cov,term=v,coef=m.params[v],se=m.bse[v],ci_low=ci.loc[v,0],ci_high=ci.loc[v,1],p=m.pvalues[v]))
  z=dict(model=label,outcome=outcome,exposure=exposure,kind=kind,n=int(m.nobs),r2=getattr(m,'rsquared',np.nan),adjusted_r2=getattr(m,'rsquared_adj',np.nan),pseudo_r2=getattr(m,'prsquared',np.nan),aic=m.aic,coefficient=m.params[exposure],se=m.bse[exposure],ci_low=ci.loc[exposure,0],ci_high=ci.loc[exposure,1],p=m.pvalues[exposure],effect_per_10pp=10*m.params[exposure])
  if kind=='Logit':
   p=m.predict();z['average_marginal_effect_per_pp']=np.mean(p*(1-p))*m.params[exposure];z['odds_ratio_10pp']=np.exp(10*m.params[exposure]);z['converged']=m.mle_retvals['converged']
  fits.append(z);return m
 except Exception as e:fits.append(dict(model=label,outcome=outcome,exposure=exposure,kind=kind,error=str(e)))
for exposure in ['draft_exclusion_pct','net_reduction_pct']:
 for outcome in ['tvk_share_2026','tvk_win','dmk_alliance_share_change','turnout_change']:
  for spec,controls in specs.items():
   if spec=='post_revision_sensitivity' and outcome=='turnout_change':continue
   formula=outcome+' ~ '+exposure+(' + '+controls if controls else '')
   kind='Logit' if outcome=='tvk_win' else 'OLS'
   # Fixed-effects logit drops all-win/all-loss districts to avoid separation.
   data=d
   if kind=='Logit' and spec in ['district_fe','post_revision_sensitivity']:
    valid=d.groupby('district').tvk_win.agg(['min','max']);data=d[d.district.isin(valid[valid['min']!=valid['max']].index)]
   fit(formula,data,f'{outcome}__{exposure}__{spec}',outcome,exposure,kind)
  if outcome!='tvk_win':fit(outcome+' ~ '+exposure+' + '+specs['district_fe'],d,f'{outcome}__{exposure}__district_cluster',outcome,exposure,cov='cluster')
  else:fit('tvk_win ~ '+exposure+' + '+specs['district_fe'],d,f'tvk_win__{exposure}__district_fe_LPM',outcome,exposure)
# Pre-SIR female percentage not available: above is composition sensitivity; also remove current sex composition.
for exposure in ['draft_exclusion_pct','net_reduction_pct']:
 ctrl=specs['district_fe'].replace(' + female_pct_apr','')
 fit('tvk_share_2026 ~ '+exposure+' + '+ctrl,d,f'tvk_share_2026__{exposure}__strict_pretreatment','tvk_share_2026',exposure)
# Robustness subsets, keeping controls parsimonious in small samples.
rob=[]
subsets={'all':d,'exclude_chennai':d[d.chennai==0],'chennai_only':d[d.chennai==1],'exclude_top10_gross':d.drop(d.nlargest(10,'draft_exclusions').index),'urban_proxy_only':d[d.urban_proxy==1],'rural_mixed_only':d[d.urban_proxy==0],'tvk_contested_only':d[d.tvk_contested==1]}
for name,dd in subsets.items():
 for x in ['draft_exclusion_pct','net_reduction_pct','draft_exclusions','net_reduction_apr']:
  for ctrl in ['', ' + dmk_alliance_share_2021 + admk_alliance_share_2021 + log_elector_density + turnout_2021']:
   m=smf.ols('tvk_share_2026 ~ '+x+ctrl,data=dd).fit(cov_type='HC3');ci=m.conf_int().loc[x]
   rob.append(dict(subset=name,exposure=x,adjusted=bool(ctrl),n=len(dd),coef=m.params[x],se=m.bse[x],ci_low=ci.iloc[0],ci_high=ci.iloc[1],p=m.pvalues[x],r2=m.rsquared))
save(pd.DataFrame(rob),'robustness')
# Addition/net rebound identity: do not put gross, net and rebound in the same model.
for x in ['draft_exclusion_pct','net_reduction_pct','net_rebound_pct']:
 fit('tvk_share_2026 ~ '+x+' + '+specs['district_fe'],d,'comparison_'+x,'tvk_share_2026',x)
fit('tvk_share_2026 ~ draft_exclusion_pct + net_rebound_pct + '+specs['district_fe'],d,'gross_and_rebound','tvk_share_2026','draft_exclusion_pct')
for x in ['shifted_absent_pct','deceased_pct','duplicate_pct']:
 fit('tvk_share_2026 ~ '+x+' + '+specs['district_fe'],d,'reason_'+x,'tvk_share_2026',x)
save(pd.DataFrame(coef),'regression_coefficients');save(pd.DataFrame(fits),'model_fit')
# Previous-party differences and adjusted association with the deletion rate.
tests=[]
for x in ['draft_exclusions','draft_exclusion_pct','net_reduction_pct']:
 a=d.loc[d.winner_party_2021=='DMK',x];b=d.loc[d.winner_party_2021=='ADMK',x];w=stats.ttest_ind(a,b,equal_var=False);u=stats.mannwhitneyu(a,b,alternative='two-sided');k=stats.kruskal(*[g[x].values for _,g in d.groupby('previous_party_group')]);tests.append(dict(variable=x,dmk_mean=a.mean(),admk_mean=b.mean(),difference=a.mean()-b.mean(),welch_t=w.statistic,welch_p=w.pvalue,mannwhitney_p=u.pvalue,kruskal_p=k.pvalue))
save(pd.DataFrame(tests),'previous_party_tests')
# Outcomes sensitivity: q is the share of draft-excluded entries that are distinct, eligible,
# still excluded at election, and would be restored. No assumption that q is observed.
d['flip_burden']=(d.margin_2026+1)/d.draft_exclusions
d['sensitivity_class']=np.select([d.flip_burden>.75,d.flip_burden>.10,d.flip_burden>.025],['Practically impossible within scenarios','Mathematically possible; demanding assumptions','Plausibly outcome-sensitive (scenario only)'],'Highly sensitive (scenario only)')
d['potentially_outcome_sensitive']=d.flip_burden<=.10
d['minimum_q_at_t70_p60']=(d.margin_2026+1)/(d.draft_exclusions*.7*.2)
d['minimum_q_at_t70_p70']=(d.margin_2026+1)/(d.draft_exclusions*.7*.4)
for t in [.5,.6,.7,.75]:d[f'p_needed_q100_t{int(t*100)}']=(1+(d.margin_2026+1)/(d.draft_exclusions*t))/2
sim=[]
for _,r in d.iterrows():
 for q in [.1,.25,.5,1.]:
  for t in [.5,.6,.7,.75]:
   n=int(np.floor(r.draft_exclusions*q*t));req=int(np.floor((n+r.margin_2026)/2)+1);pn=req/n if n else np.nan
   sim.append(dict(ac_no=r.ac_no,constituency=r.constituency,winner_party=r.winner_party_2026,margin=r.margin_2026,base='draft exclusions',q=q,turnout=t,restored_ballots=n,minimum_runnerup_votes=req,minimum_runnerup_preference=pn,possible=req<=n,minimum_preference_if_other20pct=(.8+(r.margin_2026+1)/max(n,1))/2))
save(pd.DataFrame(sim),'counterfactual_grid')
cols=['ac_no','constituency','winner_2026','winner_party_2026','runnerup_2026','runnerup_party_2026','margin_2026','draft_exclusions','draft_exclusion_pct','net_reduction_apr','net_reduction_pct','net_rebound_draft_apr','gross_additions_full_period','turnout_change','draft_deletion_margin_ratio','net_reduction_margin_ratio','winner_2021','winner_party_2021','party_control_changed','flip_burden','minimum_q_at_t70_p60','sensitivity_class']+[f'p_needed_q100_t{int(t*100)}' for t in [.5,.6,.7,.75]]
top=d.sort_values(['flip_burden','ac_no']).head(30);save(top[cols],'top30_outcome_sensitive')
save(d.sort_values('draft_rank'),'deletion_rank_all234')
save(d.groupby(['sensitivity_class','winner_alliance_2026']).size().unstack(fill_value=0),'sensitivity_counts',True)
# Same q,t,p applied to all seats is a scenario, not an estimated result.
sc=[]
for q in [.1,.25,.5,1.]:
 for t in [.5,.6,.7,.75]:
  for p in [.55,.6,.7,.8,1.]:
   yes=d.draft_exclusions*q*t*(2*p-1)>d.margin_2026
   sc.append(dict(q=q,t=t,p=p,seats=int(yes.sum()),tvk_won=int((yes & d.tvk_win.eq(1)).sum()),other_won=int((yes & d.tvk_win.eq(0)).sum())))
save(pd.DataFrame(sc),'scenario_seat_counts')
# Reason composition at high/low deletion intensity.
reason=d.groupby(['draft_q5','winner_alliance_2026'],observed=True).agg(n=('ac_no','size'),deceased=('deceased','sum'),shifted_absent=('shifted_absent','sum'),duplicate=('duplicate','sum'),total=('draft_exclusions','sum')).reset_index()
for x in ['deceased','shifted_absent','duplicate']:reason[x+'_share']=100*reason[x]/reason.total
save(reason,'reason_composition')
save(d[(d.draft_q5.astype(int)==5)&(d.tvk_win==0)].sort_values('tvk_share_2026'),'high_deletion_tvk_losses')
save(d[(d.draft_q5.astype(int)==1)&(d.tvk_win==1)].sort_values('margin_2026',ascending=False),'low_deletion_tvk_wins')
# Spatial clustering using symmetric six-nearest-neighbour graph; indicative boundary proxy.
xy=np.c_[d.longitude*np.cos(np.deg2rad(11))*111.32,d.latitude*110.574];dist=np.sqrt(((xy[:,None,:]-xy[None,:,:])**2).sum(2));np.fill_diagonal(dist,np.inf);W=np.zeros((234,234));W[np.arange(234)[:,None],np.argsort(dist,axis=1)[:,:6]]=1;W=np.maximum(W,W.T);W/=W.sum(axis=1)[:,None]
spatial=[]
for label,z in [('draft_exclusion_pct',d.draft_exclusion_pct),('tvk_share_2026',d.tvk_share_2026),('full_model_residual',models['tvk_share_2026__draft_exclusion_pct__district_fe'].resid)]:
 z=np.array(z)-np.mean(z);mi=(z@W@z)/(z@z);sims=np.array([(lambda zz:zz@W@zz/(zz@zz))(rng.permutation(z)) for _ in range(1999)]);spatial.append(dict(variable=label,moran_i=mi,permutation_p_two_sided=(1+sum(abs(sims+1/233)>=abs(mi+1/233)))/2000,n=234))
save(pd.DataFrame(spatial),'spatial_clustering')
# Within-district residual permutation test (Freedman-Lane) for the main exposure.
m=models['tvk_share_2026__draft_exclusion_pct__district_fe'];X=m.model.exog;names=m.model.exog_names;k=names.index('draft_exclusion_pct');Z=np.delete(X,k,axis=1);y=d.tvk_share_2026.to_numpy();yh=Z@np.linalg.lstsq(Z,y,rcond=None)[0];err=y-yh;pinv=np.linalg.pinv(X)[k];groups=[g.index.to_numpy() for _,g in d.groupby('district')];bs=[]
for _ in range(1999):
 e=err.copy()
 for ix in groups:e[ix]=rng.permutation(err[ix])
 bs.append(pinv@(yh+e))
save(pd.DataFrame([dict(test='within-district Freedman-Lane',coef=m.params.iloc[k],permutation_p=(1+sum(abs(np.array(bs))>=abs(m.params.iloc[k])))/2000,permutations=1999)]),'permutation_test')
# Publication plots.
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':140})
source='Sources: CEO Tamil Nadu SIR tables; ECI 2021/2026 statistical reports.'
def finish(fig,name,n=234,note=''):
 fig.text(.01,.012,f'{source} n={n}. {note}',fontsize=7,color='#50545a');fig.tight_layout(rect=[0,.055,1,.98]);fig.savefig(F/(name+'.png'),bbox_inches='tight');fig.savefig(F/(name+'.svg'),bbox_inches='tight');plt.close(fig)
def scatter(x,y,name,xlabel,ylabel):
 fig,ax=plt.subplots(figsize=(8,5.2));ax.scatter(d[x],d[y],c=np.where(d.chennai==1,'#b54b34','#277c8e'),alpha=.7,s=22)
 m=smf.ols(f'{y} ~ {x}',d).fit();xx=np.linspace(d[x].min(),d[x].max(),100);pr=m.get_prediction(pd.DataFrame({x:xx})).summary_frame();ax.plot(xx,pr['mean'],color='#192b41');ax.fill_between(xx,pr.mean_ci_lower,pr.mean_ci_upper,alpha=.12,color='#192b41')
 resid=abs(m.resid);ids=set(resid.nlargest(3).index)|set(d[x].nlargest(2).index)
 for i in ids:ax.annotate(d.loc[i,'constituency'],(d.loc[i,x],d.loc[i,y]),xytext=(4,5),textcoords='offset points',fontsize=7)
 ax.set(xlabel=xlabel,ylabel=ylabel,title=f'{ylabel} and {xlabel.lower()}');finish(fig,name,note='Red: Chennai. Line: unadjusted OLS; band: 95% mean CI.')
scatter('draft_exclusion_pct','tvk_share_2026','01_deletion_pct_tvk','Draft exclusions / pre-SIR electorate (%)','TVK vote share (%)')
scatter('draft_exclusions','tvk_share_2026','02_deletion_number_tvk','Draft-excluded entries','TVK vote share (%)')
scatter('net_reduction_pct','tvk_share_2026','03_net_pct_tvk','April net reduction / pre-SIR electorate (%)','TVK vote share (%)')
fig,ax=plt.subplots(figsize=(9,5));b=grouped('net_band');ax.bar(b.group,b.tvk_win_rate_pct,color='#277c8e');ax.set(ylabel='TVK win rate (%)',xlabel='April net electorate reduction',title='BusinessLine bands independently reproduced',ylim=(0,112));ax.tick_params(axis='x',labelrotation=15)
for i,r in b.iterrows():ax.text(i,r.tvk_win_rate_pct+2,f'{int(r.tvk_wins)}/{int(r.n)}',ha='center')
finish(fig,'04_band_win_rate',note='These bands measure net reduction, not gross deletions.')
fig,ax=plt.subplots(figsize=(8,5));ax.boxplot([g.tvk_share_2026 for _,g in d.groupby('draft_q5',observed=True)],tick_labels=[f'Q{k}\n(n={len(g)})' for k,g in d.groupby('draft_q5',observed=True)],patch_artist=True,boxprops={'facecolor':'#bbdce1'});ax.set(xlabel='Draft-exclusion rate quintile (low to high)',ylabel='TVK vote share (%)',title='TVK performance across size-normalised deletion quintiles');finish(fig,'05_quintile_vote_share')
fig,ax=plt.subplots(figsize=(8,5));groups=list(d.groupby('previous_party_group'));ax.boxplot([g.draft_exclusion_pct for _,g in groups],tick_labels=[f'{k}\n(n={len(g)})' for k,g in groups],patch_artist=True,boxprops={'facecolor':'#bbdce1'});ax.set(ylabel='Draft exclusion rate (%)',title='SIR exclusion rates by 2021 winning party');finish(fig,'06_previous_party_deletions')
fig,ax=plt.subplots(figsize=(9,10));tt=top.iloc[::-1];ax.barh(tt.constituency,tt.draft_deletion_margin_ratio,color=np.where(tt.tvk_win==1,'#277c8e','#a9b2bf'));ax.set(xscale='log',xlabel='Draft exclusions / 2026 winning margin (log scale)',title='Top 30 seats by arithmetic deletion-to-margin sensitivity');finish(fig,'07_deletion_margin_top30',n=30,note='Teal: TVK winner. Sensitivity is not evidence of wrongful deletion.')
scatter('draft_exclusion_pct','turnout_change','08_turnout_change','Draft exclusions / pre-SIR electorate (%)','Turnout change (percentage points)')
fig,axs=plt.subplots(1,2,figsize=(11,5));
for ax,x,title in zip(axs,['turnout_change','votes_polled_change_pct'],['Turnout percentage-point change','Change in ballots cast (%)']):ax.scatter(d.draft_exclusion_pct,d[x],s=15,alpha=.6);ax.set(xlabel='Draft exclusion rate (%)',ylabel=title,title=title)
finish(fig,'09_turnout_denominator')
def mapchart(columns,titles,name):
 fig,axs=plt.subplots(1,len(columns),figsize=(4*len(columns),7),squeeze=False)
 for ax,col,title in zip(axs[0],columns,titles):
  patches=[];values=[]
  for _,r in d.iterrows():
   g=geod[r.ac_no]['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
   for poly in polys:patches.append(Polygon(poly[0]));values.append(r[col])
  pc=PatchCollection(patches,cmap='viridis',linewidth=.2,edgecolor='white');pc.set_array(np.array(values));ax.add_collection(pc);ax.autoscale();ax.set_aspect(1/np.cos(np.deg2rad(11)));ax.set_axis_off();ax.set_title(title,fontsize=11);fig.colorbar(pc,ax=ax,shrink=.65)
 finish(fig,name,note='Boundaries: Baskicanvas/DataMeet (2021), illustrative; all 234 AC IDs matched.')
mapchart(['draft_exclusion_pct','tvk_share_2026'],['Draft exclusion rate (%)','TVK vote share (%)'],'10_geography_rates')
mapchart(['tvk_win','turnout_change','potentially_outcome_sensitive'],['TVK win (1=yes)','Turnout change (pp)','Scenario-sensitive (1=yes)'],'11_geography_outcomes')
fitdf=pd.DataFrame(fits);sel=fitdf[(fitdf.outcome=='tvk_share_2026')&(fitdf.exposure=='draft_exclusion_pct')&fitdf.model.str.contains('__')&~fitdf.model.str.contains('cluster|strict')]
fig,ax=plt.subplots(figsize=(9,5));yy=np.arange(len(sel));ax.errorbar(sel.coefficient,yy,xerr=[sel.coefficient-sel.ci_low,sel.ci_high-sel.coefficient],fmt='o',color='#277c8e',capsize=3);ax.set_yticks(yy,sel.model.str.split('__').str[-1]);ax.axvline(0,color='#999',lw=1);ax.set(xlabel='TVK share pp per 1 pp higher draft exclusion rate (95% CI)',title='How controls change the SIR–TVK association');finish(fig,'12_adjustment_coefficients')
d.to_csv(O/'constituency_master.csv',index=False)
print('BANDS',grouped('net_band').to_json(orient='records'));print('MODEL',sel[['model','coefficient','p','r2']].to_json(orient='records'));print('SENSITIVITY',d.groupby('sensitivity_class').size().to_dict());print('CORRELATIONS',cor[(cor.y=='tvk_share_2026')&(cor.method=='Pearson')].to_json(orient='records'))
