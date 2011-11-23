"""
Extract client information from http user agent
The module does not try to detect all capabilities of browser in current form (it can easily be extended though).
Aim is
    * fast
    * very easy to extend
    * reliable enough for practical purposes
    * and assist python web apps to detect clients.

Taken from http://pypi.python.org/pypi/httpagentparser (MIT license)
Modified my Ross Peoples for web2py to better support iPhone and iPad.
"""
import sys

class DetectorsHub(dict):
    _known_types = ['os', 'dist', 'flavor', 'browser']

    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        for typ in self._known_types:
            self.setdefault(typ, [])
        self.registerDetectors()

    def register(self, detector):
        if detector.info_type not in self._known_types:
            self[detector.info_type] = [detector]
            self._known_types.insert(detector.order, detector.info_type)
        else:
            self[detector.info_type].append(detector)

    def reorderByPrefs(self, detectors, prefs):
        if prefs is None:
            return []
        elif prefs == []:
            return detectors
        else:
            prefs.insert(0, '')
            def key_name(d):
                return d.name in prefs and prefs.index(d.name) or sys.maxint
            return sorted(detectors, key=key_name)

    def __iter__(self):
        return iter(self._known_types)

    def registerDetectors(self):
        detectors = [v() for v in globals().values() \
                         if DetectorBase in getattr(v, '__mro__', [])]
        for d in detectors:
            if d.can_register:
                self.register(d)


class DetectorBase(object):
    name = "" # "to perform match in DetectorsHub object"
    info_type = "override me"
    result_key = "override me"
    order = 10 # 0 is highest
    look_for = "string to look for"
    skip_if_found = [] # strings if present stop processin
    can_register = False
    is_mobile = False
    prefs = dict() # dict(info_type = [name1, name2], ..)
    version_splitters = ["/", " "]
    _suggested_detectors = None

    def __init__(self):
        if not self.name:
            self.name = self.__class__.__name__
        self.can_register = (self.__class__.__dict__.get('can_register', True))

    def detect(self, agent, result):
        if agent and self.checkWords(agent):
            result[self.info_type] = dict(name=self.name)
            result[self.info_type]['is_mobile'] = self.is_mobile
            if not result.get('is_mobile',None):
                result['is_mobile'] = result[self.info_type]['is_mobile']
                
            version = self.getVersion(agent)
            if version:
                result[self.info_type]['version'] = version
            
            return True
        return False

    def checkWords(self, agent):
        for w in self.skip_if_found:
            if w in agent:
                return False
        if self.look_for in agent:
            return True
        return False

    def getVersion(self, agent):
        # -> version string /None
        vs = self.version_splitters
        return agent.split(self.look_for + vs[0])[-1].split(vs[1])[0].strip()


class OS(DetectorBase):
    info_type = "os"
    can_register = False
    version_splitters = [";", " "]


class Dist(DetectorBase):
    info_type = "dist"
    can_register = False


class Flavor(DetectorBase):
    info_type = "flavor"
    can_register = False


class Browser(DetectorBase):
    info_type = "browser"
    can_register = False


class Macintosh(OS):
    look_for = 'Macintosh'
    prefs = dict(dist=None)
    def getVersion(self, agent):
        pass


class Firefox(Browser):
    look_for = "Firefox"


class Konqueror(Browser):
    look_for = "Konqueror"
    version_splitters = ["/", ";"]


class Opera(Browser):
    look_for = "Opera"
    def getVersion(self, agent):
        return agent.split(self.look_for)[1][1:].split(' ')[0]

class Netscape(Browser):
    look_for = "Netscape"

class MSIE(Browser):
    look_for = "MSIE"
    skip_if_found = ["Opera"]
    name = "Microsoft Internet Explorer"
    version_splitters = [" ", ";"]


class Galeon(Browser):
    look_for = "Galeon"


class Safari(Browser):
    look_for = "Safari"

    def checkWords(self, agent):
        unless_list = ["Chrome", "OmniWeb"]
        if self.look_for in agent:
            for word in unless_list:
                if word in agent:
                    return False
            return True

    def getVersion(self, agent):
        if "Version/" in agent:
            return agent.split('Version/')[-1].split(' ')[0].strip()
        else:
            # Mobile Safari
            return agent.split('Safari ')[-1].split(' ')[0].strip()


class Linux(OS):
    look_for = 'Linux'
    prefs = dict(browser=["Firefox"],
                 dist=["Ubuntu", "Android"], flavor=None)

    def getVersion(self, agent):
        pass


