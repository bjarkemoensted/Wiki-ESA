# -*- coding: utf-8 -*-
'''This finishes preproccessing of the output from the XML parser.
This script reads in link data and removes from the content files those 
concepts that have too few incoming links. Information on incoming links
is saved to each content file.
Finally, index maps for words and approved concepts are generated and saved.'''

from __future__ import division
import glob
import gc
import shared
import os
import sys

logfile = open(os.path.basename(__file__)+'.log', 'w')
log = shared.logmaker(logfile)

#Import shared parameters
from shared import extensions, temp_dir, min_links_in, matrix_dir

def listchopper(l):
    '''Generator to chop lists into chunks of a predefined length'''
    n = shared.link_chunk_size 
    ind = 0
    while ind < len(l):
        yield l[ind:ind+n]
        ind += n

def main():    
    #Import shared parameters and verify output dir exists
    if not os.path.exists(temp_dir):
        raise IOError

#==============================================================================
#     Read in link data and update content files accordingly
#==============================================================================

    #Get list of files containing link info and chop it up
    linkfiles = glob.glob(temp_dir + '*'+extensions['links'])
    linkchunks = listchopper(linkfiles)
    
    linkfiles_read = 0
    for linkchunk in linkchunks:
        #Hash mapping each article to a set of articles linking to it
        linkhash = {}
        
        for filename in linkchunk:
            with open(filename, 'r') as f:
                newstuff = shared.load(f)
            #Add link info to linkhash
            for target, sources in newstuff.iteritems():
                try:
                    linkhash[target].update(set(sources))
                except KeyError:
                    linkhash[target] = set(sources)
            
            #Log status
            linkfiles_read += 1
            log("Read " + filename + " - " + 
                str(100*linkfiles_read/len(linkfiles))[:4] + " % of link data.")
        
        log("Chunk finished - updating content files")
        #Update concept with newly read link data
        contentfiles = glob.glob(temp_dir + '*'+extensions['content'])
        contentfiles_read = 0
        for filename in contentfiles:
            #Read file. Content is like {'article title' : {'text' : blah}}
            with open(filename, 'r') as f:
                content = shared.load(f)

            #Search linkhash for links going TO concept                
            for concept in content.keys():
                try:
                    sources = linkhash[concept]
                except KeyError:
                    sources = set([])  #Missing key => zero incoming links
                
                #Update link info for concept
                try:
                    content[concept]['links_in'] = set(content[concept]['links_in'])
                    content[concept]['links_in'].update(sources)
                except KeyError:
                    content[concept]['links_in'] = sources
                
            #Save updated content
            with open(filename, 'w') as f:
                shared.dump(content, f)
                
            contentfiles_read += 1
            if contentfiles_read % 100 == 0:
                log("Fixed " + str(100*contentfiles_read/len(contentfiles))[:4]
                    + "% of content files")
        pass  #Proceed to next link chunk

#==============================================================================
#     Finished link processing 
#     Remove unworthy concepts and combine concept/word lists.   
#==============================================================================
    
    #What, you think memory grows on trees?
    del linkhash
    gc.collect()    
    
    #Set of all approved concepts
    concept_list = set([])
    
    #Purge inferior concepts (with insufficient incoming links)
    for filename in contentfiles:
        #Read in content file
        with open(filename, 'r') as f:
            content = shared.load(f)
        
        for concept in content.keys():
            entry = content[concept]
            if 'links_in' in entry and len(entry['links_in']) >= min_links_in:
                concept_list.add(concept)
            else:
                del content[concept]
        
        with open(filename, 'w') as f:
            shared.dump(content, f)
    
    log("Links done - saving index files")

    #Make sure output dir exists
    if not os.path.exists(matrix_dir):
        os.makedirs(matrix_dir)    
    
    #Generate and save a concept index map. Structure: {concept : index}
    concept_indices = {n: m for m,n in enumerate(concept_list)}
    with open(matrix_dir+'concept2index.ind', 'w') as f:
        shared.dump(concept_indices, f)
    
    #Read in all wordlists and combine them.
    words = set([])
    for filename in glob.glob(temp_dir + '*'+extensions['words']):
        with open(filename, 'r') as f:
            words.update(shared.load(f))
        
    #Generate and save a word index map. Structure: {word : index}
    word_indices = {n: m for m,n in enumerate(words)}
    with open(matrix_dir+'word2index.ind', 'w') as f:
        shared.dump(word_indices, f)
    
    log("Wrapping up.")
    #Attempt to notify that job is done
    if shared.notify:
        try:
            shared.pushme(sys.argv[0]+' completed.')
        except:
            log("Job's done. Push failed.")    
    
    logfile.close()

if __name__ == '__main__':
    main()