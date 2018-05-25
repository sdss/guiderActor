# !usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Licensed under a 3-clause BSD license.
#
# @Author: Brian Cherinka
# @Date:   2016-06-10 22:10:30
# @Last modified by:   Brian
# @Last Modified time: 2016-06-10 22:53:14

from __future__ import absolute_import, division, print_function

import opscore.protocols.keys as keys
import opscore.protocols.types as types
import opscore.utility.YPF as YPF
from guiderActor.Commands import GuiderCmd
from opscore.utility.qstr import qstr


class GuiderCmd_LOCAL(GuiderCmd.GuiderCmd):

    def __init__(self, actor):
        # initialize from the superclass
        super(GuiderCmd_LOCAL, self).__init__(actor)

        # Define some new command keywords

        # Define new commands for Local
        pass
