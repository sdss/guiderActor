#!/usr/bin/env python
# -*- coding:utf-8 -*-

# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2018-05-24
# @Filename: setup.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)
# @Copyright: José Sánchez-Gallego

from setuptools import Extension, setup


module_libguide = Extension(
    'guiderActor.libguide',
    sources=['src/gimg/ipGguide.c', 'src/gimg/gutils.c', 'src/gimg/shUtils.c'],
    include_dirs=['include'])


setup(ext_modules=[module_libguide])
