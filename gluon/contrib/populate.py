# from web2py

from __future__ import print_function
from pydal._compat import pickle, unicodeT
import sys
import re
import random
import datetime

IUP = {'ad': {'minim': 1}, 'irure': {'dolor': 1}, 'in': {'voluptate': 1, 'reprehenderit': 1, 'culpa': 1}, 'ea': {'commodo': 1}, 'excepteur': {'sint': 1}, 'sunt': {'in': 1}, 'elit': {'sed': 1}, 'duis': {'aute': 1}, 'sed': {'do': 1}, 'eiusmod': {'tempor': 1}, 'enim': {'ad': 1}, 'eu': {'fugiat': 1}, 'et': {'dolore': 1}, 'labore': {'et': 1}, 'incididunt': {'ut': 1}, 'reprehenderit': {'in': 1}, 'est': {'laborum': 1}, 'quis': {'nostrud': 1}, 'sit': {'amet': 1}, 'deserunt': {'mollit': 1}, 'nostrud': {'exercitation': 1}, 'qui': {'officia': 1}, '.': {'excepteur': 1, 'ut': 1, 'duis': 1}, 'consectetur': {'adipiscing': 1}, 'aute': {'irure': 1}, 'dolore': {'eu': 1, 'magna': 1}, 'mollit': {'anim': 1}, 'aliquip': {'ex': 1}, 'nulla': {'pariatur': 1}, 'laborum': {'': 1}, 'do': {'eiusmod': 1}, 'non': {'proident': 1}, 'commodo': {'consequat': 1}, 'aliqua': {'.': 1}, 'cillum': {'dolore': 1}, 'sint': {'occaecat': 1}, 'velit': {'esse': 1}, 'officia': {'deserunt': 1}, 'veniam': {'quis': 1}, 'consequat': {'.': 1}, 'magna': {'aliqua': 1}, 'cupidatat': {'non': 1}, 'ullamco': {'laboris': 1}, 'lorem': {'ipsum': 1}, 'amet': {'consectetur': 1}, 'ipsum': {'dolor': 1}, 'nisi': {'ut': 1}, 'fugiat': {'nulla': 1}, 'occaecat': {'cupidatat': 1}, 'proident': {'sunt': 1}, 'ut': {'aliquip': 1, 'labore': 1, 'enim': 1}, 'minim': {'veniam': 1}, 'culpa': {'qui': 1}, 'tempor': {'incididunt': 1}, 'pariatur': {'.': 1}, 'laboris': {'nisi': 1}, 'anim': {'id': 1}, 'adipiscing': {'elit': 1}, 'id': {'est': 1}, 'dolor': {'in': 1, 'sit': 1}, 'voluptate': {'velit': 1}, 'esse': {'cillum': 1}, 'exercitation': {'ullamco': 1}, 'ex': {'ea': 1}}

