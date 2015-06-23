# -*- coding: utf-8 -*-
'''Stuff to passively mine Twitter for data and save to files.
Logging and error handling should work.
Simply place in the folder you want the tweets saved in and go 
'python thisfile.py'. Tweets are saved in json format.'''

from __future__ import division
import tweepy
from datetime import date
import json
import time

#This should allow printing tweets in unicode to any console... I think.
import sys
import codecs
sys.stdout = codecs.getwriter('utf8')(sys.stdout)
sys.stderr = codecs.getwriter('utf8')(sys.stderr)

#==============================================================================
# Adjust paremeters here
#==============================================================================

#Set search keywords
keywords = ['google','starbucks','ibm','toyota','microsoft','burger king',
            'mcdonalds','coca cola','vodafone','ford','general motors',
            'intel','boeing','disney','water','glass','sun','bitcoin']

#Number of tweets to store in each file
tweets_pr_file = 10**5


#==============================================================================
# Testing stuff. Implements IncompleteRead exception to be raised when
# the Twitter API messes up.
#==============================================================================

class IncompleteRead(Exception):
    pass

#import random
#def maybe_crash(n=10):
#    if random.randint(0,n) == 0:
#        raise IncompleteRead('ermagehrd!')

#==============================================================================
# Define TweetHarvester class
#==============================================================================

#Import credentials for accessing Twitter API
from supersecretstuff import consumer_key, consumer_secret, access_token, access_token_secret
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)

  
class TweetHarvester:
    '''Simple class to handle tweet harvest.
    Harvest can be performed actively or passively, i.e. using the 'mine' 
    method to gather a fixed number of tweets or using the 'listen' method
    to stream tweets matching a given search term.
    Harvested tweets are sent to the process method which by default simply
    stores them inside the object.'''
    
    def __init__(self):
        self.max_tweets = -1  #-1 for unlimited stream
        self.tweets_pr_file = 10
        self.files_saved = 0
        self.harvested_tweets = []
        self.verbose = False
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
# Main loop. The Twitter API seems to raise a weird ImcompleteRead exception
# every three days or so. The somewhat weird loop structure here accommodates
# this. Be sure to know what you're doing before messing with it, as the 
# rareness of the exceptions might make any change appear to be working
# while still crashing a few days after initial testing.
#==============================================================================


def main():

    #Create harvester
    th = TweetHarvester()
    #Enable printed output
    th.verbose = True
    #Set number of tweets contained in each output file
    th.tweets_pr_file = tweets_pr_file
    
    #Emergency brakes :)
    stop = False    
    
    #GO!
    while True:
        try:
            th.listen(keywords)
        except KeyboardInterrupt:
            stop = True
        except IncompleteRead:
            th.log("IncompleteRead occurred")
        except:
            th.log('Some other exception occurred. Retrying')
            pass
        finally:
            th.writeout()
        if stop:
            break
    return None

if __name__ == '__main__':
    main()
