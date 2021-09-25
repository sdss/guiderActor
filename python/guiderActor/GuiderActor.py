#!/usr/bin/env python
"""An actor to run the guider"""

import abc
import os

import actorcore.Actor
import gcameraThread
import GuiderState
import masterThread
import movieThread
import opscore.actor.keyvar
import opscore.actor.model

import guiderActor
from guiderActor import myGlobals


def set_default_pids(config, gState):
    """Set the PID value defaults from the config file."""

    axes = dict(RADEC='raDec', ROT='rot', FOCUS='focus', SCALE='scale')
    for axis in config.options('PID'):
        axis = axes[axis.upper()]
        Kp, Ti_min, Ti_max, Td, Imax, nfilt = [float(v) for v in config.get('PID', axis).split()]
        gState.set_pid_defaults(axis,
                                Kp=Kp,
                                Ti_min=Ti_min,
                                Ti_max=Ti_max,
                                Td=Td,
                                Imax=Imax,
                                nfilt=int(nfilt))
        gState.pid[axis].setPID(Kp=Kp, Ti=Ti_min, Td=Td, Imax=Imax, nfilt=nfilt)


def set_pid_scaling(config, gState):
    """Set the min/max altitude and the axes to scale the PID terms on."""

    gState.axes_to_scale = config.get('PID_altitude_scale', 'axes').split()
    gState.alt_min = float(config.get('PID_altitude_scale', 'min'))
    gState.alt_max = float(config.get('PID_altitude_scale', 'max'))


def set_telescope(config, gState):
    """Set values related to the telescope from the config file."""

    gState.plugPlateScale = float(config.get('telescope', 'scale'))
    gState.dSecondary_dmm = float(config.get('telescope', 'dSecondary_dmm'))
    gState.longitude = float(config.get('telescope', 'longitude'))
    gState.focalRatio = float(config.get('telescope', 'focalRatio'))


def set_gcamera(config, gState):
    """Set values related to the guide camera from the config file."""

    # expTime = float(config.get('gcamera', 'exposureTime'))
    # readTime = float(config.get('gcamera', 'binnedReadTime'))
    # masterThread.set_time(gState, expTime, 1, readTime)
    gState.gcameraPixelSize = float(config.get('gcamera', 'pixelSize'))
    gState.gcameraMagnification = float(config.get('gcamera', 'magnification'))


class GuiderActor(actorcore.Actor.SDSSActor):
    """Manage the threads that calculate guiding corrections and gcamera commands."""

    __metaclass__ = abc.ABCMeta

    @staticmethod
    def newActor(location=None, **kwargs):
        """Return the version of the actor based on our location."""
        location = GuiderActor._determine_location(location)
        if location == 'APO':
            return GuiderActorAPO('guider', productName='guiderActor', **kwargs)
        elif location == 'LCO':
            raise ValueError('this actor cannot be run at LCO')
        elif location == 'LOCAL':
            return GuiderActorLocal('guider', productName='guiderActor', **kwargs)
        else:
            raise KeyError('Don\'t know my location: cannot return a working Actor!')

    def __init__(self, name, debugLevel=30, productName=None, makeCmdrConnection=True):

        actorcore.Actor.Actor.__init__(self,
                                       name,
                                       productName=productName,
                                       makeCmdrConnection=makeCmdrConnection)

        self.version = guiderActor.__version__

        self.logger.setLevel(debugLevel)
        self.logger.propagate = True

        # Tests that lib/libguide.so exists.
        libguide_path = os.path.expandvars('$GUIDERACTOR_DIR/python/guiderActor/libguide.so')
        assert os.path.exists(libguide_path), ('cannot find libguide.so. Was it compiled '
                                               'and linked in '
                                               '$GUIDERACTOR_DIR/python/guiderActor/libguide.so?')

        # guiderActor.myGlobals.actorState = actorcore.Actor.ActorState(self)
        # actorState = guiderActor.myGlobals.actorState
        # self.actorState = actorState
        # actorState.gState = GuiderState.GuiderState()
        # actorState.actorConfig = self.config
        # gState = actorState.gState

        # Define thread list
        self.threadList = [
            ('master', guiderActor.MASTER, masterThread),
            ('gcamera', guiderActor.GCAMERA, gcameraThread),
            ('movie', guiderActor.MOVIE, movieThread),
        ]

        # Load other actor's models so we can send it commands
        # And ours: we use the models to generate the FITS cards.
        self.models = {}
        for actor in ['ecamera', 'mcp', 'tcc', 'guider', 'apo']:
            self.models[actor] = opscore.actor.model.Model(actor)

        self.actorState = actorcore.Actor.ActorState(self, self.models)
        self.actorState.gState = GuiderState.GuiderState()
        self.actorState.actorConfig = self.config
        myGlobals.actorState = self.actorState
        self.actorState.timeout = 60  # timeout on message queues
        gState = self.actorState.gState

        for what in self.config.options('enable'):
            enable = {'True': True, 'False': False}[self.config.get('enable', what)]
            gState.setGuideMode(what, enable)

        set_default_pids(self.config, gState)
        set_pid_scaling(self.config, gState)
        set_telescope(self.config, gState)
        set_gcamera(self.config, gState)

        gState.fitting_algorithm = self.config.get('general', 'fitting_algorithm')


class GuiderActorAPO(GuiderActor):
    """APO version of this actor."""

    location = 'APO'

    def guidingIsOK(self, cmd, actorState, force=False):
        """Is it OK to be guiding?"""

        return True


class GuiderActorLocal(GuiderActor):
    """Test version of this actor. In prnciple, inherits from GuiderActorAPO."""

    location = 'LOCAL'

    def guidingIsOk(self, cmd, actorState, force=False):
        return True
