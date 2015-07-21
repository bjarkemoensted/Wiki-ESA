# -*- coding: utf-8 -*-
'''Small module for computational linguistics applied to Twitter.
The main classes are a TweetHarvester, which gathers data from Twitters' API,
and a SemanticAnalyser, which relies on the previously constructed TFIDF 
matrices.'''

from __future__ import division
from scipy import sparse as sps
from collections import Counter
from numpy.linalg import norm
import re
import shared
import tweepy
from datetime import date
import json
import time
import sys
import codecs
from pprint import pprint
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

#==============================================================================
# This stuff defines a twitter 'harvester' for downloading Tweets
#==============================================================================

#Import credentials for accessing Twitter API
from supersecretstuff import consumer_key, consumer_secret, access_token, access_token_secret
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

class listener(tweepy.StreamListener):
    '''Listener class to access Twitter stream.'''
    #What to do with a tweet (override later)
    def process(self, content):
        print content
        return None
        
    def on_status(self, status):
        self.process(status)
        return True

    def on_error(self, status):
        print status

# Exception to be raised when the Twitter API messes up. Happens occasionally.
class IncompleteRead(Exception):
    pass

class TweetHarvester(object):
    '''Simple class to handle tweet harvest.
    Harvest can be performed actively or passively, i.e. using the 'mine' 
    method to gather a fixed number of tweets or using the 'listen' method
    to stream tweets matching a given search term.
    Harvested tweets are sent to the process method which by default simply
    stores them inside the object.'''
    
    def __init__(self, max_tweets=-1, verbose = False, tweets_pr_file = 10**5):
        #Set parameters
        self.max_tweets = max_tweets  #-1 for unlimited stream
        self.verbose = verbose
        self.tweets_pr_file = tweets_pr_file
        
        #Internal parameters to keep track of harvest status
        self.files_saved = 0
        self.harvested_tweets = []
        self.current_filenumber = 0
        self.current_date = date.today()
    
    def filename_maker(self):
        #Update counter and date if neccessary
        if not self.current_date == date.today():
            self.current_date = date.today()
            self.current_filenumber = 0
        else:
            pass  #Date hasn't changed. Proceed.
        filename = str(self.current_date) + "-data%s.json" % self.current_filenumber
        self.current_filenumber += 1
        return filename
        
    #Simple logging function
    def log(self, text):
        string = text+" at "+time.asctime()+"\n"
        if self.verbose:
            print string
        with open('tweetlog.log', 'a') as logfile:
            logfile.write(string)
        #Must return true so I can log errors without breaking the stream.
        return True

    def listen(self, search_term):
        #Make a listener
        listener = tweepy.StreamListener()
        #Override relevant methods.
        listener.on_status = self.process
        listener.on_error = lambda status_code: self.log("Error: "+status_code)
        listener.on_timeout = lambda: self.log("Timeout.")
        
        twitterStream = tweepy.Stream(auth, listener)
        twitterStream.filter(track=search_term)
        
    def mine(self, search_term, n = None):
        '''Mine a predefined number of tweets using input search word'''
        if n == None:
            n = self.max_tweets
            
        api = tweepy.API(auth)
        tweets = tweepy.Cursor(api.search, q=search_term).items(n)
        for tweet in tweets:
            self.process(tweet)
    
    def process(self, tweet):
        self.harvested_tweets.append(tweet)
        if self.verbose:
            print "Holding %s tweets." % len(self.harvested_tweets)
        
        #Write to file if buffer is full
        if len(self.harvested_tweets) == self.tweets_pr_file:
            self.writeout()

        #Check if limit has been reached (returning false cuts off listener)            
        return not (len(self.harvested_tweets) == self.max_tweets)
        
    def writeout(self):
        filename = self.filename_maker()
        with open(filename,'w') as outfile:
            outfile.writelines([json.dumps(t._json)+"\n" 
                            for t in self.harvested_tweets])
        
        self.harvested_tweets = []
        self.files_saved += 1
        #Log event
        s = "Saved %s files" % self.files_saved
        self.log(s)


#==============================================================================
# Defines stuff to analyse text using an already constructed interpretation
# matrix.
#==============================================================================

from shared import matrix_dir, row_chunk_size, extensions