class Macintosh(OS):
    look_for = 'Macintosh'
    prefs = dict(dist=None, flavor=['MacOS'])
    def getVersion(self, agent):
        pass


class MacOS(Flavor):
    look_for = 'Mac OS'
    prefs = dict(browser=['Firefox', 'Opera', "Microsoft Internet Explorer"])

    def getVersion(self, agent):
        version_end_chars = [';', ')']
        part = agent.split('Mac OS')[-1].strip()
        for c in version_end_chars:
            if c in part:
                version = part.split(c)[0]
                break
        return version.replace('_', '.')


class Windows(OS):
    look_for = 'Windows'
    prefs = dict(browser=["Microsoft Internet Explorer", 'Firefox'],
                 dict=None, flavor=None)

    def getVersion(self, agent):
        v = agent.split('Windows')[-1].split(';')[0].strip()
        if ')' in v:
            v = v.split(')')[0]
        return v


class Ubuntu(Dist):
    look_for = 'Ubuntu'
    version_splitters = ["/", " "]
    prefs = dict(browser=['Firefox'])


class Debian(Dist):
    look_for = 'Debian'
    version_splitters = ["/", " "]
    prefs = dict(browser=['Firefox'])


class Chrome(Browser):
    look_for = "Chrome"
    version_splitters = ["/", " "]

class ChromeOS(OS):
    look_for = "CrOS"
    version_splitters = [" ", " "]
    prefs = dict(browser=['Chrome'])
    def getVersion(self, agent):
        vs = self.version_splitters
        return agent.split(self.look_for+vs[0])[-1].split(vs[1])[1].strip()[:-1]

class Android(Dist):
    look_for = 'Android'
    is_mobile = True

    def getVersion(self, agent):
        return agent.split('Android')[-1].split(';')[0].strip()


class iPhone(Dist):
    look_for = 'iPhone'
    is_mobile = True

    def getVersion(self, agent):
        version_end_chars = ['like', ';', ')']
        part = agent.split('CPU OS')[-1].strip()
        for c in version_end_chars:
            if c in part:
                version = 'iOS ' + part.split(c)[0].strip()
                break
        return version.replace('_', '.')

class iPad(Dist):
    look_for = 'iPad'
    is_mobile = True

    def getVersion(self, agent):
        version_end_chars = ['like', ';', ')']
        part = agent.split('CPU OS')[-1].strip()
        for c in version_end_chars:
            if c in part:
                version = 'iOS ' + part.split(c)[0].strip()
                break
        return version.replace('_', '.')

detectorshub = DetectorsHub()

def detect(agent):
    result = dict()
    prefs = dict()
    _suggested_detectors = []
    for info_type in detectorshub:
        if not _suggested_detectors:
            detectors = detectorshub[info_type]
            _d_prefs = prefs.get(info_type, [])
            detectors = detectorshub.reorderByPrefs(detectors, _d_prefs)
            if "detector" in locals():
                detector._suggested_detectors = detectors
        else:
            detectors = _suggested_detectors
        for detector in detectors:
            # print "detector name: ", detector.name
            if detector.detect(agent, result):
                prefs = detector.prefs
                _suggested_detectors = detector._suggested_detectors
                break
    return result


class Result(dict):
    def __missing__(self, k):
        return ""

def simple_detect(agent):
    """
    -> (os, browser, is_mobile) # tuple of strings
    """
    result = detect(agent)
    os_list = []
    if 'flavor' in result: os_list.append(result['flavor']['name'])
    if 'dist' in result: os_list.append(result['dist']['name'])
    if 'os' in result: os_list.append(result['os']['name'])

    os = os_list and " ".join(os_list) or "Unknown OS"
    os_version = os_list and ('flavor' in result and result['flavor'] and result['flavor'].get(
            'version')) or ('dist' in result and result['dist'] and result['dist'].get('version')) \
            or ('os' in result and result['os'] and result['os'].get('version')) or ""
    browser = 'browser' in result and result['browser']['name'] \
        or 'Unknown Browser'
    browser_version = 'browser' in result \
        and result['browser'].get('version') or ""
    if browser_version:
        browser = " ".join((browser, browser_version))
    if os_version:
        os = " ".join((os, os_version))
    #is_mobile = ('dist' in result and result.dist.is_mobile) or ('os' in result and result.os.is_mobile) or False
    return os, browser, result.is_mobile


