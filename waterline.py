from bs4 import BeautifulSoup
import urllib2
import redis
import re
import datetime
import time
import pickle
import plotly.plotly as py
from plotly.graph_objs import Data, Scatter 
import process
import sys

poll = False
log = True
plot = True
push = False

serverStart = process.ProcessClass(exec_list=([r'redis-server', './redis.conf'],), out=True, limit_response=0, errors_expected=False,
                           return_proc=True, use_call=False, use_shell=False, environ=None)
print "Starting Redis"
serverStart.execute()

r = redis.StrictRedis(host = 'localhost', port = 6379, db = 0)
def set_value(redis, key, value):
    redis.set(key, pickle.dumps(value))

def get_value(redis, key):
    pickled_value = redis.get(key)
    if pickled_value is None:
        return None
    return pickle.loads(pickled_value)


siteKeys = ['335124','335125','335126',]
location = {}


#r.flushdb()


for siteKey in siteKeys:
    if poll:
        print 'http://www.h2oline.com/default.aspx?pg=si&op=%s' % siteKey
        response = urllib2.urlopen('http://www.h2oline.com/default.aspx?pg=si&op=%s' % siteKey)
        html = response.read()
        r.set(siteKey, html)
        time.sleep(5)
    cfs = get_value(r, siteKey + '-cfs')
    if not cfs:
        cfs = {}
    soup = BeautifulSoup(r.get(siteKey))
    locationSpan = soup.span(id = 'PPStyle3-C')
    try:
        location[siteKey] = locationSpan[0].get_text().split(siteKey)[1].lstrip()
    except:
        print siteKey,locationSpan,cfs
        
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
    
    
def parseFlow(flowData):
    flowMatches = [#'Until (?:(\d{1,2}:\d{1,2} (?:AM|PM)|MIDNIGHT)) (today|tomorrow). (\d\,\d{1,6}|\d{1,6})',
                   'At (?:(\d{1,2}:\d{1,2} (?:AM|PM)|MIDNIGHT)) (today|tomorrow) the total flow below the dam was (\d\,\d{1,6}|\d{1,6})',
                   'From (?:(\d{1,2}:\d{1,2} (?:AM|PM)|MIDNIGHT)) (today|tomorrow) until (?:(\d{1,2}:\d{1,2} (?:AM|PM)|MIDNIGHT)) (\d\,\d{1,6}|\d{1,6})',
                   'From (?:(\d{1,2}:\d{1,2} (?:AM|PM)|MIDNIGHT)) (today|tomorrow) until (?:(\d{1,2}:\d{1,2} (?:AM|PM)|MIDNIGHT)) (?:(today|tomorrow).*) (\d\,\d{1,6}|\d{1,6})']
    for f in flowMatches:
        m = re.match(f,flowData)
        if m:
            # print m.groups()
            return m.groups()

def convertTimes(flowDate, fDList):
    fdList = ['11:59 PM' if f=='MIDNIGHT' else f for f in fDList]
    # print fdList
    fdList = [datetime.datetime.strptime(f, "%I:%M %p") if ':' in f else f for f in fdList]
    for x in xrange(len(fdList)):
        if type(fdList[x]) == datetime.datetime:
            if fdList[x+1]=='tomorrow':
                fdList[x] = fdList[x].replace(year=flowDate.year, month=flowDate.month, day=flowDate.day+1)
            else:
                fdList[x] = fdList[x].replace(year=flowDate.year, month=flowDate.month, day=flowDate.day)
    fdList = [f for f in fdList if f not in ('today','tomorrow')]
    print '\t '+str(fdList)
    return fdList


flowList = []
for siteKey in siteKeys:
    damName = location[siteKey].split('AT')[1].lstrip()
    if log:
        print siteKey, damName
    histFlow = get_value(r, siteKey + '-cfs')
    xActualDate = []
    yActualFlow = []
    xExpectedDate = []
    yExpectedFlow = []
    sortedDates = histFlow.keys()
    sortedDates.sort()
    datePoints = len(sortedDates)
    for datePoint in xrange(datePoints):
        flowDate = sortedDates[datePoint]
        flowData = histFlow[flowDate]
        if log:
            print '\n\t'+flowDate.strftime('%b %d %Y %H:%M:%S')
        
        for fD in flowData:
            tomorrow = False
            fDList = parseFlow(fD)
            if log:
                print '\t  ' + fD
            if fDList:
                datesAndFlows = convertTimes(flowDate, fDList)
                if len(datesAndFlows) == 2:
                    yActualFlow.append(datesAndFlows[-1])
                    xActualDate.append(datesAndFlows[0])
                else:
                    for dF in datesAndFlows[0:-1]:
                        yExpectedFlow.append(datesAndFlows[-1])
                        xExpectedDate.append(dF)
    
    flowList += [Scatter(name = damName+'-expected' ,x = xExpectedDate, y = yExpectedFlow, fill ="none", line={"dash":"dot"})]
                
    flowList += [Scatter(name = damName ,x = xActualDate, y = yActualFlow, fill ="tozeroy")]
    
data = Data(flowList)
riverName = damName = location[siteKey].split('AT')[0].rstrip()

if plot:
    py.sign_in('sundaymtn','kfw4lbn1wt')
    unique_url = py.plot(data, filename = riverName+'-test', auto_open=False, overwrite=True)

serverStop = process.ProcessClass(exec_list=([r'redis-cli', 'shutdown'],), out=True, limit_response=0, errors_expected=False,
                           return_proc=False, use_call=False, use_shell=False, environ=None)
print "Stopping Redis"
serverStart.execute()


addUpdatedDb = process.ProcessClass(exec_list=([r'git remote set-url origin https://sundaymtn:669288a22a7ba23a44fc088f9442deb5b299a03e@github.com/sundaymtn/waterline.git'],
                                               [r'git config user.email "sundaymtn@gmail.com"'],
                                               [r'git config user.name "Seth Carter"'],
                                               [r'git status'],
                                               [r'git checkout master'],
                                               [r'git branch --set-upstream master origin/master'],
                                               [r'git add waterline.rdb'],
                                               [r'git commit -m "[skip ci] updated waterline data"'],
                                               [r'git push']), out=True, limit_response=0, errors_expected=False,
                           return_proc=False, use_call=False, use_shell=True, environ=None)
if push:
    print 'Pushing updated redis db to remote'
    ret = addUpdatedDb.execute()
    for line in ret:
        print '\t'+line



