import os
import sys

sys.path.append(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "pydal"))

import pydal
sys.modules['pydal'] = pydal
