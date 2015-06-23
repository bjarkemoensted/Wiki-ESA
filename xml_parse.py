# -*- coding: utf-8 -*-
'''Parses a full Wikipedia XML-dump and saves to files containing
a maximum of 1000 articles.
In the end, each file is saved as a JSON file containing entries like:
{{
    'concept':
    {
    'text': <article contents>,
    'links_in' : Set of links TO the article in question, 
    'links_out' : Set of links FROM the article in question,
    }
}
Although links_in is added by the generate_indices script.
Also saved are dicts for keeping track of word and concept indices when
building a large sparse matrix for the semantic interpreter.
The file structure is like {'word blah' : index blah}'''

import re
import xml.sax as SAX
import wikicleaner
import os
import glob
import shared
import sys

DEFAULT_FILENAME = 'medium_wiki.xml'

def canonize_title(title):
  # remove leading whitespace and underscores
    title = title.strip(' _')
  # replace sequencesences of whitespace and underscore chars with a single space
    title = re.compile(r'[\s_]+').sub(' ', title)
    #remove forbidden characters
    title = re.sub('[?/\\\*\"\']','',title)
    return title.title()

#Import shared parameters
from shared import extensions, temp_dir

#Cleanup
for ext in extensions.values():
    for f in glob.glob(temp_dir + '*'+ext):
        os.remove(f)

def filename_generator(folder):
    '''Generator for output filenames'''
    if not os.path.exists(folder):
        os.makedirs(folder)
    count = 0
    while True:
        filename = folder+"content"+str(count)
        count += 1
        yield filename

make_filename = filename_generator(temp_dir)

#Format {right title : redirected title}, e.g. {because : ([cuz, cus])}
redirects = {}

#Minimum number of links/words required to keep an article.
from shared import min_links_out, min_words

#Open log file for writing and import logging function
logfile = open(os.path.basename(__file__)+'.log', 'w')
log = shared.logmaker(logfile)

