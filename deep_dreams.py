# -*- coding: utf-8 -*-
from __future__ import division

from cunning_linguistics import SemanticAnalyser
import datetime
from dateutil.parser import parse
import json
from matplotlib import pylab as plt
import numpy as np
import pytz
import datetime
import sys
import glob
import time
import multiprocessing


REFERENCE = 'reference_google.txt'
PUBLISHED = datetime.datetime(2015, 06, 17)  #Date ref was published
WIDTH = 6  #Number of days to include around pub date
OUTPUT_FILENAME = 'deep_dreams.txt'
KEYWORD = 'google'

#15-06-17
with open(REFERENCE, 'r') as f:
    reference_text = f.read()

now = time.time()

epoch = datetime.datetime(1970,1,1, tzinfo = pytz.utc)
def dt2epoch(dt):
    utc_date = dt.astimezone(pytz.utc)
    delta = utc_date - epoch
    return delta.total_seconds()

def percentof(small, large):
    return str(100*small/large) + "%"

#Get canonical date string
def timeparse(string):
    dt = parse(string)
    (y,m,d) = (str(dt.year), str(dt.month).zfill(2), str(dt.day).zfill(2))
    return "%s-%s-%s" % (y,m,d)

filelist = set([])
for w in np.arange(-WIDTH, WIDTH+1, 1):
    delta = datetime.timedelta(days = w)
    dt = PUBLISHED + delta
    prefix = dt.strftime("%Y-%m-%d")
    pattern = 'tweets/' + prefix + '-data*'
    filelist.update((glob.glob(pattern)))

filelist = list(filelist)

#Make an analyser
sa = SemanticAnalyser()
#Read raw data
with open(REFERENCE, 'r') as f:
    reference_vector = sa.interpretation_vector(f.read())


def worker(filename):
    pass  #update!!!

Y = []
X = []
#required entries in tweets
ineedthese = ['lang', 'text', 'created_at']
#GO!
for filename in filelist:
    with open(filename, 'r') as f:
        tweets = [json.loads(line) for line in f.readlines()]
    for tweet in tweets:
        if not all(stuff in tweet.keys() for stuff in ineedthese):
            continue
        if not tweet['lang'] == 'en':
            continue
        text = tweet['text'].lower()
        if not KEYWORD in text:
            continue
        t = dt2epoch(parse(tweet['created_at']))
        this_vector = sa.interpretation_vector(text)
        similarity = sa.scalar(this_vector, reference_vector)
        if np.isnan(similarity):
            continue
        X.append(t)
        Y.append(similarity)
    #

inds = np.argsort(X)
X = [X[i] for i in inds]
Y = [Y[i] for i in inds]
#    plt.plot(X, Y)
#    plt.show()
