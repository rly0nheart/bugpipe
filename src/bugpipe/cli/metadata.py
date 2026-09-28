"""
Package metadata, read from the installed distribution.
"""

from importlib.metadata import metadata

pkg_name = "bugpipe"
__metadata = metadata(pkg_name)
author = __metadata["Author"]
description = __metadata["Summary"]
license = __metadata["License-Expression"]
version = __metadata["Version"]
