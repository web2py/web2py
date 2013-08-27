from pickle import Pickler, MARK, DICT, EMPTY_DICT
from types import DictionaryType

def save_dict(self, obj):
     self.write(EMPTY_DICT if self.bin else MARK+DICT)
     self.memoize(obj)
     self._batch_setitems([(key,obj[key]) for key in sorted(obj)])

Pickler.dispatch[DictionaryType] = save_dict          
