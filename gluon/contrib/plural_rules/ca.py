#!/usr/bin/env python
# -*- coding: utf8 -*-
# Plural-Forms for ca (Catalan)

nplurals=2  # Catalan language has 2 forms:
            # 1 singular and 1 plural

# Determine plural_id for number *n* as sequence of positive
# integers: 0,1,...
# NOTE! For singular form ALWAYS return plural_id = 0
get_plural_id = lambda n: int(n != 1)

# Construct and return plural form of *word* using
# *plural_id* (which ALWAYS>0). This function will be executed
# for words (or phrases) not found in plural_dict dictionary
construct_plural_form = lambda word, plural_id:(word[:-2] + 'gues' if word[-2:] == 'ga' else
                                                word[:-2] + 'ques' if word[-2:] == 'ca' else
                                                word[:-2] + 'ces' if word[-2:] == 'ça' else
                                                word[:-2] + 'ges' if word[-2:] == 'ja' else
                                                word[:-2] + 'ües' if word[-3:] in ('gua', 'qua') else
                                                word[:-1] + 'es' if word[-1:] == 'a' else
                                                word if word[-1:] == 's' else
                                                word + 's')
