# -*- coding: utf-8 -*-
import re
from htmlentitydefs import name2codepoint

namespaces = set(['help', 'file talk', 'module', 'topic', 'mediawiki',
'wikipedia talk', 'file', 'user talk', 'special', 'category talk', 'category',
'media', 'wikipedia', 'book', 'draft', 'book talk', 'template', 'help talk',
'timedtext', 'mediawiki talk', 'portal talk', 'portal', 'user', 'module talk',
'template talk', 'education program talk', 'education program',
'timedtext talk', 'draft talk', 'talk'])

def dropNested(text, openDelim, closeDelim):
    '''Helper function to match nested expressions which may cause problems
    example: {{something something {{something else}} and something third}}
    cannot be easily matched with a regexp to remove all occurrences.
    Copied from the WikiExtractor project.'''
    openRE = re.compile(openDelim)
    closeRE = re.compile(closeDelim)
    # partition text in separate blocks { } { }
    matches = []                # pairs (s, e) for each partition
    nest = 0                    # nesting level
    start = openRE.search(text, 0)
    if not start:
        return text
    end = closeRE.search(text, start.end())
    next = start
    while end:
        next = openRE.search(text, next.end())
        if not next:            # termination
            while nest:         # close all pending
                nest -=1
                end0 = closeRE.search(text, end.end())
                if end0:
                    end = end0
                else:
                    break
            matches.append((start.start(), end.end()))
            break
        while end.end() < next.start():
            # { } {
            if nest:
                nest -= 1
                # try closing more
                last = end.end()
                end = closeRE.search(text, end.end())
                if not end:     # unbalanced
                    if matches:
                        span = (matches[0][0], last)
                    else:
                        span = (start.start(), last)
                    matches = [span]
                    break
            else:
                matches.append((start.start(), end.end()))
                # advance start, find next close
                start = next
                end = closeRE.search(text, next.end())
                break           # { }
        if next != start:
            # { { }
            nest += 1
    # collect text outside partitions
    res = ''
    start = 0
    for s, e in  matches:
        res += text[start:s]
        start = e
    res += text[start:]
    return res

def unescape(text):
    '''Removes HTML or XML character references and entities
    from a text string.
    @return nice text'''
    def fixup(m):
        text = m.group(0)
        code = m.group(1)
        return text
        try:
            if text[1] == "#":  # character reference
                if text[2] == "x":
                    return unichr(int(code[1:], 16))
                else:
                    return unichr(int(code))
            else:               # named entity
                return unichr(name2codepoint[code])
        except UnicodeDecodeError:
            return text # leave as is

    return re.sub("&#?(\w+);", fixup, text)

def drop_spans(matches, text):
    """Drop from text the blocks identified in matches"""
    matches.sort()
    res = ''
    start = 0
    for s, e in  matches:
        res += text[start:s]
        start = e
    res += text[start:]
    return res

###Compile regexps for text cleanup:
#Construct patterns for elements to be discarded:
discard_elements = set([
        'gallery', 'timeline', 'noinclude', 'pre',
        'table', 'tr', 'td', 'th', 'caption',
        'form', 'input', 'select', 'option', 'textarea',
        'ul', 'li', 'ol', 'dl', 'dt', 'dd', 'menu', 'dir',
        'ref', 'references', 'img', 'imagemap', 'source'
        ])
discard_element_patterns = []
for tag in discard_elements:
    pattern = re.compile(r'<\s*%s\b[^>]*>.*?<\s*/\s*%s>' % (tag, tag), re.DOTALL | re.IGNORECASE)
    discard_element_patterns.append(pattern)

#Construct patterns to recognize HTML tags
selfclosing_tags = set([ 'br', 'hr', 'nobr', 'ref', 'references' ])
selfclosing_tag_patterns = []
for tag in selfclosing_tags:
    pattern = re.compile(r'<\s*%s\b[^/]*/\s*>' % tag, re.DOTALL | re.IGNORECASE)
    selfclosing_tag_patterns.append(pattern)

#Construct patterns for tags to be ignored
ignored_tags = set([
        'a', 'b', 'big', 'blockquote', 'center', 'cite', 'div', 'em',
        'font', 'h1', 'h2', 'h3', 'h4', 'hiero', 'i', 'kbd', 'nowiki',
        'p', 'plaintext', 's', 'small', 'span', 'strike', 'strong',
        'sub', 'sup', 'tt', 'u', 'var',
])
ignored_tag_patterns = []
for tag in ignored_tags:
    left = re.compile(r'<\s*%s\b[^>]*>' % tag, re.IGNORECASE)
    right = re.compile(r'<\s*/\s*%s>' % tag, re.IGNORECASE)
    ignored_tag_patterns.append((left, right))

#Construct patterns to recognize math and code
placeholder_tags = {'math':'formula', 'code':'codice'}
placeholder_tag_patterns = []
for tag, repl in placeholder_tags.items():
    pattern = re.compile(r'<\s*%s(\s*| [^>]+?)>.*?<\s*/\s*%s\s*>' % (tag, tag), re.DOTALL | re.IGNORECASE)
    placeholder_tag_patterns.append((pattern, repl))

#HTML comments
comment = re.compile(r'<!--.*?-->', re.DOTALL)

#Wikilinks
wiki_link = re.compile(r'\[\[([^[]*?)(?:\|([^[]*?))?\]\](\w*)')
parametrized_link = re.compile(r'\[\[.*?\]\]')

