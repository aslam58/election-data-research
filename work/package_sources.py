import json,hashlib,re,pandas as pd
from pathlib import Path
from lxml import html
R=Path('work/raw');O=Path('outputs');rows=[]
def add(file,url,role):
 p=R/file
 rows.append(dict(file='work/raw/'+file,url=url,role=role,accessed='2026-10-06',sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else '',bytes=p.stat().st_size if p.exists() else 0))
for p in R.glob('*.aspx.html'):add(p.name,'https://www.elections.tn.gov.in/'+p.name[:-5],'CEO official roll or source catalogue')
add('ceosir.html','https://www.elections.tn.gov.in/SIR_2026.aspx','Official SIR source catalogue')
add('asdportal.html','https://erolls.tn.gov.in/asd','Official public booth ASD portal; CAPTCHA and old/new part crosswalk required')
add('eci2026links_correct.json','https://www.eci.gov.in/eci-backend/public/api/election-result?category_id=26','2026 official catalogue')
add('eci2021links.json','https://www.eci.gov.in/eci-backend/public/api/old-site-statistical-report-data?docid=13680','2021 official catalogue')
for a in json.load(open(R/'eci2026links_correct.json'))['results']:
 num=re.match(r'(\d+)',a['title'])[1];f='eci2026_'+num+'.xlsx'
 if (R/f).exists():add(f,a['xlsx_url'],'ECI 2026 statistical report '+num)
 if num=='10':add('results2026.pdf',a['pdf_zip_url'],'ECI 2026 detailed results PDF')
for a in json.load(open(R/'eci2021links.json'))['results']['data'][0]['document_attach']:
 name=a['record_realname'];m=re.match(r'(\d+)',name)
 if m and name.endswith('.xlsx') and (R/('eci2021_'+m[1]+'.xlsx')).exists():add('eci2021_'+m[1]+'.xlsx',a['record_location'],'ECI 2021 statistical report '+m[1])
add('results2021.pdf','https://archive.org/download/httpseci.gov.infilesfile13680-tamil-nadu-general-legislative-election-2021/10-%20Detailed%20Results.pdf','Archived ECI report; aggregate candidate votes cross-checked against primary XLSX')
add('form20_2021_ac001.pdf','https://www.elections.tn.gov.in/Form20_TNLA2021/dt1/AC001.pdf','Official 2021 booth Form20 sample; no booth regression estimated')
add('rural_ac.xlsx','https://tnrd.tn.gov.in/databases/ac_pc/List%20of%20Rural%20Assembly%20Constituency%20in%20Village%20Panchayats.xlsx','Official panchayat-AC crosswalk; reference vintage unspecified')
add('census_population.pdf','https://des.tn.gov.in/sites/default/files/2024-11/01%20areaandpopulation.pdf','Official DES Census2011 district rural/urban population, PDF page3')
add('tn.geojson','https://raw.githubusercontent.com/baskicanvas/tamilnadu-assembly-constituency-maps/master/tn_ac_2021.geojson','Third-party illustrative boundary map, 234 ACs; approximate area/centres')
add('opencity.json','https://data.opencity.in/api/3/action/package_show?id=tamil-nadu-sir-voter-rolls-2026','OpenCity resource catalogue; filenames and origins audited')
for a in json.load(open(R/'opencity.json'))['result']['resources']:
 f=a['url'].split('/')[-1]
 if (R/f).exists():add(f,a['url'],'OpenCity secondary transcription of official data; independent transcription check only')
pd.DataFrame(rows).drop_duplicates('file').to_csv(O/'source_registry.csv',index=False)
# Inventory of publicly linked Form20s, without falsely implying all PDFs were downloaded.
t=html.parse(str(R/'Form20_TNLA2021.aspx.html'));a=[dict(label=x.text_content().strip(),url='https://www.elections.tn.gov.in/'+x.get('href'),downloaded=x.get('href').endswith('AC001.pdf')) for x in t.xpath('//a') if 'Form20_TNLA2021/' in str(x.get('href'))];pd.DataFrame(a).to_csv(O/'form20_2021_source_inventory.csv',index=False)
# Re-runable data validation.
d=pd.read_csv(O/'constituency_master.csv').set_index('ac_no');checks=[]
for f,p in [('tn_elector_rolls_19022025.csv','draft'),('tn-rolls-feb2026.csv','feb'),('tn_acwise_gendercount.csv','apr')]:
 a=pd.read_csv(R/f);a=a[pd.to_numeric(a['Sl No.'] if p=='apr' else a['AC No.'],errors='coerce').notna()].copy();a.index=a['AC No.'].astype(int);a=a.sort_index()
 for c,g in [('Male','male'),('Female','female'),('Third Gender','third')]:
  assert (pd.to_numeric(a[c])==d[p+'_'+g]).all();checks.append(dict(check=f'{p} {g}: CEO vs OpenCity',n=234,result='PASS'))