FIRST_NAMES = "James,John,Robert,Michael,William,David,Richard,Charles,Joseph,Thomas,Christopher,Daniel,Paul,Mark,Donald,George,Kenneth,Steven,Edward,Brian,Ronald,Anthony,Kevin,Jason,Matthew,Gary,Timothy,Jose,Larry,Jeffrey,Frank,Scott,Eric,Stephen,Andrew,Raymond,Gregory,Joshua,Jerry,Dennis,Walter,Patrick,Peter,Harold,Douglas,Henry,Carl,Arthur,Ryan,Roger,Joe,Juan,Jack,Albert,Jonathan,Justin,Terry,Gerald,Keith,Samuel,Willie,Ralph,Lawrence,Nicholas,Roy,Benjamin,Bruce,Brandon,Adam,Harry,Fred,Wayne,Billy,Steve,Louis,Jeremy,Aaron,Randy,Howard,Eugene,Carlos,Russell,Bobby,Victor,Martin,Ernest,Phillip,Todd,Jesse,Craig,Alan,Shawn,Clarence,Sean,Philip,Chris,Johnny,Earl,Jimmy,Antonio,Danny,Bryan,Tony,Luis,Mike,Stanley,Leonard,Nathan,Dale,Manuel,Rodney,Curtis,Norman,Allen,Marvin,Vincent,Glenn,Jeffery,Travis,Jeff,Chad,Jacob,Lee,Melvin,Alfred,Kyle,Francis,Bradley,Jesus,Herbert,Frederick,Ray,Joel,Edwin,Don,Eddie,Ricky,Troy,Randall,Barry,Alexander,Bernard,Mario,Leroy,Francisco,Marcus,Micheal,Theodore,Clifford,Miguel,Oscar,Jay,Jim,Tom,Calvin,Alex,Jon,Ronnie,Bill,Lloyd,Tommy,Leon,Derek,Warren,Darrell,Jerome,Floyd,Leo,Alvin,Tim,Wesley,Gordon,Dean,Greg,Jorge,Dustin,Pedro,Derrick,Dan,Lewis,Zachary,Corey,Herman,Maurice,Vernon,Roberto,Clyde,Glen,Hector,Shane,Ricardo,Sam,Rick,Lester,Brent,Ramon,Charlie,Tyler,Gilbert,Gene,Marc,Reginald,Ruben,Brett,Angel,Nathaniel,Rafael,Leslie,Edgar,Milton,Raul,Ben,Chester,Cecil,Duane,Franklin,Andre,Elmer,Brad,Gabriel,Ron,Mitchell,Roland,Arnold,Harvey,Jared,Adrian,Karl,Cory,Claude,Erik,Darryl,Jamie,Neil,Jessie,Christian,Javier,Fernando,Clinton,Ted,Mathew,Tyrone,Darren,Lonnie,Lance,Cody,Julio,Kelly,Kurt,Allan,Nelson,Guy,Clayton,Hugh,Max,Dwayne,Dwight,Armando,Felix,Jimmie,Everett,Jordan,Ian,Wallace,Ken,Bob,Jaime,Casey,Alfredo,Alberto,Dave,Ivan,Johnnie,Sidney,Byron,Julian,Isaac,Morris,Clifton,Willard,Daryl,Ross,Virgil,Andy,Marshall,Salvador,Perry,Kirk,Sergio,Marion,Tracy,Seth,Kent,Terrance,Rene,Eduardo,Terrence,Enrique,Freddie,Wade,Austin,Stuart,Fredrick,Arturo,Alejandro,Jackie,Joey,Nick,Luther,Wendell,Jeremiah,Evan,Julius,Dana,Donnie,Otis,Shannon,Trevor,Oliver,Luke,Homer,Gerard,Doug,Kenny,Hubert,Angelo"

