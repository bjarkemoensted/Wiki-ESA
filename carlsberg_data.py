# -*- coding: utf-8 -*-
'''Uses ESA to determine most probable topis for tweets contained in 
input file'''

from __future__ import division

import json
from dateutil.parser import parse
from cunning_linguistics import SemanticAnalyser

def percentof(small, large):
    return str(100*small/large) + "%"

#Get canonical date string
def timeparse(string):
    dt = parse(string)
    (y,m,d) = (str(dt.year), str(dt.month).zfill(2), str(dt.day).zfill(2))
    return "%s-%s-%s" % (y,m,d)

def main():
    #Make an analyser
    sa = SemanticAnalyser()
    sa.display_concepts = 10  #Number of concepts to keep
    #Read raw data
    with open('carlsberg_filtered_tweets.txt', 'r') as f:
        raw = f.readlines()
    
    count = 0
    results = []
    for tweet in raw:
        temp = {}
        data = json.loads(tweet)
        temp['time'] = timeparse(data['created_at'])
        temp['rt'] = data['retweeted']
        temp['scores'] = sa.interpret_text(data['text'])
        results.append(json.dumps(temp)+"\n")
        count += 1
        if count % 1000 == 0:
            print "Processed %s of %s tweets." % (count, len(raw)),
            print percentof(count, len(raw))
        
    with open('carlsberg_data.json','w') as outfile:
        outfile.writelines(results)

    
if __name__ == '__main__':
    main()