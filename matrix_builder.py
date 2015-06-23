# -*- coding: utf-8 -*-
'''Builds a huge sparse matrix of Term frequency/Inverse Document Frequency 
(TFIDF) of the previously extracted words and concepts.
First a matrix containing simply the number of occurrences of word i in the
article corresponding to concept j is build (in DOK format as that is faster
for iterative construction), then the matrix is converted to sparse row format
(CSR), TFIDF values are computed, each row is normalized and finally pruned.'''

from __future__ import division
import scipy.sparse as sps
import numpy as np
from collections import Counter
import glob
import shared
import sys
import os

def percentof(small, large):
    return str(100*small/large) + "%"

logfile = open(os.path.basename(__file__)+'.log', 'w')
log = shared.logmaker(logfile)

#import shared parameters
from shared import (extensions, matrix_dir, prune, temp_dir, column_chunk_size,
                    row_chunk_size, datatype)

def main():
    #Cleanup
    for f in glob.glob(matrix_dir + '/*'+extensions['matrix']):
        os.remove(f)

    #Set pruning parameters
    window_size = shared.window_size
    cutoff = shared.cutoff
    
    #Read in dicts mapping words and concepts to their respective indices
    log("Reading in word/index data")
    word2index = shared.load(open(matrix_dir+'word2index.ind', 'r'))
    concept2index = shared.load(open(matrix_dir+'concept2index.ind', 'r'))
    log("...Done!")
    
#==============================================================================
#     Construct count matrix in small chunks    
#==============================================================================
    
    #Count words and concepts
    n_words = len(word2index)
    n_concepts = len(concept2index)
    
    #Determine matrix dimensions
    matrix_shape = (n_words, n_concepts)
    
    #Allocate sparse matrix. Dict-of-keys should be faster for iterative
    #construction. Convert to csr for fast row operations later.
    mtx = sps.dok_matrix(matrix_shape, dtype = datatype)
    
    def matrix_chopper(matrix, dim):
        '''Generator to split a huge matrix into small submatrices, which can
        then be stored in individual files.
        This is handy both when constructing the matrix (building the whole
        matrix without saving to files in the process takes about 50 gigs RAM),
        and when applying it, as this allows one to load only the submatrix
        relevant to a given word.'''
        ind = 0
        counter = 0
        rows = matrix.get_shape()[0]
        while ind < rows:
            end = min(ind+dim, rows)
            #Return pair of submatrix number and the submatrix itself
            yield counter, sps.vstack([matrix.getrow(i)\
                                    for i in xrange(ind, end)], format = 'csr')
            counter += 1
            ind += dim
    
    def writeout():
        '''Saves the matrix as small submatrrices in separate files.'''
        for n, submatrix in matrix_chopper(mtx, row_chunk_size):
            filename = matrix_dir+str(n)+extensions['matrix']
            #Update submatrix if it's already partially calculated
            log("Writing out chunk %s" % n)
            try:
                with open(filename, 'r') as f:
                    submatrix = submatrix + shared.mload(f)
                #
            except IOError:
                pass #File doesn't exist yet, so no need to change mtx
            
            #Dump the submatrix to file
            with open(filename, 'w') as f:
                shared.mdump(submatrix, f)
        return None
    
    log("Constructing matrix.")
    filelist = glob.glob(temp_dir + '*'+extensions['content'])
    files_read = 0
    for filename in filelist:
        with open(filename, 'r') as f:
            content = shared.load(f)
        
        #Loop over concepts (columns) as so we don't waste time with rare words
        for concept, entry, in content.iteritems():
            #This is the column index (concept w. index j)
            j = concept2index[concept]
            
            #Convert concept 'countmap' like so: {word : n}
            wordmap = Counter(entry['text'].split()).iteritems()
            
            #Add them all to the matrix
            for word, count in wordmap:
                #Find row index of the current word
                i = word2index[word]
    
                #Add the number of times word i occurs in concept j to the matrix
                mtx[i,j] = count
            #
        #Update file count
        files_read += 1
        log("Processed content file no. %s of %s - %s"
            % (files_read, len(filelist)-1, percentof(files_read, len(filelist))))
        
        if files_read % column_chunk_size == 0:
            mtx = mtx.tocsr()
            writeout()
            mtx = sps.dok_matrix(matrix_shape)
        #
    
    #Convert matrix to CSR format and write to files.
    mtx = mtx.tocsr()
    writeout()

#==============================================================================
# Count matrix/matrices constructed - computing TF-IDF
#==============================================================================

    log("Done - computing TF-IDF")
    
    #Grap list of matrix files (containing the submatrices from before)
    matrixfiles = glob.glob(matrix_dir + "*" + extensions['matrix'])
    words_processed = 0  #for logging purposes    
    
    for filename in matrixfiles:
        with open(filename, 'r') as f:
            mtx = shared.mload(f)
        
        #Number of words in a submatrix
        n_rows = mtx.get_shape()[0]
        
        for w in xrange(n_rows):
            #Grap non-zero elements from the row corresonding to word w
            row = mtx.data[mtx.indptr[w] : mtx.indptr[w+1]]
            if len(row) == 0:
                continue
            
            #Make a vectorized function to convert a full row to TF-IDF
            f = np.vectorize(lambda m_ij: (1+np.log(m_ij))*
                             np.log(n_concepts/len(row)))
    
            #Map all elements to TF-IDF and update matrix
            row = f(row)
            
            #Normalize the row
            assert row.dtype.kind == 'f'  #Non floats round to zero w/o warning
            normfact = 1.0/np.linalg.norm(row)            
            row *= normfact
            
            #Start inverted index pruning
            if prune:                
                #Number of documents containing w
                n_docs = len(row)        
                
                #Don't prune if the windows exceeds the array bounds (duh)
                if window_size < n_docs:
                    
                    #Obtain list of indices such that row[index] is sorted
                    indices = np.argsort(row)[::-1]
            
                    #Generate a sorted row
                    sorted_row = [row[index] for index in indices]
            
                    #Go through sorted row and truncate when pruning condition is met
                    for i in xrange(n_docs-window_size):
                        if sorted_row[i+window_size] >= cutoff*sorted_row[i]:   
                            #Truncate, i.e. set the remaining entries to zero
                            sorted_row[i:] = [0]*(n_docs-i)
                            break
                        else:
                            pass
                        
                    #Unsort to original positions
                    for i in xrange(n_docs):    
                        row[indices[i]] = sorted_row[i]
                
            #Update matrix
            mtx.data[mtx.indptr[w] : mtx.indptr[w+1]] = row
            
            #Log it
            words_processed += 1
            if words_processed % 10**3 == 0:
                log("Processing word %s of %s - %s" % 
                    (words_processed, n_words,
                     percentof(words_processed, n_words)))
        
        #Keep it sparse - no need to store zeroes
        mtx.eliminate_zeros()
        with open(filename, 'w') as f:
            shared.mdump(mtx, f)
    
    log("Done!")
    
    #Notify that the job is done
    if shared.notify:
        try:
            shared.pushme(sys.argv[0]+' completed.')
        except:
            log("Job's done. Push failed.")    
    
    logfile.close()
    return None

if __name__ == '__main__':
    main()