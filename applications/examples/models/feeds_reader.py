def group_feed_reader(group, mode='div', counter='5'):
    """parse group feeds"""

    url = "http://groups.google.com/group/%s/feed/rss_v2_0_topics.xml?num=%s" %\
          (group, counter)
    from gluon.contrib import feedparser
    g = feedparser.parse(url)

    if mode == 'div':
        html = XML(TAG.BLOCKQUOTE(UL(*[LI(A(entry['title'] + ' - ' +
                                            entry['author'][
                                                entry['author'].rfind('('):],
                                            _href=entry['link'], _target='_blank'))
                                       for entry in g['entries']]),
                                  _class="boxInfo",
                                  _style="padding-bottom:5px;"))

    else:
        html = XML(UL(*[LI(A(entry['title'] + ' - ' +
                             entry['author'][entry['author'].rfind('('):],
                             _href=entry['link'], _target='_blank'))
                        for entry in g['entries']]))

    return html


def code_feed_reader(project, mode='div'):
    """parse code feeds"""

    url = "http://code.google.com/feeds/p/%s/hgchanges/basic" % project
    from gluon.contrib import feedparser
    g = feedparser.parse(url)
    if mode == 'div':
        html = XML(DIV(UL(*[LI(A(entry['title'], _href=entry['link'],
                                 _target='_blank'))
                            for entry in g['entries'][0:5]]),
                       _class="boxInfo",
                       _style="padding-bottom:5px;"))
    else:
        html = XML(UL(*[LI(A(entry['title'], _href=entry['link'],
                             _target='_blank'))
                        for entry in g['entries'][0:5]]))

    return html