LAST_NAMES="Smith,Johnson,Williams,Jones,Brown,Davis,Miller,Wilson,Moore,Taylor,Anderson,Thomas,Jackson,White,Harris,Martin,Thompson,Garcia,Martinez,Robinson,Clark,Rodriguez,Lewis,Lee,Walker,Hall,Allen,Young,Hernandez,King,Wright,Lopez,Hill,Scott,Green,Adams,Baker,Gonzalez,Nelson,Carter,Mitchell,Perez,Roberts,Turner,Phillips,Campbell,Parker,Evans,Edwards,Collins,Stewart,Sanchez,Morris,Rogers,Reed,Cook,Morgan,Bell,Murphy,Bailey,Rivera,Cooper,Richardson,Cox,Howard,Ward,Torres,Peterson,Gray,Ramirez,James,Watson,Brooks,Kelly,Sanders,Price,Bennett,Wood,Barnes,Ross,Henderson,Coleman,Jenkins,Perry,Powell,Long,Patterson,Hughes,Flores,Washington,Butler,Simmons,Foster,Gonzales,Bryant,Alexander,Russell,Griffin,Diaz,Hayes,Myers,Ford,Hamilton,Graham,Sullivan,Wallace,Woods,Cole,West,Jordan,Owens,Reynolds,Fisher,Ellis,Harrison,Gibson,Mcdonald,Cruz,Marshall,Ortiz,Gomez,Murray,Freeman,Wells,Webb,Simpson,Stevens,Tucker,Porter,Hunter,Hicks,Crawford,Henry,Boyd,Mason,Morales,Kennedy,Warren,Dixon,Ramos,Reyes,Burns,Gordon,Shaw,Holmes,Rice,Robertson,Hunt,Black,Daniels,Palmer,Mills,Nichols,Grant,Knight,Ferguson,Rose,Stone,Hawkins,Dunn,Perkins,Hudson,Spencer,Gardner,Stephens,Payne,Pierce,Berry,Matthews,Arnold,Wagner,Willis,Ray,Watkins,Olson,Carroll,Duncan,Snyder,Hart,Cunningham,Bradley,Lane,Andrews,Ruiz,Harper,Fox,Riley,Armstrong,Carpenter,Weaver,Greene,Lawrence,Elliott,Chavez,Sims,Austin,Peters,Kelley,Franklin,Lawson,Fields,Gutierrez,Ryan,Schmidt,Carr,Vasquez,Castillo,Wheeler,Chapman,Oliver,Montgomery,Richards,Williamson,Johnston,Banks,Meyer,Bishop,Mccoy,Howell,Alvarez,Morrison,Hansen,Fernandez,Garza,Harvey,Little,Burton,Stanley,Nguyen,George,Jacobs,Reid,Kim,Fuller,Lynch,Dean,Gilbert,Garrett,Romero,Welch,Larson,Frazier,Burke,Hanson,Day,Mendoza,Moreno,Bowman,Medina,Fowler,Brewer,Hoffman,Carlson,Silva,Pearson,Holland,Douglas,Fleming,Jensen,Vargas,Byrd,Davidson,Hopkins,May,Terry,Herrera,Wade,Soto,Walters"

class Learner:
    def __init__(self):
        self.db = {}

    def learn(self, text):
        replacements1 = {'[^a-zA-Z0-9\.;:\-]': ' ',
                         '\s+': ' ', ', ': ' , ', '\. ': ' . ',
                         ': ': ' : ', '; ': ' ; '}
        for key, value in replacements1.items():
            text = re.sub(key, value, text)
        items = [item.lower() for item in text.split(' ')]
        for i in range(len(items) - 1):
            item = items[i]
            nextitem = items[i + 1]
            if item not in self.db:
                self.db[item] = {}
            if nextitem not in self.db[item]:
                self.db[item][nextitem] = 1
            else:
                self.db[item][nextitem] += 1

    def save(self, filename):
        with open(filename, 'wb') as fp:
            pickle.dump(self.db, fp)

    def load(self, filename):
        with open(filename, 'rb') as fp:
            self.loadd(pickle.load(fp))

    def loadd(self, db):
        self.db = db

    def generate(self, length=10000, prefix=False):
        replacements2 = {' ,': ',', ' \.': '.\n', ' :': ':', ' ;':
                         ';', '\n\s+': '\n'}
        keys = list(self.db.keys())
        key = keys[random.randint(0, len(keys) - 1)]
        words = key
        words = words.capitalize()
        regex = re.compile('[a-z]+')
        for i in range(length):
            okey = key
            if not key in self.db:
                break  # should not happen
            db = self.db[key]
            s = sum(db.values())
            i = random.randint(0, s - 1)
            for key, value in db.items():
                if i < value:
                    break
                else:
                    i -= value
            if okey == '.':
                key1 = key.capitalize()
            else:
                key1 = key
            if prefix and regex.findall(key1) and \
                    random.random() < 0.01:
                key1 = '<a href="%s%s">%s</a>' % (prefix, key1, key1)
            words += ' ' + key1
        text = words
        for key, value in replacements2.items():
            text = re.sub(key, value, text)
        return text + '.\n'


