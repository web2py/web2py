EXPIRATION = 60 * 60  # logout after 60 minutes of inactivity
CHECK_VERSION = True
WEB2PY_URL = 'http://web2py.com'
WEB2PY_VERSION_URL = WEB2PY_URL+'/examples/default/version'

###########################################################################
# Preferences for EditArea
# the user-interface feature that allows you to edit files in your web
# browser.

## Default editor
TEXT_EDITOR = 'ace' or 'edit_area' or 'amy'
## Editor Color scheme (only for ace)
TEXT_EDITOR_THEME = (
    "chrome", "clouds", "clouds_midnight", "cobalt", "crimson_editor", "dawn", 
    "dreamweaver", "eclipse", "idle_fingers", "kr_theme", "merbivore",
    "merbivore_soft", "monokai", "mono_industrial", "pastel_on_dark", 
    "solarized_dark", "solarized_light", "textmate", "tomorrow",
    "tomorrow_night", "tomorrow_night_blue", "tomorrow_night_bright",
    "tomorrow_night_eighties", "twilight", "vibrant_ink")[0]
## Editor Keyboard bindings (only for ace)
TEXT_EDITOR_KEYBINDING = '' #'emacs' or 'vi'
    
### edit_area
# The default font size, measured in 'points'. The value must be an integer > 0
FONT_SIZE = 10

# Displays the editor in full screen mode. The value must be 'true' or 'false'
FULL_SCREEN = 'false'

# Display a check box under the editor to allow the user to switch
# between the editor and a simple
# HTML text area. The value must be 'true' or 'false'
ALLOW_TOGGLE = 'true'

# Replaces tab characters with space characters.
# The value can be 'false' (meaning that tabs are not replaced),
# or an integer > 0 that specifies the number of spaces to replace a tab with.
REPLACE_TAB_BY_SPACES = 4

# Toggle on/off the code editor instead of textarea on startup
DISPLAY = "onload" or "later"

# if demo mode is True then admin works readonly and does not require login
DEMO_MODE = False

# if visible_apps is not empty only listed apps will be accessible
FILTER_APPS = []

# To upload on google app engine this has to point to the proper appengine
# config file
import os
# extract google_appengine_x.x.x.zip to web2py root directory
#GAE_APPCFG = os.path.abspath(os.path.join('appcfg.py'))
# extract google_appengine_x.x.x.zip to applications/admin/private/
GAE_APPCFG = os.path.abspath(os.path.join('/usr/local/bin/appcfg.py'))

# To use web2py as a teaching tool, set MULTI_USER_MODE to True
MULTI_USER_MODE = False
EMAIL_SERVER    = 'localhost'
EMAIL_SENDER    = 'professor@example.com'
EMAIL_LOGIN     = None

# configurable twitterbox, set to None/False to suppress
TWITTER_HASH = "web2py"

# parameter for downloading LAYOUTS
LAYOUTS_APP = 'http://web2py.com/layouts'
#LAYOUTS_APP = 'http://127.0.0.1:8000/layouts'


# parameter for downloading PLUGINS
PLUGINS_APP = 'http://web2py.com/plugins'
#PLUGINS_APP = 'http://127.0.0.1:8000/plugins'

# set the language
if 'adminLanguage' in request.cookies and not (request.cookies['adminLanguage'] is None):
    T.force(request.cookies['adminLanguage'].value)


