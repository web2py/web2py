import re

CACHED_REGEXES = {}

def re_compile(regex):
    try:
        return CACHED_REGEXES[regex]
    except KeyError:
        compiled_regex = CACHED_REGEXES[regex] = re.compile(regex)
        return compiled_regex