b=pd.read_csv(O/'tables/net_bands.csv')
assert b.n.tolist()==[19,80,66,37,22,10]
assert b.tvk_wins.tolist()==[2,22,32,24,18,10]
assert b.dmk_wins.tolist()==[7,20,21,8,3,0]
assert b.admk_wins.tolist()==[6,24,11,5,1,0]
assert b.other_party_wins.tolist()==[4,14,2,0,0,0]
assert len(d)==234 and set(d.index)==set(range(1,235))
assert (d.deceased+d.shifted_absent+d.duplicate==d.draft_exclusions).all()
assert (d.draft_exclusions-d.net_rebound_draft_apr==d.net_reduction_apr).all()
assert (d.valid_plus_nota_2026+d.postal_rejected_2026+d.evm_excluded_2026==d.votes_polled_2026).all()
checks.extend([dict(check='234 unique consecutive AC identifiers',n=234,result='PASS'),dict(check='2021 primary XLSX vs archived PDF candidate-total reconciliation',n=234,result='PASS'),dict(check='2026 candidate+NOTA+postal rejects+excluded EVM=ballots',n=234,result='PASS'),dict(check='Draft reasons sum to draft exclusions',n=234,result='PASS'),dict(check='Draft exclusions minus draft-April rebound equals April net reduction',n=234,result='PASS'),dict(check='BusinessLine six bands n/TVK/DMK/ADMK/Other exact reproduction',n=6,result='PASS')])
pd.DataFrame(checks).to_csv(O/'validation_log.csv',index=False)
# Dictionary: one row per master variable, including missingness and measurement provenance.
manual={
'ac_no':('Official Assembly constituency number; unique join key, 1–234','CEO/ECI','identifier'),
'district':('CEO draft-roll district; contemporary administrative district','CEO draft','text'),
'constituency':('CEO constituency label; numbers disambiguate repeated names','CEO draft','text'),
'pre_sir_electorate_reconstructed':('Draft electorate + draft exclusions. Reconstructed pre-SIR general electorate; not January2025 roll','CEO draft + ASD','electors'),
'draft_exclusions':('December19 draft omissions: deceased + shifted/absent + multiple-enrolment entries. NOT full-period gross removals or eligible persons still excluded in April','CEO ACwise_ASD','entries'),
'deceased':('Draft excluded entries administratively labelled deceased; classification not individually validated','CEO ACwise_ASD','entries'),
'shifted_absent':('Draft excluded entries jointly labelled shifted/absent; permanently shifted and absent cannot be separated','CEO ACwise_ASD','entries'),
'duplicate':('Draft entries labelled enrolled at multiple places; not distinct disenfranchised citizens','CEO ACwise_ASD','entries'),
'net_reduction_apr':('Reconstructed pre-SIR electorate minus April6 general roll; BusinessLine exposure','CEO derived','electors'),
'net_reduction_feb':('Reconstructed pre-SIR electorate minus February23 final roll','CEO derived','electors'),
'net_change_apr':('April6 general roll minus reconstructed pre-SIR; negative means decrease','CEO derived','electors'),
'net_rebound_draft_apr':('April6 minus December19 draft; net post-draft recovery, NOT gross additions or identified restorations','CEO derived','electors'),
'draft_exclusion_pct':('100 × draft exclusions / reconstructed pre-SIR electorate','CEO derived','percent'),
'net_reduction_pct':('100 × April net reduction / reconstructed pre-SIR electorate','CEO derived','percent'),
'net_rebound_pct':('100 × draft-April net rebound / reconstructed pre-SIR electorate','CEO derived','percent'),
'urban_proxy':('1 if AC absent from TNRD village-panchayat crosswalk, else0. Proxy only; 0 includes suburban/mixed ACs','TNRD','binary'),
'urban_rural_classification':('No listed panchayat (urban proxy) or contains panchayats (rural/mixed); not official Census AC classification','TNRD','text'),
'listed_panchayat_rows':('Number of listed village-panchayat records mapped to AC; vintage unspecified','TNRD','rows'),
'census_parent_district':('2011 district geography assigned to present successor district; approximate harmonisation','CEO + DES','text'),
'district_urban_pct_2011':('100 × district urban population / district total population in2011; contextual proxy, not AC urban share','DES Census2011 PDF page3','percent'),
'area_km2_approx':('Approximate polygon area: lon×111.32×cos(mean latitude), lat×110.574; exterior minus holes. Third-party boundaries','Baskicanvas/DataMeet derived','km2'),
'longitude':('Mean exterior-ring vertex longitude; approximate spatial location, not population centroid','Map derived','degrees'),
'latitude':('Mean exterior-ring vertex latitude; approximate spatial location, not population centroid','Map derived','degrees'),
'log_elector_density':('Natural log(pre-SIR electorate / approximate polygon area)','CEO + map derived','log electors/km2'),
'log_pre_electorate':('Natural log reconstructed pre-SIR electorate','CEO derived','log electors'),
'pre_sir_growth_from_2021_pct':('100 × (pre-SIR / ECI2021 electorate −1); population/enrolment/mobility proxy, NOT measured migration. Different service-elector coverage','CEO/ECI derived','percent'),
'chennai':('1 if CEO district is Chennai,16 ACs; excludes suburbs in other districts','CEO','binary'),
'female_pct_apr':('100 × female electorate / April general electorate; post-revision composition sensitivity, excluded from strict models','CEO derived','percent'),
'party_control_changed':('Registered winning party2026 differs from winning party2021; not alliance change or by-election-adjusted incumbency','ECI derived','binary'),
'previous_party_group':('2021 registered winning party: DMK,ADMK,INC,BJP,other','ECI derived','category'),
'winner_alliance_2026':('Pre-election alliance based on registered party: TVK; DMK+ includesDMK INC CPI CPI(M) VCK IUML DMDK; AIADMK+ includesADMK BJP PMK AMMKMNKZ','ECI party labels + coalition mapping','category'),
'flip_burden':('(2026 margin+1)/draft exclusions; minimum net extra runner-up votes per draft-excluded entry for strict win','derived counterfactual','fraction'),
'potentially_outcome_sensitive':('flip_burden <=0.10; scenario-screen equivalent to q=.5,t=.5,p=.7 in two-candidate allocation, ignoring integer rounding','scenario assumption','binary'),
'sensitivity_class':('Burden<=.025 highly sensitive;(.025,.10] plausibly scenario-sensitive;(.10,.75] demanding;>.75 impossible within t<=.75 andq<=1. Labels NOT estimated probabilities','scenario assumption','category'),
'minimum_q_at_t70_p60':('(margin+1)/(draft exclusions×.7×.2); q eligibility/still-excluded fraction required at70% turnout,60:40 runner-up:winner','scenario assumption','fraction; >1 infeasible'),
'minimum_q_at_t70_p70':('(margin+1)/(draft exclusions×.7×.4); at70% turnout,70:30 split','scenario assumption','fraction; >1 infeasible'),
'draft_deletion_margin_ratio':('Draft exclusions /2026 winner-minus-runnerup margin','CEO/ECI derived','ratio'),
'net_reduction_margin_ratio':('April net reduction /2026 margin; sensitivity comparator, not person count','CEO/ECI derived','ratio'),
'dmk_alliance_share_change':('2026 pre-election DMK-alliance share minus2021 DMK-alliance share; DMDK enters in2026, so composition changes','ECI derived','percentage points'),
'dmk_core_share_change':('Same as alliance change after subtracting2026 DMDK share. Artificial fixed-label comparator; contested seats differ','ECI derived','percentage points'),
'dmdk_share_2026':('Registered DMDK candidate votes /valid+NOTA×100; zero where absent','ECI2026 report10','percent'),
'margin_pct_2021':('2021 winning vote margin /valid+NOTA×100','ECI2021 report10','percentage points'),
'comparable_ballot_turnout_change':('100×valid+NOTA2026/electorate2026 −100×valid+NOTA2021/electorate2021; alternate same-ballot numerator','ECI derived','percentage points'),
'votes_polled_change_pct':('100×(votes polled2026/votes polled2021−1)','ECI derived','percent'),
' turn':''}
rows=[]
for col in d.reset_index().columns:
 if col in manual and isinstance(manual[col],tuple):desc,src,unit=manual[col]
 elif col.startswith(('gross_','pre_sir_male','pre_sir_female','pre_sir_third','change_pre_sir_','documentation_','other_reason_')):desc='Unavailable in assembled AC-level sources; blank means unknown, never zero';src='Not available';unit='percent' if 'rate' in col else 'electors/entries'
 elif re.match(r'(draft|feb|apr|jan2025)_(male|female|third|electorate)$',col):
  stage,g=col.split('_',1);desc={'draft':'December19 2025 draft','feb':'February23 2026 final','apr':'April6 2026 last nomination date general roll','jan2025':'January6 2025 roll; NOT pre-SIR baseline'}[stage]+'; '+g;src='CEO ACwise_Gendercount';unit='electors'
 elif col.startswith('change_draft_apr_'):desc='April6 minus December19 draft by gender; net change, not gross additions';src='CEO derived';unit='electors'
 elif col in ['deceased_pct','shifted_absent_pct','duplicate_pct']:desc='100×category count / reconstructed pre-SIR electorate';src='CEO derived';unit='percent'
 elif col.startswith('draft_deletions_gt_'):desc='Draft exclusions strictly exceed '+col.split('_')[3]+' 2026 winning margin';src='derived';unit='binary'
 elif col.startswith('p_needed_q100_'):desc='(1+(margin+1)/(draft exclusions×turnout))/2, q=1, all remaining ballots winner; turnout encoded in suffix. >1 infeasible; continuous approximation';src='scenario assumption';unit='fraction'
 elif col in ['draft_band','net_band']:desc='Absolute count bands <=10000,<=20000,<=30000,<=50000,<=80000,>80000; draft exclusions or April net reduction';src='derived';unit='category'
 elif re.match(r'(draft|net)_(rank|q5|q10|20_60_20)',col):desc='AC rate ranking: rank1 highest; quintile/decile1 lowest; pandas qcut on first-tie ranks, AC order; bottom/top47 seats, middle140; deciles23/24';src='derived';unit='rank/group'
 elif col=='tvk_win':desc='2026 winning registered party isTVK';src='ECI derived';unit='binary'
 elif col=='tvk_contested':desc='TVK positive candidate votes,233 ACs; Edappadi=0';src='ECI report10';unit='binary'
 elif col=='turnout_change':desc='Reported ECI2026 turnout minus ECI2021 turnout; 2-decimal source precision';src='ECI2026 report12/2021 report8';unit='percentage points'
 elif col=='turnout_2026_pre_sir_denominator':desc='100×2026 ballots /pre-SIR general electorate; descriptive counter-denominator, not causal turnout';src='ECI/CEO derived';unit='percent'
 elif col=='turnout_denominator_component':desc='Reported2026 turnout minus turnout2026 usingpre-SIR denominator; service-elector universes differ';src='ECI/CEO derived';unit='percentage points'
 elif col.endswith(('_2021','_2026')):
  yr=col[-4:];k=col[:-5];src='ECI'+yr+' report10';unit='votes';desc=k.replace('_',' ')
  if k=='electorate':src='ECI'+yr+' report'+('10' if yr=='2021' else '12');unit='electors including service';desc='Election statistical-report electorate'
  elif k in ['votes_polled','turnout','postal_rejected','evm_excluded']:src='ECI'+yr+' report'+('8' if yr=='2021' else '12');desc={'votes_polled':'Total ballots cast including invalid/excluded where reported','turnout':'Reported turnout percentage','postal_rejected':'Rejected postal ballots','evm_excluded':'EVM votes excluded from counting'}[k];unit='percent' if k=='turnout' else 'votes'
  elif k.startswith(('winner_party','runnerup_party')):unit='party code';desc='Registered party, including allies using another party symbol under that symbol label'
  elif k in ['winner','runnerup']:unit='text';desc='Candidate name; NOTA excluded from winner/runner-up ranking'
  elif 'share' in k:unit='percent';desc=k.replace('_',' ')+' = corresponding votes /(all candidate votes+NOTA)×100; zero when party absent'
  elif k=='valid_plus_nota':desc='Sum all candidate votes plusNOTA; vote-share denominator, excludes rejected/excluded ballots'
  elif k=='margin':desc='Winner votes minus runner-up votes; positive winning margin'
  else:desc=k.replace('_',' ')+'; coalition mappings documented in report; absent party votes=0'
 else:desc=col.replace('_',' ');src='Derived; see reproducible code';unit='see name'
 rows.append(dict(variable=col,definition=desc,source=src,unit=unit,nonmissing=int(d.reset_index()[col].notna().sum()),missing=int(d.reset_index()[col].isna().sum())))
pd.DataFrame(rows).to_csv(O/'variable_dictionary.csv',index=False)
print('Registered',len(rows),'variables;',len(a),'Form20 links; source manifest saved')
