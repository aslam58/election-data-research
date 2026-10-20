import pandas as pd, numpy as np, re, json
from read_xlsx import sheets
from pathlib import Path
R=Path('work/raw'); O=Path('outputs'); O.mkdir(exist_ok=True)
def rolls(file,prefix):
 d=pd.read_html(R/file)[0]
 if 'AC No.' not in d:
  d['AC No.']=d['No. and Name of the AC'].str.extract(r'^(\d+)')
  d['District Name']=d['No. and Name of the District'].str.replace(r'^\d+-','',regex=True)
  d['Name of Assembly Constituency']=d['No. and Name of the AC'].str.replace(r'^\d+-','',regex=True)
 d=d[pd.to_numeric(d['AC No.'],errors='coerce').notna()].copy();d['ac_no']=d['AC No.'].astype(int)
 d=d.set_index('ac_no'); d=d.rename(columns={'District Name':'district','Name of District':'district','Name of Assembly Constituency':'constituency','Male':prefix+'_male','Female':prefix+'_female','Third Gender':prefix+'_third','Total':prefix+'_electorate'})
 return d[['district','constituency',prefix+'_male',prefix+'_female',prefix+'_third',prefix+'_electorate']]
d=rolls('ACwise_Gendercount_19122025.aspx.html','draft')
for file,p in [('ACwise_Gendercount_23022026.aspx.html','feb'),('ACwise_Gendercount_07042026.aspx.html','apr'),('ACwise_Gendercount_06012025.aspx.html','jan2025')]:
 t=rolls(file,p); d=d.join(t.drop(columns=['district','constituency']),validate='one_to_one')
a=pd.read_html(R/'ACwise_ASD.aspx.html')[0];a['ac_no']=a['No and Name of the AC'].str.extract(r'^(\d+)').astype(float);a=a.dropna(subset=['ac_no']).set_index('ac_no')
a=a.rename(columns={'Deceased':'deceased','Shifted/ Absent':'shifted_absent','Enrolled at multiple places':'duplicate','Total':'draft_exclusions'})
d=d.join(a[['deceased','shifted_absent','duplicate','draft_exclusions']],validate='one_to_one')
for c in d.columns:
 if c not in ['district','constituency']:d[c]=pd.to_numeric(d[c])
d['pre_sir_electorate_reconstructed']=d.draft_electorate+d.draft_exclusions
d['gross_deletions_full_period']=np.nan;d['gross_additions_full_period']=np.nan
d['net_reduction_apr']=d.pre_sir_electorate_reconstructed-d.apr_electorate
d['net_reduction_feb']=d.pre_sir_electorate_reconstructed-d.feb_electorate
d['net_change_apr']=-d.net_reduction_apr
d['net_rebound_draft_apr']=d.apr_electorate-d.draft_electorate
d['draft_exclusion_pct']=100*d.draft_exclusions/d.pre_sir_electorate_reconstructed
d['net_reduction_pct']=100*d.net_reduction_apr/d.pre_sir_electorate_reconstructed
d['net_rebound_pct']=100*d.net_rebound_draft_apr/d.pre_sir_electorate_reconstructed
d['shifted_absent_pct']=100*d.shifted_absent/d.pre_sir_electorate_reconstructed
d['deceased_pct']=100*d.deceased/d.pre_sir_electorate_reconstructed
d['duplicate_pct']=100*d.duplicate/d.pre_sir_electorate_reconstructed
for g in ['male','female','third']:d['change_draft_apr_'+g]=d['apr_'+g]-d['draft_'+g]
# Candidate results, original ECI party labels.
c26=pd.read_excel(R/'eci2026_10.xlsx',header=3)
c26=c26[pd.to_numeric(c26['AC NO.'],errors='coerce').notna()].copy()
c26=c26.rename(columns={'AC NO.':'ac_no','CANDIDATE NAME':'candidate','PARTY':'party','TOTAL':'votes'})
c26['candidate']=c26.candidate.str.replace(r'^\d+\s+','',regex=True)
c26['ac_no']=c26.ac_no.astype(int); c26['votes']=pd.to_numeric(c26.votes)
# Parse the archived official 2021 PDF text. Every candidate vote and constituency total reconciled below.
txt=(R/'results2021.txt').read_text().replace('14\nMALE 48 GENERAL IND Matchbox 73 0 73 0.04\nANBUMANIKANDANTAMILSOORIYAN.K','14 ANBUMANIKANDANTAMILSOORIYAN.K MALE 48 GENERAL IND Matchbox 73 0 73 0.04'); blocks=re.split(r'Constituency\s+(\d+)\s*\.\s*([^\n]+?)\s+TOTAL ELECTORS\s+(\d+)',txt)
rows=[]; totals=[]; bad=[]
for i in range(1,len(blocks),4):
 ac,name,el,body=blocks[i:i+4]; ac=int(ac)
 t=re.search(r'TURN OUT TOTAL:\s+(\d+)\s+(\d+)\s+(\d+)',body)
 if not t:bad.append((ac,'missing total'));continue
 totals.append({'ac_no':ac,'electorate_2021':int(el),'votes_polled_2021':int(t[3]),'turnout_2021':100*int(t[3])/int(el)})
 for line in re.split(r'(?m)(?=^\d+\s+\D)',body):
  m=re.match(r'^(\d+)\s+(.+?)\s+(MALE|FEMALE|THIRD(?: GENDER)?)\s+(\d+)\s+(GENERAL|SC|ST)\s+(\S+)\s+.*?(\d+)\s+(\d+)\s+(\d+)\b',line,re.S)
  if m:rows.append({'ac_no':ac,'candidate':' '.join(m[2].split()),'party':m[6],'votes':int(m[9])})
  else:
   m=re.match(r'^\d+\s+NOTA\s+NOTA\s+NOTA\s+(\d+)\s+(\d+)\s+(\d+)',line)
   if m: rows.append({'ac_no':ac,'candidate':'NOTA','party':'NOTA','votes':int(m[3])})
