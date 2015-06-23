# -*- coding: utf-8 -*-
'''Parameters to be shared between scripts. Always import from here.'''

from __future__ import division
import cPickle as pickle
import numpy as np
import pprint
import heapq
import matplotlib.pyplot as plt
from operator import add

def dict_nlargest(d,n):
    return heapq.nlargest(n ,d, key = lambda k: d[k])


def date2string(dtobj):
    return str(dtobj)[:10]

def getcolor():
    cols = ['b','g','r','c','m','y','k','w']
    ind = 0
    while True:
        yield cols[ind]
        ind = 0 if ind >= len(cols)-1 else ind+1

if __name__ == '__main__':
    pp = pprint.PrettyPrinter(indent=2)
    with open('results.p','r') as f:
        raw = pickle.load(f)
    
    
    #get top scoring concepts
    n = 5
    totals = {}
    times = []
    for t in raw:
        s = date2string(t['created_at'])
        if not s in times:
            times.append(s)
        for k, v in t['scores'].iteritems():
            try:
                totals[k] += v
            except KeyError:
                totals[k] = v
    
    top_concepts = dict_nlargest(totals, n)
    c2i = {n:m for m,n in enumerate(top_concepts)}
#    i2c = {n:m for m,n in c2i}
    times.sort()
    time2index = {n:m for m,n in enumerate(times)}
        
    


    datalist = []
    for _ in xrange(len(top_concepts)):
        datalist.append(len(times)*[0])
    #i, j = concept, date
    for t in raw:
        date = date2string(t['created_at'])
        j = time2index[date]
        for c in top_concepts:
            i = c2i[c] #duh
            
            try:
                datalist[i][j] += t['scores'][c]
            except KeyError:
                pass #no score = 0
    

    test = [100,100,100,100]
    ind = np.arange(len(times))    # the x locations for the groups
    width = 0.35       # the width of the bars: can also be len(x) sequence
    
    plotlist = []
    #Bottom to stack each concepts bar on top of.
    bottom = len(times)*[0] 
    #color generator. Bam!
    colgen = getcolor()       
    for concept_data in datalist:
        plotlist.append(plt.bar(ind, concept_data, width, bottom = bottom, color=colgen.next()))
        #raise bottom
        bottom = map(add, bottom, concept_data)
    
    
#    p1 = plt.bar(ind, menMeans,   width)
#    p2 = plt.bar(ind, womenMeans, width, bottom=menMeans, color='g')
#    p3 = plt.bar(ind, test, width, bottom=map(add,menMeans,womenMeans), color = 'r')
    
    labels = tuple(times)    
    noideabutpyplotneedsthis = tuple([p[0] for p in plotlist])    
    
    #I'm sorry...
    ymax = max([sum([row[j] for row in datalist]) for j in xrange(len(datalist[0]))])

    
    plt.ylabel('Total TF-IDF')
    plt.title('Supercool Twitter stuff!!1')
    plt.xticks(ind+width/2., labels)
    plt.yticks(np.arange(0,ymax,int(ymax/20)))
    plt.legend( noideabutpyplotneedsthis, top_concepts )
    


#N = 5
#menMeans   = (20, 35, 30, 35, 27)
#womenMeans = (25, 32, 34, 20, 25)
#menStd     = (2, 3, 4, 1, 2)
#womenStd   = (3, 5, 2, 3, 3)
#ind = np.arange(N)    # the x locations for the groups
#width = 0.35       # the width of the bars: can also be len(x) sequence
#
#p1 = plt.bar(ind, menMeans,   width, color='r', yerr=womenStd)
#p2 = plt.bar(ind, womenMeans, width, color='y',
#             bottom=menMeans, yerr=menStd)
#
#plt.ylabel('Scores')
#plt.title('Scores by group and gender')
#plt.xticks(ind+width/2., ('G1', 'G2', 'G3', 'G4', 'G5') )
#plt.yticks(np.arange(0,81,10))
#plt.legend( (p1[0], p2[0]), ('Men', 'Women') )
#
#plt.show()