class SemanticAnalyser(object):
    '''Analyser class using Explicit Semantic Analysis (ESA) to process 
    text fragments. It can compute semantic (pseudo) distance and similarity,
    as well'''
    def __init__(self, matrix_filename = 'matrix.mtx'):        
        #Hashes for word and concept indices
        with open(matrix_dir+'word2index.ind', 'r') as f:
            self.word2index = shared.load(f)
        with open(matrix_dir+'concept2index.ind', 'r') as f:
            self.concept2index = shared.load(f)
        self.index2concept = {i : c for c, i in self.concept2index.iteritems()}
        
        #Count number of words and concepts
        self.n_words = len(self.word2index)
        self.n_concepts = len(self.concept2index)
        
    def clean(self, text):
        text = re.sub('[^\w\s\d\'\-]','', text)
        text = text.lower()        
        
        return text
    
    def interpretation_vector(self, text):
        '''Converts a text fragment string into a row vector where the i'th
        entry corresponds to the total TF-IDF score of the text fragment
        for concept i'''
        
        #Remove mess (quotes, parentheses etc) from text        
        text = self.clean(text)
        
        #Convert string to hash like {'word' : no. of occurrences}
        countmap = Counter(text.split()).iteritems()
        
        #Interpretation vector to be returned
        result = sps.csr_matrix((1, self.n_concepts), dtype = float)
        
        #Add word count in the correct position of the vector
        for word, count in countmap:
            try:
                ind = self.word2index[word]
                #Which file to look in
                file_number = int(ind/row_chunk_size)
                filename = matrix_dir+str(file_number)+extensions['matrix']
                
                #And which row to extract
                row_number = ind % row_chunk_size
                
                #Do it! Do it naw!
                with open(filename, 'r') as f:
                    temp = shared.mload(f)
                    result = result + count*temp.getrow(row_number)
            except KeyError:
                pass    #No data on this word -> discard
        
        #Done. Return row vector as a 1x#concepts CSR matrix
        return result
        
    def interpret_text(self, text, display_concepts = 10):
        '''Attempts to guess the core concepts of the given text fragment'''
        #Compute the interpretation vector for the text fragment
        vec = self.interpretation_vector(text)
        
        #Magic, don't touch
        top_n = vec.data.argsort()[:len(vec.data)-1-display_concepts:-1]
        
        #List top scoring concepts and their TD-IDF
        concepts = [self.index2concept[vec.indices[i]] for i in top_n]
        return concepts
#        scores = [vec.data[i] for i in top_n]
#        #Return as dict {concept : score}
#        return dict(zip(concepts, scores))
    
    def interpret_file(self, filename):
        with open(filename, 'r') as f:
            data = self.clean(f.read())
        return self.interpret_text(data)
        
    def interpret_input(self):
        text = raw_input("Enter text fragment: ")
        topics = self.interpret_text(text)
        print "Based on your input, the most probable topics of your text are:"
        print topics[:self.display_concepts]

    def scalar(self, v1, v2):
        #Compute their inner product and make sure it's a scalar
        dot = v1.dot(v2.transpose())
        assert dot.shape == (1,1)
        
        if dot.data:
            scal = dot.data[0]
        else:
            scal = 0    #Empty sparse matrix means zero
            
        #Normalize and return
        sim = scal/(norm(v1.data)*norm(v2.data))
        return sim

    def cosine_similarity(self, text1, text2):
        '''Determines cosine similarity between input texts.
        Returns float in [0,1]'''
        
        #Determine intepretation vectors
        v1 = self.interpretation_vector(text1)
        v2 = self.interpretation_vector(text2)
        
        #Compute the normalized dot product and return
        return self.scalar(v1, v2)
        
        
    def cosine_distance(self, text1, text2):
        return 1-self.cosine_similarity(text1, text2)

if __name__ == '__main__':
    th = TweetHarvester(verbose=True, max_tweets=10)
    th.mine('carlsberg', n=10)
    temp = [t._json for t in th.harvested_tweets if t._json['lang'] == 'en']
    js = temp[4]
    with open('tweet_example.json', 'w') as f:
        pprint(js, stream=f)
    
#    if len(sys.argv) > 1:
#        fn = sys.argv[1]
#    else:
#        fn = 'interpret_me.txt'
#        with open(fn, 'r') as f:
#            data = f.read()
#        #
#    data = sa.clean(data)
#    guesses = sa.interpret_text(data)
#
#    if len(sys.argv) > 2:
#        output_filename = sys.argv[2]
#    else:
#        output_filename = 'guesses.txt'
#    with open(output_filename, 'w') as f:
#        for line in guesses:
#            f.write(line.encode('utf8'))
#            f.write('\n')