c21=pd.DataFrame(rows); totals=pd.DataFrame(totals).set_index('ac_no');d=d.join(totals)
for ac,g in c21.groupby('ac_no'):
 if g.votes.sum()!=d.loc[ac,'votes_polled_2021']:bad.append((ac,int(g.votes.sum()),int(d.loc[ac,'votes_polled_2021'])))
pd.DataFrame(bad).to_csv('work/parse2021_errors.csv',index=False)
print('2021 parse gaps',bad)
# Primary machine-readable report cross-checks the archived PDF; use full candidate names.
x=sheets(R/'eci2021_10.xlsx')[0];x.columns=x.iloc[3];x=x.iloc[4:];x=x[pd.to_numeric(x['AC NO.'],errors='coerce').notna()]
x=x.rename(columns={'AC NO.':'ac_no','CANDIDATE NAME':'candidate','PARTY':'party','TOTAL':'votes'})
x['candidate']=x.candidate.str.replace(r'^\d+\s+','',regex=True);x['ac_no']=x.ac_no.astype(int);x['votes']=pd.to_numeric(x.votes)
assert x.groupby('ac_no').votes.sum().sort_index().equals(c21.groupby('ac_no').votes.sum().sort_index())
c21=x[['ac_no','candidate','party','votes']].copy()
for s in sheets(R/'eci2021_8.xlsx'):
 ac=int(re.match(r'(\d+)-',s.iloc[1,3])[1]);d.loc[ac,'votes_polled_2021']=int(s.loc[s[1]=='5. Total',5].iloc[0]);d.loc[ac,'turnout_2021']=float(s.loc[s[0]=='III. Polling Percentage',5].iloc[0])
def summarize(c,year):
 rows=[]
 for ac,g in c.groupby('ac_no'):
  g=g.sort_values('votes',ascending=False); candidates=g[g.party!='NOTA']; w,r=candidates.iloc[0],candidates.iloc[1];den=g.votes.sum()
  z={'ac_no':int(ac),f'winner_{year}':w.candidate,f'winner_party_{year}':w.party,f'winner_votes_{year}':w.votes,f'winner_share_{year}':100*w.votes/den,f'runnerup_{year}':r.candidate,f'runnerup_party_{year}':r.party,f'runnerup_votes_{year}':r.votes,f'margin_{year}':w.votes-r.votes,f'valid_plus_nota_{year}':den}
  for p in ['TVK','DMK','ADMK','NOTA','MNM','NTK']:
   v=g.loc[g.party==p,'votes'].sum();z[f'{p.lower()}_votes_{year}']=v;z[f'{p.lower()}_share_{year}']=100*v/den
  for label,parties in [('dmk_alliance',['DMK','INC','CPI','CPM','CPI(M)','VCK','IUML']+(['DMDK'] if year==2026 else [])),('admk_alliance',['ADMK','BJP','PMK']+(['AMMKMNKZ'] if year==2026 else []))]:
   v=g.loc[g.party.isin(parties),'votes'].sum();z[f'{label}_votes_{year}']=v;z[f'{label}_share_{year}']=100*v/den
  rows.append(z)
 return pd.DataFrame(rows).set_index('ac_no')
