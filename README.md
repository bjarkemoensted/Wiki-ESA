# Wiki-ESA
Explicit Semantic Analysis based on Wikipedia

This is a python library which contains code to 1) construct a semantic interpreter based on data from Wikipedia and 2) apply this to various kinds of texts.

To construct an interpreter, first obtain a Wikipedia XML dump from http://dumps.wikimedia.org/enwiki/

1) Then run xml_parse.py with the downloaded file as its argument. This outputs some temporary files containing information on the words, links and articles encountered.

2) Next, run generate_indices.py to generate lists of indices corresponding to unique words and articles encountered

3) Finally, run matrix_builder.py to construct a very large sparse interpretation matrix. Each row corresponds to a unique word, each column to a 'concept', i.e. a Wikipedia article, and each entry is the TF-IDF score for word i in article j. The Matrix is saved in separate chunks to conserve memory.

medium_wiki.xml can be used as an example file for demonstration/testing purposes, as it contains only the first 100 or so Wikipedia articles.

cunning_linguistics.py then contains classes to perform text analysis and harvest tweets for analysis.