#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Plural-Forms for fr (French))

nplurals=2  # French language has 2 forms:
            # 1 singular and 1 plural

# Determine plural_id for number *n* as sequence of positive
# integers: 0,1,...
# NOTE! For singular form ALWAYS return plural_id = 0
get_plural_id = lambda n: int(n != 1)

# Construct and return plural form of *word* using
# *plural_id* (which ALWAYS>0). This function will be executed
# for words (or phrases) not found in plural_dict dictionary
# construct_plural_form = lambda word, plural_id: (word + 'suffix')

irregular={
    'aïeul': 'aïeux',
    'bonhomme': 'bonshommes',
    'ciel': 'cieux',
    'oeil': 'yeux',
    'œil': 'yeux',
    'madame': 'mesdames',
    'mademoiselle': 'mesdemoiselles',
    'monsieur': 'messieurs',
    'bijou': 'bijoux',
    'caillou': 'cailloux',
    'chou': 'choux',
    'genou': 'genoux',
    'hibou': 'hiboux',
    'joujou': 'joujoux',
    'pou': 'poux',
    'corail': ' coraux',
    'émail': 'émaux',
    'travail': 'travaux',
    'vitrail': 'vitraux',
    'soupirail': 'soupiraux',
    'bail': 'baux',
    'fermail': 'fermaux',
    'ventail': 'ventaux',
    'bleu': 'bleus',
    'pneu': 'pneus',
    'émeu': 'émeus',
    'enfeu': 'enfeus',
    #'lieu': 'lieus', # poisson

}

def construct_plural_form(word, plural_id):
    u"""
    >>> [construct_plural_form(x, 1) for x in \
         [ 'bleu', 'nez', 'sex', 'bas', 'gruau', 'jeu', 'journal',\
          'chose' ]]
    ['bleus', 'nez', 'sex', 'bas', 'gruaux', 'jeux', 'journaux', 'choses']
    """
    if word in irregular:
        return irregular[word]
    if word[-1:] in ('s', 'x', 'z'):
        return word
    if word[-2:] in ('au', 'eu'):
        return word + 'x'
    if word[-2:] == 'al':
        return word[0:-2] + 'aux'
    return word + 's'

if __name__ == '__main__':
    import doctest
    doctest.testmod()