def da_du_ma(n=4):
    return ''.join([['da', 'du', 'ma', 'mo', 'ce', 'co',
                     'pa', 'po', 'sa', 'so', 'ta', 'to']
                    [random.randint(0, 11)] for i in range(n)])


def populate(table, n=None, default=True, compute=False, contents=None, ell=None):
    """Populate table with n records.

    if n is None, it does not populate the database but returns a generator
    if default=True use default values to fields.
    if compute=False doesn't load values into computed fields.
    if contents has data, use these values to populate related fields.

    can be used in two ways:

    >>> populate(db.tablename, n=100)

    or

    >>> for k,row in enumerate(populate(db.tablename)): print row
    """

    contents = contents or {}

    generator = populate_generator(table, default=default,
                                   compute=compute, contents=contents, ell=None)
    if n is not None:
        for k,record in enumerate(generator):
            if k>=n: break
            table.insert(**record)
        table._db.commit()

    return generator

def populate_generator(table, default=True, compute=False, contents=None, ell=None):
    """Populate table with n records.

    if default=True use default values to fields.
    if compute=False doesn't load values into computed fields.
    if contents has data, use these values to populate related fields.
    """
    contents = contents or {}

    if not ell:
        ell = Learner()
        ell.loadd(IUP)

    ids = {}

    while True:
        record = contents.copy() # load user supplied contents.

        for fieldname in table.fields:
            if fieldname in record:
                continue # if user supplied it, let it be.

            field = table[fieldname]
            if not isinstance(field.type, (str, unicodeT)):
                continue
            elif field.type == 'id':
                continue
            elif field.type == 'upload':
                continue
            elif field.compute is not None:
                continue
            elif default and not field.default in (None, ''):
                record[fieldname] = field.default
            elif compute and field.compute:
                continue
            elif field.type == 'boolean':
                record[fieldname] = random.random() > 0.5
            elif field.type == 'date':
                record[fieldname] = \
                    datetime.date(2009, 1, 1) - \
                    datetime.timedelta(days=random.randint(0, 365))
            elif field.type == 'datetime':
                record[fieldname] = \
                    datetime.datetime(2009, 1, 1) - \
                    datetime.timedelta(days=random.randint(0, 365))
            elif field.type == 'time':
                h = random.randint(0, 23)
                m = 15 * random.randint(0, 3)
                record[fieldname] = datetime.time(h, m, 0)
            elif field.type == 'password':
                record[fieldname] = ''
            elif field.type == 'integer' and \
                    hasattr(field.requires, 'options'):
                options = field.requires.options(zero=False)
                if len(options) > 0:
                    record[fieldname] = options[
                        random.randint(0, len(options) - 1)][0]
                else:
                    record[fieldname] = None
            elif field.type == 'list:integer' and hasattr(field.requires, 'options'):
                options = field.requires.options(zero=False)
                if len(options) > 0:
                    record[fieldname] = [item[0] for item in random.sample(
                        options, random.randint(0, len(options) - 1) / 2)]
            elif field.type == 'integer':
                try:
                    record[fieldname] = random.randint(
                        field.requires.minimum, field.requires.maximum - 1)
                except:
                    if 'day' in  fieldname:
                        record[fieldname] = random.randint(1,28)
                    elif 'month' in fieldname:
                        record[fieldname] =random.randint(1,12)
                    elif 'year' in fieldname:
                        record[fieldname] =random.randint(2000,2013)
                    else:
                        record[fieldname] = random.randint(0, 1000)
            elif field.type == 'double' \
                    or str(field.type).startswith('decimal'):
                if hasattr(field.requires, 'minimum'):
                    rand = random.random()
                    if str(field.type).startswith('decimal'):
                        import decimal
                        rand = decimal.Decimal(rand)
                    record[fieldname] = field.requires.minimum + \
                        rand * (field.requires.maximum -
                                field.requires.minimum)
                else:
                    record[fieldname] = random.random() * 1000
            elif field.type[:10] == 'reference ':
                tablename = field.type[10:]
                if not tablename in ids:
                    if table._db._dbname == 'gql':
                        ids[tablename] = [x.id for x in table._db(
                            table._db[field.type[10:]].id > 0).select()]
                    else:
                        ids[tablename] = [x.id for x in table._db(
                            table._db[field.type[10:]].id > 0).select()]
                n = len(ids[tablename])
                if n:
                    record[fieldname] = \
                        ids[tablename][random.randint(0, n - 1)]
                else:
                    record[fieldname] = 0
            elif field.type[:15] == 'list:reference ':
                tablename = field.type[15:]
                if not tablename in ids:
                    if table._db._dbname == 'gql':
                        ids[tablename] = [x.id for x in table._db(
                            table._db[field.type[15:]].id > 0).select()]
                    else:
                        ids[tablename] = [x.id for x in table._db(
                            table._db[field.type[15:]].id > 0).select()]
                n = len(ids[tablename])
                if n:
                    record[fieldname] = [item for item in random.sample(
                        ids[tablename], random.randint(0, n - 1) / 2)]
                else:
                    record[fieldname] = 0
            elif field.type == 'list:string' \
                    and hasattr(field.requires, 'options'):
                options = field.requires.options(zero=False)
                if len(options) > 0:
                    record[fieldname] = [item[0] for item in random.sample(
                        options, random.randint(0, len(options) - 1) / 2)]
            elif field.type == 'string':
                if hasattr(field.requires, 'options'):
                    options = field.requires.options(zero=False)
                    record[fieldname] = \
                        options[random.randint(0, len(options) - 1)][0]
                elif fieldname.find('url') >= 0:
                    record[fieldname] = 'http://%s.example.com' % \
                        da_du_ma(4)
                elif fieldname.find('email') >= 0:
                    record[fieldname] = '%s@example.com' % da_du_ma(4)
                elif fieldname.find('name')>=0:
                    if fieldname.find('first')>=0:
                        record[fieldname] = random.choice(FIRST_NAMES)
                    elif fieldname.find('last')>=0:
                        record[fieldname] = random.choice(LAST_NAMES)
                    elif fieldname.find('username')>=0:
                        record[fieldname] = random.choice(FIRST_NAMES).lower()+str(random.randint(1000,9999))
                    else:
                        record[fieldname] = random.choice(FIRST_NAMES)+' '+random.choice(LAST_NAMES)
                elif fieldname.find('phone')>=0:
                    record[fieldname] = '(%s%s%s) %s%s%s-%s%s%s%s' % (
                        random.choice('1234567890'),random.choice('1234567890'),random.choice('1234567890'),random.choice('1234567890'),random.choice('1234567890'),random.choice('1234567890'),random.choice('1234567890'),random.choice('1234567890'),random.choice('1234567890'),random.choice('1234567890'))
                elif fieldname.find('address') >=0:
                    record[fieldname] = '%s %s %s Street' % (random.randint(1000,9000),random.choice(FIRST_NAMES),random.choice(LAST_NAMES))
                else:
                    z = ell.generate(10, prefix=False)
                    record[fieldname] = z[:min(60,field.length)].replace('\n', ' ')
            elif field.type == 'text':
                if fieldname.find('address')>=0:
                    record[fieldname] = '%s %s %s Street\nChicago, IL\nUSA' % (random.randint(1000,9000),random.choice(FIRST_NAMES),random.choice(LAST_NAMES))
                else:
                    record[fieldname] = ell.generate(
                        random.randint(10, 100), prefix=None)
        yield record

if __name__ == '__main__':
    ell = Learner()
    ell.db = IUP
    if len(sys.argv) > 1:
        ell.learn(open(sys.argv[1]).read())
        print(ell.db)
    print(ell.generate(100))
