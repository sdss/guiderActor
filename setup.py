#!/usr/bin/env python
# -*- coding:utf-8 -*-

# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2018-05-24
# @Filename: setup.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
# @Copyright: José Sánchez-Gallego

import os
from distutils.command.build import build
from distutils.core import Extension, setup


module_libguide = Extension('libguide',
                            sources=['src/gimg/ipGguide.c',
                                     'src/gimg/gutils.c',
                                     'src/gimg/shUtils.c'],
                            include_dirs=['include'])


class GuiderActorBuild(build):
    """Custom build command."""

    def run(self):
        build.run(self)
        os.symlink(self.build_lib, os.path.join(os.path.dirname(__file__), 'lib'))


setup(name='guiderActor',
      version='3.9.5dev',
      description='The SDSS guider actor',
      maintainer='Jose Sanchez-Gallego',
      maintainer_email='gallegoj@uw.edu',
      url='https://github.com/sdss/guiderActor',
      ext_modules=[module_libguide],
      cmdclass={'build': GuiderActorBuild})
