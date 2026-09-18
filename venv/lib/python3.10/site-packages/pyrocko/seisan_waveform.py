
"""
This module has been moved to :py:mod:`pyrocko.io.seisan_waveform`.
"""
import sys
import pyrocko
if pyrocko.grumpy == 1:
    sys.stderr.write('using renamed pyrocko module: pyrocko.seisan_waveform\n')
    sys.stderr.write('           -> should now use: pyrocko.io.seisan_waveform\n\n')
elif pyrocko.grumpy == 2:
    sys.stderr.write('pyrocko module has been renamed: pyrocko.seisan_waveform\n')
    sys.stderr.write('              -> should now use: pyrocko.io.seisan_waveform\n\n')
    raise ImportError('Pyrocko module "pyrocko.seisan_waveform" has been renamed to "pyrocko.io.seisan_waveform".')

from pyrocko.io.seisan_waveform import *
