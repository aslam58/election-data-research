import pandas as pd,numpy as np
import statsmodels.formula.api as smf
from scipy import stats
from pathlib import Path
D=Path('outputs');T=D/'tables';d=pd.read_csv(D/'constituency_master.csv');c=pd.read_csv(D/'candidates_2026.csv')
d['dmdk_share_2026']=100*d.ac_no.map(c[c.party=='DMDK'].groupby('ac_no').votes.sum()).fillna(0)/d.valid_plus_nota_2026
d['dmk_core_share_change']=d.dmk_alliance_share_change-d.dmdk_share_2026
d['gross_addition_rate_pct']=np.nan
for g in ['male','female','third']:d['pre_sir_'+g]=np.nan;d['change_pre_sir_apr_'+g]=np.nan
d['documentation_related_exclusions']=np.nan;d['other_reason_exclusions']=np.nan
base='dmk_alliance_share_2021 + admk_alliance_share_2021 + margin_pct_2021 + C(previous_party_group) + log_pre_electorate + turnout_2021 + pre_sir_growth_from_2021_pct'
controls={'strict_full':base+' + urban_proxy + district_urban_pct_2011 + log_elector_density','official_urban_proxies_only':base+' + urban_proxy + district_urban_pct_2011','strict_district_fe':base+' + urban_proxy + log_elector_density + C(district)','strict_fe_plus_mnm':base+' + urban_proxy + log_elector_density + C(district) + mnm_share_2021','official_proxies_district_fe':base+' + urban_proxy + C(district)'}
rows=[];cs=[]
for x in ['draft_exclusion_pct','net_reduction_pct']:
 for y in ['tvk_share_2026','tvk_win','dmk_alliance_share_change','dmk_core_share_change','turnout_change']:
  for spec,ctrl in controls.items():
   dd=d
   if y=='tvk_win' and ('district_fe' in spec or spec=='strict_fe_plus_mnm'):
    mixed=d.groupby('district').tvk_win.nunique();dd=d[d.district.isin(mixed[mixed>1].index)]
   f=y+' ~ '+x+' + '+ctrl
   m=smf.logit(f,dd).fit(disp=False,maxiter=300,cov_type='HC1') if y=='tvk_win' else smf.ols(f,dd).fit(cov_type='HC3')
   ci=m.conf_int();row=dict(outcome=y,exposure=x,spec=spec,n=int(m.nobs),coef=m.params[x],se=m.bse[x],ci_low=ci.loc[x,0],ci_high=ci.loc[x,1],p=m.pvalues[x],r2=getattr(m,'rsquared',np.nan),pseudo_r2=getattr(m,'prsquared',np.nan))
   if y=='tvk_win':row.update(converged=m.mle_retvals['converged'],odds_ratio_10pp=np.exp(10*m.params[x]),average_marginal_effect_per_pp=np.mean(m.predict()*(1-m.predict()))*m.params[x])
   rows.append(row)
   for term in m.params.index:cs.append(dict(outcome=y,exposure=x,spec=spec,term=term,coef=m.params[term],se=m.bse[term],ci_low=ci.loc[term,0],ci_high=ci.loc[term,1],p=m.pvalues[term]))
pd.DataFrame(rows).to_csv(T/'strict_models.csv',index=False);pd.DataFrame(cs).to_csv(T/'strict_coefficients.csv',index=False)
# Additional alternative bins and net-outlier removal.
d['draft_rate_band']=pd.cut(d.draft_exclusion_pct,[0,5,10,15,20,30,100],include_lowest=True)
d.groupby('draft_rate_band',observed=True).agg(n=('ac_no','size'),tvk_win_rate=('tvk_win','mean'),tvk_share=('tvk_share_2026','mean')).to_csv(T/'alternative_rate_bands.csv')
r=[]
for x in ['draft_exclusion_pct','net_reduction_pct']:
 dd=d.drop(d.nlargest(10,'net_reduction_apr').index);m=smf.ols('tvk_share_2026 ~ '+x+' + '+controls['strict_full'],dd).fit(cov_type='HC3');ci=m.conf_int().loc[x];r.append(dict(exposure=x,n=len(dd),coef=m.params[x],se=m.bse[x],ci_low=ci.iloc[0],ci_high=ci.iloc[1],p=m.pvalues[x]))
pd.DataFrame(r).to_csv(T/'exclude_net_outliers.csv',index=False)
# Geography correlation and turnout arithmetic.
r=[]
for x in ['urban_proxy','district_urban_pct_2011','log_elector_density','pre_sir_growth_from_2021_pct','mnm_share_2021']:
 for y in ['draft_exclusion_pct','net_reduction_pct','tvk_share_2026']:
  a=stats.pearsonr(d[x],d[y]);r.append(dict(x=x,y=y,r=a.statistic,p=a.pvalue))
pd.DataFrame(r).to_csv(T/'confounder_correlations.csv',index=False)
# Raw prior-party association conditional on urban geography, not causal targeting.
m=smf.ols('draft_exclusion_pct ~ C(previous_party_group, Treatment(reference="ADMK")) + urban_proxy + district_urban_pct_2011 + log_elector_density + log_pre_electorate',d).fit(cov_type='HC3');ci=m.conf_int();pd.DataFrame(dict(coef=m.params,se=m.bse,ci_low=ci[0],ci_high=ci[1],p=m.pvalues)).to_csv(T/'previous_party_adjusted.csv')
# Stage totals and arithmetic audit.
assert np.allclose(d.deceased+d.shifted_absent+d.duplicate,d.draft_exclusions)
assert np.allclose(d.draft_exclusions-d.net_rebound_draft_apr,d.net_reduction_apr)
assert np.allclose(d.valid_plus_nota_2026+d.postal_rejected_2026+d.evm_excluded_2026,d.votes_polled_2026)
assert d.ac_no.nunique()==234 and not d[['draft_exclusion_pct','tvk_share_2026','turnout_change']].isna().any().any()
for yr in [2021,2026]:
 cc=pd.read_csv(D/f'candidates_{yr}.csv');assert len(cc[cc.party=='NOTA'])==234
for file,p in [('tn_elector_rolls_19022025.csv','draft'),('tn-rolls-feb2026.csv','feb'),('tn_acwise_gendercount.csv','apr')]:
 a=pd.read_csv('work/raw/'+file);print(file,a.columns.tolist(),a.shape)
print('TOTALS',d[['deceased','shifted_absent','duplicate','electorate_2021','electorate_2026','votes_polled_2021','votes_polled_2026']].sum().to_dict())
print('STRICT',pd.DataFrame(rows).query("outcome=='tvk_share_2026'").to_string(index=False))
d.to_csv(D/'constituency_master.csv',index=False)