d=d.join(summarize(c21,2021)).join(summarize(c26,2026))
v=pd.read_excel(R/'eci2026_12.xlsx',header=None);v=v[pd.to_numeric(v[0],errors='coerce').between(1,234)].set_index(0)
for col,j in [('electorate_2026',5),('votes_polled_2026',13),('turnout_2026',15),('postal_rejected_2026',16),('evm_excluded_2026',17)]:d[col]=pd.to_numeric(v[j])
d['turnout_change']=d.turnout_2026-d.turnout_2021
d['dmk_alliance_share_change']=d.dmk_alliance_share_2026-d.dmk_alliance_share_2021
d['tvk_win']=(d.winner_party_2026=='TVK').astype(int)
d['chennai']=(d.district=='Chennai').astype(int)
d['female_pct_apr']=100*d.apr_female/d.apr_electorate
d['margin_pct_2021']=100*d.margin_2021/d.valid_plus_nota_2021
d['log_pre_electorate']=np.log(d.pre_sir_electorate_reconstructed)
d['pre_sir_growth_from_2021_pct']=100*(d.pre_sir_electorate_reconstructed/d.electorate_2021-1)
d['party_control_changed']=(d.winner_party_2021!=d.winner_party_2026)
d['draft_deletion_margin_ratio']=d.draft_exclusions/d.margin_2026
d['net_reduction_margin_ratio']=d.net_reduction_apr/d.margin_2026
for k in [1,2,5,10]:d[f'draft_deletions_gt_{k}x_margin']=d.draft_exclusions>k*d.margin_2026
assert len(d)==234 and set(d.index)==set(range(1,235))
# Broad urban proxy: no village panchayat listed in the TNRD constituency crosswalk.
# Rural-containing is not equivalent to predominantly rural. Reference vintage unspecified.
norm=lambda s:re.sub('[^a-z]','',re.sub(r'\((SC|ST)\)','',str(s)).lower())
aliases={'gandharvakottai':'gandarvakkottai','pappireddippatti':'pappireddipatti','poonmallae':'poonamallee','sholingur':'sholinghur','villupuram':'viluppuram'}
lookup={norm(row.constituency):int(ac) for ac,row in d.iterrows()}
rr=pd.read_excel(R/'rural_ac.xlsx');cross=[]
for name,g in rr.groupby(rr.columns[2]):
 key=aliases.get(norm(name),norm(name));assert key in lookup,name
 cross.append({'tnrd_name':name,'ac_no':lookup[key],'listed_panchayat_rows':len(g)})
cross=pd.DataFrame(cross);cross.to_csv(O/'rural_crosswalk.csv',index=False)
d['listed_panchayat_rows']=d.index.map(cross.set_index('ac_no').listed_panchayat_rows).fillna(0).astype(int)
d['urban_proxy']=(d.listed_panchayat_rows==0).astype(int)
d['urban_rural_classification']=np.where(d.urban_proxy==1,'No listed village panchayat (urban proxy)','Contains listed village panchayats (rural/mixed)')
# Census 2011 old-district urban population; map successor districts to their parent.
import pdfplumber
pop=pdfplumber.open(R/'census_population.pdf').pages[2].extract_text();census={'Chennai':100.}
for line in pop.splitlines():
 m=re.match(r'^([A-Za-z ]+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)$',line)
 if m:census[m[1]]=100*int(m[5])/(int(m[2])+int(m[5]))
parent={'Chengalpattu':'Kancheepuram','Ranipet':'Vellore','Tirupathur':'Vellore','Kallakurichi':'Viluppuram','Tenkasi':'Tirunelveli','Mayiladuthurai':'Nagapattinam','Sivaganga':'Sivagangai'}
d['census_parent_district']=d.district.replace(parent);d['district_urban_pct_2011']=d.census_parent_district.map(census)
assert d.district_urban_pct_2011.notna().all()
d['comparable_ballot_turnout_change']=100*d.valid_plus_nota_2026/d.electorate_2026-100*d.valid_plus_nota_2021/d.electorate_2021
d['votes_polled_change_pct']=100*(d.votes_polled_2026/d.votes_polled_2021-1)
d['turnout_2026_pre_sir_denominator']=100*d.votes_polled_2026/d.pre_sir_electorate_reconstructed
d['turnout_denominator_component']=d.turnout_2026-d.turnout_2026_pre_sir_denominator
d['tvk_contested']=(d.tvk_votes_2026>0).astype(int)
d.index=d.index.astype(int);d=d.sort_index()
print('roll sums',d[['draft_electorate','feb_electorate','apr_electorate','draft_exclusions','pre_sir_electorate_reconstructed','net_reduction_apr']].sum().to_dict())
print('winners',d.winner_party_2026.value_counts().to_dict())
print('2021 winners',d.winner_party_2021.value_counts().to_dict())
print('2026 valid reconciliation',(d.valid_plus_nota_2026+d.postal_rejected_2026+d.evm_excluded_2026-d.votes_polled_2026).value_counts().to_dict())
d.to_csv(O/'constituency_master.csv');c21.to_csv(O/'candidates_2021.csv',index=False);c26.to_csv(O/'candidates_2026.csv',index=False)
