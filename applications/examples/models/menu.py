# -*- coding: utf-8 -*-

response.menu = [
    (T('Home'),False,URL('default','index')),
    (T('About'),False,URL('default','what')),
    (T('Download'),False,URL('default','download')),
    (T('Docs & Resources'),False,URL('default','documentation')),
    (T('Support'),False,URL('default','support')),
    (T('Contributors'),False,URL('default','who'))]

#########################################################################
## Changes the menu active item
#########################################################################
def toggle_menuclass(cssclass='pressed',menuid='headermenu'):
    """This function changes the menu class to put pressed appearance"""

    positions = dict(
                           index='',
                           what='-108px -115px',
                           download='-211px -115px',
                           who='-315px -115px',
                           support='-418px -115px',
                           documentation='-520px -115px'
                           )


    if request.function in positions.keys():
            jscript = """
            <script>
             $(document).ready(function(){
                         $('.%(menuid)s a').removeClass('%(cssclass)s');
                         $('.%(function)s').toggleClass('%(cssclass)s').css('background-position','%(cssposition)s')

             });
            </script>
            """ % dict(cssclass=cssclass,
                            menuid=menuid,
                            function=request.function,
                            cssposition=positions[request.function]
                            )

            return XML(jscript)
    else:
        return ''