class WikiHandler(SAX.ContentHandler):
    '''ContentHandler class to process XML and deal with the WikiText.
    It works basically like this:
    It traverses the XML file, keeping track of the type of data being read and
    adding any text to its input buffer. When event handlers register a page
    end, the page content is processed, the processed content is placed in the
    output buffer, and the input buffer is flushed.
    Whenever a set number of articles have been processed, the output buffer is
    written to a file. The point of this approach is to 
    limit memory consumption.'''
    
    def __init__(self):
        SAX.ContentHandler.__init__(self)
        self.current_data = None
        self.title = ''
        self.input_buffer = []
        self.output_buffer = {}
        self.article_counter = 0
        self.links = []
        self.categories = []
        self.redirect = None
        self.verbose = False
        #Harvest unique words here
        self.words = set([])
        #keeps track of ingoing article links. format {to : set([from])}
        self.linkhash = {}
    
    def flush_input_buffer(self):
        '''Deletes info on the currently processed article.
        This is called when a page end event is registered.'''
        self.input_buffer = []
        self.current_data = None
        self.title = ''
        self.links = []
        self.categories = []
        self.redirect = None
        
    def flush_output_buffer(self):
        '''Flushes data gathered so far to a file and resets.'''
        self.output_buffer = {}
        self.words = set([])
        self.linkhash = {}
    
    def startElement(self, tag, attrs):
        '''Eventhandler for element start - keeps track of current datatype.'''
        self.current_data = tag
        #Informs the parser of the redirect destination of the article
        if tag == "redirect":
            self.redirect = attrs['title']
            return None
    
    def endElement(self, name):
        '''Eventhandler for element end. This causes the parser to process
        its input buffer when a pageend is encountered.'''
        #Process content after each page
        if name == 'page':
            self.process()
        #Write remaining data at EOF.
        elif name == 'mediawiki':
            self.writeout()

    def characters(self, content):
        '''Character event handler. This simply passes any raw text from an
        article field to the input buffer and updates title info.'''
        if self.current_data == 'text':
            self.input_buffer.append(content)
        elif self.current_data == 'title' and not content.isspace():
            self.title = content
    
    def process(self):
        '''Process input buffer contents. This converts wikilanguage to
        plaintext, registers link information and checks if content has
        sufficient words and outgoing links (ingoing links can't be checked
        until the full XML file is processed).'''
        
        #Ignore everything else if article redirects
        if self.redirect:
            self.flush_input_buffer()
            return None
            global redirects
            try:
                redirects[self.title].add(self.redirect)
            except KeyError:
                redirects[self.title] = set([self.redirect])
            self.flush_input_buffer()
            return None
        
        #Redirects handled - commence processing
        print "processing: "+self.title.encode('utf8')
        #Combine buffer content to a single string
        text = ''.join(self.input_buffer).lower()
        
        #Find and process link information
        link_regexp = re.compile(r'\[\[(.*?)\]')
        links = re.findall(link_regexp, text)  #grap stuff like [[<something>]]
        #Add links to the parsers link hash
        for link in links:
            #Check if link matches a namespace, e.g. 'file:something.png'
            if any([ns+':' in link for ns in wikicleaner.namespaces]):
                continue #Proceed to next link
            #Namespaces done, so remove any colons:
            link = link.replace(':', '')
            if not link:
                continue  #Some noob could've written an empty link...
            #remove chapter designations/displaytext - keep article title
            raw = re.match(r'([^\|\#]*)', link).group(0)
            title = canonize_title(raw)
            #note down that current article has outgoing link to 'title'
            self.links.append(title)
            #also note that 'title' has incoming link from here
            try:
                self.linkhash[title].add(self.title)  #maps target->sources
            except KeyError:
                self.linkhash[title] = set([self.title])
        
        #Disregard current article if it contains too few links       
        if len(self.links) < min_links_out:
            self.flush_input_buffer()
            return None
        
        #Cleanup text        
        text = wikicleaner.clean(text)
        article_words = text.split()
        
        #Disregard article if it contains too few words
        if len(article_words) < min_words:
            self.flush_input_buffer()
            return None
                
        #Update global list of unique words
        self.words.update(set(article_words))
        
        #Add content to output buffer
        output = {
            'text' : text,
            #Don't use category info for now
            #'categories' : self.categories,
            'links_out' : self.links
        }
        self.output_buffer[self.title] = output
        self.article_counter += 1
        
        #Flush output buffer to file
        if self.article_counter%1000 == 0:
            self.writeout()            
        
        #Done, flushing buffer
        self.flush_input_buffer()
        return None
        
    def writeout(self):
        '''Writes output buffer contents to file'''
        #Generate filename and write to file
        filename = make_filename.next()
        #Write article contents to file
        with open(filename+extensions['content'], 'w') as f:
            shared.dump(self.output_buffer, f)
        
        #Store wordlist as files
        with open(filename+extensions['words'], 'w') as f:
            shared.dump(self.words, f)
        
        #Store linkhash in files
        with open(filename+extensions['links'], 'w') as f:
            shared.dump(self.linkhash, f)
        
        if self.verbose:
            log("wrote "+filename)
        
        #Empty output buffer
        self.flush_output_buffer()
        return None
    
if __name__ == "__main__":
    if len(sys.argv) == 2:
        file_to_parse = sys.argv[1]
    else:
        file_to_parse = DEFAULT_FILENAME
    
    #Create and configure content handler
    test = WikiHandler()
    test.verbose = True
    
    #Create a parser and set handler
    ATST = SAX.make_parser()
    ATST.setContentHandler(test)
    
    #Let the parser walk the file
    log("Parsing started...")
    ATST.parse(file_to_parse)
    log("...Parsing done!")
    
    #Attempt to send notification that job is done
    if shared.notify:
        try:
            shared.pushme(sys.argv[0]+' completed.')
        except:
            log("Job's done. Push failed.")
    
    logfile.close()