if __name__ == '__main__':
    import time
    import unittest

    data = (
        ("Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-GB; rv:1.9.0.10) Gecko/2009042315 Firefox/3.0.10",
         ('MacOS Macintosh X 10.5', 'Firefox 3.0.10'),
         {'flavor': {'version': 'X 10.5', 'name': 'MacOS'}, 'os': {'name': 'Macintosh'}, 'browser': {'version': '3.0.10', 'name': 'Firefox'}},),
        ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_6) AppleWebKit/534.24 (KHTML, like Gecko) Chrome/11.0.696.3 Safari/534.24,gzip(gfe)",
         ('MacOS Macintosh X 10.6.6', 'Chrome 11.0.696.3'),
         {'flavor': {'version': 'X 10.6.6', 'name': 'MacOS'}, 'os': {'name': 'Macintosh'}, 'browser': {'version': '11.0.696.3', 'name': 'Chrome'}},),
        ("Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.2) Gecko/20100308 Ubuntu/10.04 (lucid) Firefox/3.6 GTB7.1",
         ('Ubuntu Linux 10.04', 'Firefox 3.6'),
         {'dist': {'version': '10.04', 'name': 'Ubuntu'}, 'os': {'name': 'Linux'}, 'browser': {'version': '3.6', 'name': 'Firefox'}},),
        ("Mozilla/5.0 (Linux; U; Android 2.2.1; fr-ch; A43 Build/FROYO) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1",
         ('Android Linux 2.2.1', 'Safari 4.0'),
         {'dist': {'version': '2.2.1', 'name': 'Android'}, 'os': {'name': 'Linux'}, 'browser': {'version': '4.0', 'name': 'Safari'}},),
        ("Mozilla/5.0 (iPhone; U; CPU like Mac OS X; en) AppleWebKit/420+ (KHTML, like Gecko) Version/3.0 Mobile/1A543a Safari/419.3",
         ('MacOS IPhone X', 'Safari 3.0'),
         {'flavor': {'version': 'X', 'name': 'MacOS'}, 'dist': {'version': 'X', 'name': 'IPhone'}, 'browser': {'version': '3.0', 'name': 'Safari'}},),
        ("Mozilla/5.0 (X11; CrOS i686 0.0.0) AppleWebKit/534.24 (KHTML, like Gecko) Chrome/11.0.696.27 Safari/534.24,gzip(gfe)",
         ('ChromeOS 0.0.0', 'Chrome 11.0.696.27'),
         {'os': {'name': 'ChromeOS', 'version': '0.0.0'}, 'browser': {'name': 'Chrome', 'version': '11.0.696.27'}},),
        ("Mozilla/4.0 (compatible; MSIE 6.0; MSIE 5.5; Windows NT 5.1) Opera 7.02 [en]",
         ('Windows NT 5.1', 'Opera 7.02'),
         {'os': {'name': 'Windows', 'version': 'NT 5.1'}, 'browser': {'name': 'Opera', 'version': '7.02'}},),
        ("Opera/9.80 (X11; Linux i686; U; en) Presto/2.9.168 Version/11.50",
         ("Linux", "Opera 9.80"),
         {"os": {"name": "Linux"}, "browser": {"name": "Opera", "version": "9.80"}},),
        ("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.7.5) Gecko/20060127 Netscape/8.1",
         ("Windows NT 5.1", "Netscape 8.1"),
         {'os': {'name': 'Windows', 'version': 'NT 5.1'}, 'browser': {'name': 'Netscape', 'version': '8.1'}},),
        )

    class TestHAP(unittest.TestCase):
        def setUp(self):
            self.harass_repeat = 1000
            self.data = data

        def test_simple_detect(self):
            for agent, simple_res, res in data:
                self.assertEqual(simple_detect(agent), simple_res)

        def test_detect(self):
            for agent, simple_res, res in data:
                self.assertEqual(detect(agent), res)

        def test_harass(self):
            then = time.time()
            for agent, simple_res, res in data * self.harass_repeat:
                detect(agent)
            time_taken = time.time() - then
            no_of_tests = len(self.data) * self.harass_repeat
            print "\nTime taken for %s detecttions: %s" \
                % (no_of_tests, time_taken)
            print "Time taken for single detecttion: ", \
                time_taken / (len(self.data) * self.harass_repeat)

    unittest.main()


class mobilize(object): 

    def __init__(self, func): 
        self.func = func 

    def __call__(self):
        from gluon import current 
        user_agent = current.request.user_agent()
        if user_agent.is_mobile: 
            items = current.response.view.split('.')
            items.insert(-1,'mobile')
            current.response.view = '.'.join(items)
        return self.func() 
