# -*- coding: utf-8 -*-
'''Parameters and methods to be shared between scripts.
Always import from here.'''

import time 
import httplib
import urllib
import scipy.sparse as sps
import numpy as np
import json

#==============================================================================
# Parameters that should be adjusted according to available ressources
#==============================================================================

#Number of data files to process at a time. Highly RAM-dependent
link_chunk_size = 600 #600 is good for a standard laptop
column_chunk_size = 500 #These take up a bit more space than links
row_chunk_size = 10**4 #No of words pr file

datatype = np.float64 #Must be float. Double precision might be pushing it
indent = 4 #json indentation. 4 for readability - 0 for optimal storing

#Minimum number of links/words required to keep an article.
min_links_in = 0   #5
min_links_out = 0  #5
min_words = 0  #100

#Pruning parameters
prune = True
window_size = 100
cutoff = 0.95

#Whether to send notifications when done
notify = False

#==============================================================================
# Parameters that generally shouldn't be fiddled with
#==============================================================================

#Allow push notifications to inform of progress in the script
try:
    from supersecretstuff import pushover_api_token, pushover_user_key
except ImportError:
    if notify: #Tell user not to hold their breath
        print "Pushover credentials missing - can't send push notifications."


conn = httplib.HTTPSConnection("api.pushover.net:443")
def pushme(text = __name__+' finished!'):
    conn.request("POST", "/1/messages.json", urllib.urlencode({
    "token": pushover_api_token,
    "user": pushover_user_key,
    "message": text,
    }), { "Content-type": "application/x-www-form-urlencoded" })
    conn.getresponse()

#Returns functions to write log files as the script progresses.
def logmaker(filehandle):
    def log(text):
        string = text+" at "+time.asctime()+"\n"
        print string
        filehandle.write(string)
        return None
    return lambda text: log(text)
        

#File name extensions
extensions = {'content' : '.raw',
              'words' : '.w',
              'links' : '.l',
              'matrix' : '.mtx'}

#File directories
temp_dir = 'temp/' #Temporary files. Duh.
matrix_dir = 'matrix/' #Files containing subspacess of TFIDF-matrix

#==============================================================================
# The following methods are to be used istead of Python's default json dumps
# for two reasons.:
# First: The 'normal' methods (load and dump) ensure consistent formatting and
# automatically converts datatypes which json doesn't understand, e.g. sets.
# Second: mload and mdump allows frictionless dumping and loading of the
# sparse matrix format CSR employed by Python's scipy library.
#==============================================================================


def dump(obj, file_handle, type='regular'):
    '''Dumps object to JSON format. Automatically converts set -> list
    Remembering this is YOUR responsibility, future me!'''
    if type=='regular':
        json.dump(obj, file_handle, indent=indent,
                  default = lambda someset: list(someset))

def load(file_handle):
    return json.load(file_handle, object_hook=None)

def dump_helper(obj):
    '''Helper method to allow json dumps of csr matrices. Don't fiddle.'''
    if isinstance(obj, sps.csr_matrix):
        d = {'object_type' : 'csr_matrix',
             'data' : obj.data,
             'indices' : obj.indices,
             'indptr' : obj.indptr,
             'shape' : obj.shape}
    #CSR relies on numpy arrays, so we need to be able to dump those, too.
    elif isinstance(obj, np.ndarray):
        d = obj.tolist()
    else:
        raise TypeError("Can't handle %s objects." % type(obj))
    
    return d

def mdump(obj, file_handle):
    '''Dumps CSR matrices to JSON file.'''
    json.dump(obj, file_handle, indent=indent,
              default = dump_helper)

def reconstruct(d):
    '''Helper method to reconstruct CSR matrix dumped in JSON format'''
    if 'object_type' in d and d['object_type'] == 'csr_matrix':
        data = np.array(d['data'])
        indices = d['indices']
        indptr = d['indptr']
        shape = tuple(d['shape'])
        instance = sps.csr_matrix((data, indices, indptr),
                                        shape)
        return instance

def mload(file_handle):
    '''Loads CSR matrices from JSON dump.'''
    return json.load(file_handle, object_hook=reconstruct)

if __name__ == '__main__':
    print pushme()