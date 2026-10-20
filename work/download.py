import json, pathlib, urllib.request, concurrent.futures
R=pathlib.Path('work/raw')
jobs=[]
j=json.loads((R/'eci2021links.json').read_text())
for a in j['results']['data'][0]['document_attach']:
    name=a['record_realname']
    if name.endswith('.xlsx') and name.split('-')[0].strip() in ['8','10','11','12','2']:
        jobs.append((a['record_location'],'eci2021_'+name.split('-')[0].strip()+'.xlsx'))
jobs.append(('https://www.eci.gov.in/eci-backend/public/all_files/election_report/General_Election_to_the_Legislative_Assembly_of_Tamil_Nadu_2026_2026/10-Detailed_Results_1778165153.xlsx','eci2026_10.xlsx'))
for p in ['CAO2026_7.aspx','ASD_19122025.aspx','Summary_Revision.aspx','Elections.aspx']:
    jobs.append(('https://www.elections.tn.gov.in/'+p,p+'.html'))
def run(j):
    url,name=j
    try:
        b=urllib.request.urlopen(url,timeout=45).read(); (R/name).write_bytes(b)
        return name,len(b)
    except Exception as e:return name,str(e)
if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:print(list(ex.map(run,jobs)))
    (R/'download_manifest.json').write_text(json.dumps(jobs,indent=2))
