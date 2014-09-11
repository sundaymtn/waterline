from bs4 import BeautifulSoup
import urllib2
import redis
import re
import datetime
import pickle
import plotly.plotly as py
from plotly.graph_objs import Data, Scatter 

r = redis.StrictRedis(host = 'localhost', port = 6379, db = 0)

def set_value(redis, key, value):
    redis.set(key, pickle.dumps(value))

def get_value(redis, key):
    pickled_value = redis.get(key)
    if pickled_value is None:
        return None
    return pickle.loads(pickled_value)


siteKeys = ['335122','335121','335123','335124', '335125', '335126']
location = {}


# r.flushdb()


for siteKey in siteKeys:
    response = urllib2.urlopen('http://www.h2oline.com/default.aspx?pg=si&op=%s' % siteKey)
    html = response.read()
    r.set(siteKey, html)
    cfs = get_value(r, siteKey + '-cfs')
    if not cfs:
        cfs = {}
    soup = BeautifulSoup(r.get(siteKey))
    locationSpan = soup.span(id = 'PPStyle3-C')
    try:
        location[siteKey] = locationSpan[0].get_text().split(siteKey)[1].lstrip()
    except:
        print siteKey,locationSpan,html
        
    timeSpan = soup.span(id = 'Footer-C')
    match = re.search(r'([A-Z]{3}).(\d{2}),.(\d{4}).AT.\d{2}:\d{2}:\d{2}', timeSpan[0].get_text().lstrip())
    if match:
        flowDateObj = datetime.datetime.strptime(match.group(0), "%b %d, %Y AT %H:%M:%S")
    flowDate = flowDateObj

    forecastSpan = soup.span(id = 'PPStyle4-P')

    flowData = forecastSpan[0].get_text().lstrip().rstrip().split(' CFS')
    flowData2 = [f.split(':  ')[1] for f in flowData if ': ' in f]
    for flow in flowData2:
        if flow not in flowData:
            flowData.insert(0,flow)
    for flow in flowData:
        if flow.startswith(('At', 'From', 'Until')):
            if cfs.has_key(flowDate):
                if not flow in cfs[flowDate]:
                    cfs[flowDate].append(flow)
            else:
                cfs[flowDate] = [flow,]
    set_value(r, siteKey + '-cfs', cfs)
    r.save()

flowList = []
for siteKey in siteKeys:
    damName = location[siteKey].split('AT')[1].lstrip()
    print siteKey, damName
    histFlow = get_value(r, siteKey + '-cfs')
    x = []
    y = []
    sortedDates = histFlow.keys()
    sortedDates.sort()

    for flowDate in sortedDates:
        flowData = histFlow[flowDate]
        
        print '\t'+flowDate.strftime('%b %d %Y %H:%M:%S')
        x.append(flowDate)
        for fD in flowData:
            print '\t  ' + fD
            if fD.startswith('At'):
                y.append(fD.split(' ')[-1])
    flowList += [Scatter(name = damName ,x = x, y = y, fill ="tozeroy")]
    
data = Data(flowList)
riverName = damName = location[siteKey].split('AT')[0].rstrip()
unique_url = py.plot(data, filename = riverName)






