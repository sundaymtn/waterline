# import plotly
# plotly.tools.set_credentials_file(username='sundaymtn', api_key='kfw4lbn1wt', stream_ids=['vk5teiulzq', '7ksku8wn17'])

import plotly.plotly as py
from plotly.graph_objs import *

histFlow = {'Sep 10 2014 16:40:08': [u'Until MIDNIGHT Thu SEP 11, 1,400',
                                     u'At 4:25 PM today the total flow below the dam was 1395'],
            'Sep 11 2014 08:50:05': [u'Until MIDNIGHT today, Thu, 1,400',
                                     u'At 8:45 AM today the total flow below the dam was 1395']
            }

data = Data()
for flowDate, flowData in histFlow.iteritems():
    x = []
    y = []
    x.append(flowDate)
    for fD in flowData:
        if fD.startswith('At'):
            y.append(fD.split(' ')[-1])
    print x
    print y
    current = Scatter(name = 'current',x = x, y = y)
    print current
    data += Data([current])


unique_url = py.plot(data, filename = 'basic-line')
