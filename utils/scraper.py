from bs4 import BeautifulSoup
import urllib.request

from pprint import pprint

from collections import OrderedDict

from datetime import datetime, date

import pandas as pd

db = '35.243.242.247'

from sqlalchemy import create_engine
engine = create_engine('postgresql://felipe:columbiaviz@%s:5432/gradcafe' % db )



#%%


baseUrl ="https://www.thegradcafe.com/survey/index.php?q=Computer+Science&t=a&pp=250&o=&p="

def getPageUrl(inx):
    return baseUrl + str(inx)

for page_inx in range(1,81):
    pageUrl = getPageUrl(page_inx)
    page = urllib.request.urlopen(pageUrl)
    soup = BeautifulSoup(page, 'html.parser')
    
    
    
    table_search = soup.find_all(
            lambda tag: tag.name == 'table' and 
            tag.get('class') == ['submission-table']
        )
    
    table = table_search[0]
    
    rows = table.find_all('tr', recursive=False)
    
    i=0
    
    entries = []
    
    for row in rows:
    #    if i < 3:
    #        i+=1
    #        continue
        
        i+=1
    #    print(i)
        children = list(row.children)
        
#        print(children)
        
        thirdCol = list(children[2].children)
        
        thirdColSplit = children[2].text.split()
        
        if thirdColSplit[0] not in ('Accepted', 'Rejected'):
            continue
        
#        print(thirdColSplit)
        
        if thirdColSplit[4] == 'on':
            del thirdColSplit[4]
            
        dateStr = ' '.join(thirdColSplit[4:7])
        
        try:
            isoDate = datetime.strptime(dateStr, '%d %b %Y').date().isoformat()
        except:
            isoDate = None
        
        scores = thirdCol[2].contents[0] if len(thirdCol) > 2 else None
        
        
        ugpa = scores.contents[1][2:] if scores else None
        ugpa = float(ugpa) if ugpa and ugpa != 'n/a' else None
        
    #    greStr = scores.contents[4][2:].split('/') if scores else (None, None, None)
        
        greStr = scores.text.split('(V/Q/W): ')[1][:12].split('/') if scores else (None, None, None)
        
    #    print(scores.text if scores else None)
        
        v = int(greStr[0]) if greStr[0] else None
        q = int(greStr[1]) if greStr[1] else None
        w = float(greStr[2][:4]) if greStr[2] else None
        
        status = children[3].text.strip()
        status = status if status != '' else None
        
        notes = children[5].text
        notes = notes if notes != '' else None
        
        
        
        entry = OrderedDict(
            institution=children[0].text,
            program=children[1].text,
            decision=thirdColSplit[0],
            date=isoDate,
            gpa=ugpa,
            v=v,
            q=q,
            w=w,
            status=status,
            notes=notes
            
            )
        
        entries.append(entry)
        
    print(page_inx)    
    df = pd.DataFrame(entries)
#    df.to_sql('scraped', engine, if_exists='append', index=False)
    print(page_inx)
    
#    break
        
        
    