#External links
externalLink = re.compile(r'\[\w+.*? (.*?)\]')
externalLinkNoAnchor = re.compile(r'\[\w+[&\]]*\]')

#Bold/italic text
bold_italic = re.compile(r"'''''([^']*?)'''''")
bold = re.compile(r"'''(.*?)'''")
italic_quote = re.compile(r"''\"(.*?)\"''")
italic = re.compile(r"''([^']*)''")
quote_quote = re.compile(r'""(.*?)""')

#Spaces
spaces = re.compile(r' {2,}')

#Dots
dots = re.compile(r'\.{4,}')

#Sections
section = re.compile(r'(==+)\s*(.*?)\s*\1')

# Match preformatted lines
preformatted = re.compile(r'^ .*?$', re.MULTILINE)

#Wikilinks
def make_anchor_tag(match):
    '''Recognizes links and returns only their anchor. Example:
    <a href="www.something.org">Link text</a> -> Link text'''
    link = match.group(1)
    colon = link.find(':')
    if colon > 0 and link[:colon] not in namespaces:        
        return ''
    trail = match.group(3)
    anchor = match.group(2)
    if not anchor:
        if link[:colon] in namespaces:
            return '' #Don't keep stuff like "category:shellfish"
        anchor = link
    anchor += trail
    return anchor

def clean(text):
    '''Outputs an article in plaintext from its format in the raw xml dump.'''        
    # Drop transclusions (template, parser functions)
    # See: http://www.mediawiki.org/wiki/Help:Templates
    text = dropNested(text, r'{{', r'}}')
    # Drop tables
    text = dropNested(text, r'{\|', r'\|}')
    
    # Convert wikilinks links to plaintext
    text = wiki_link.sub(make_anchor_tag, text)
    # Drop remaining links
    text = parametrized_link.sub('', text)
    
    # Handle external links
    text = externalLink.sub(r'\1', text)
    text = externalLinkNoAnchor.sub('', text)
    
    #Handle text formatting
    text = bold_italic.sub(r'\1', text)
    text = bold.sub(r'\1', text)
    text = italic_quote.sub(r'&quot;\1&quot;', text)
    text = italic.sub(r'&quot;\1&quot;', text)
    text = quote_quote.sub(r'\1', text)
    text = text.replace("'''", '').replace("''", '&quot;')
    
    ################ Process HTML ###############    
    
    # turn into HTML
    text = unescape(text)
    
    # do it again (&amp;nbsp;)    
    text = unescape(text)
    
    # Collect spans

    matches = []
    # Drop HTML comments
    for m in comment.finditer(text):
            matches.append((m.start(), m.end()))

    # Drop self-closing tags
    for pattern in selfclosing_tag_patterns:
        for m in pattern.finditer(text):
            matches.append((m.start(), m.end()))
    
    # Drop ignored tags
    for left, right in ignored_tag_patterns:
        for m in left.finditer(text):
            matches.append((m.start(), m.end()))
        for m in right.finditer(text):
            matches.append((m.start(), m.end()))

    # Bulk remove all spans
    text = drop_spans(matches, text)
    
    # Cannot use dropSpan on these since they may be nested
    # Drop discarded elements
    for pattern in discard_element_patterns:
        text = pattern.sub('', text)
    
    # Expand placeholders
    for pattern, placeholder in placeholder_tag_patterns:
        index = 1
        for match in pattern.finditer(text):
            text = text.replace(match.group(), '%s_%d' % (placeholder, index))
            index += 1
    
    #############################################
    
    # Drop preformatted
    # This can't be done before since it may remove tags
    text = preformatted.sub('', text)

    # Cleanup text
    text = text.replace('\t', ' ')
    text = spaces.sub(' ', text)
    text = dots.sub('...', text)
    text = re.sub(u' (,:\.\)\]»)', r'\1', text)
    text = re.sub(u'(\[\(«) ', r'\1', text)
    text = re.sub(r'\n\W+?\n', '\n', text) # lines with only punctuations
    text = text.replace(',,', ',').replace(',.', '.')    
    
    #Handle section headers, residua etc.
    page = []
    headers = {}
    empty_section = False
    
    for line in text.split('\n'):

        if not line:
            continue
        # Handle section titles
        m = section.match(line)
        if m:
            title = m.group(2)
            lev = len(m.group(1))
            if title and title[-1] not in '!?':
                title += '.'
            headers[lev] = title
            # drop previous headers
            for i in headers.keys():
                if i > lev:
                    del headers[i]
            empty_section = True
            continue
        # Handle page title
        if line.startswith('++'):
            title = line[2:-2]
            if title:
                if title[-1] not in '!?':
                    title += '.'
                page.append(title)
        # handle lists
        elif line[0] in '*#:;':
            continue
        # Drop residuals of lists
        elif line[0] in '{|' or line[-1] in '}':
            continue
        # Drop irrelevant lines
        elif (line[0] == '(' and line[-1] == ')') or line.strip('.-') == '':
            continue
        elif len(headers):
            items = headers.items()
            items.sort()
            for (i, v) in items:
                page.append(v)
            headers.clear()
            page.append(line)   # first line
            empty_section = False
        elif not empty_section:
            page.append(line)    
    
    text = ''.join(page)

    #Remove quote tags.
    text = text.replace("&quot;", '')

    #Get rid of parentheses, punctuation and the like    
    text = re.sub('[^\w\s\d\'\-]','', text)
    return text