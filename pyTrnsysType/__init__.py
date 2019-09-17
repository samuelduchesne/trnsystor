# Version of the package
__version__ = "1.1.2-dev"

# warn if a newer version of archetypal is available
from outdated import warn_if_outdated

warn_if_outdated("pyTrnsysType", __version__)

from .utils import *
from .trnsymodel import *
from .input_file import *
