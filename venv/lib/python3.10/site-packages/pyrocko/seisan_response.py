
"""
This module has been moved to :py:mod:`pyrocko.io.seisan_response`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.seisan_response\n')
    sys.stderr.write('           -> should now use: pyrocko.io.seisan_response\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.seisan_response\n')
    sys.stderr.write('              -> should now use: pyrocko.io.seisan_response\n\n')
    raise ImportError('Pyrocko module "pyrocko.seisan_response" has been renamed to "pyrocko.io.seisan_response".')

from pyrocko.io.seisan_response import *
