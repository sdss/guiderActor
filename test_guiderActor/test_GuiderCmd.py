"""
Tests of the GuiderCmd functions, without executing any threads.

Each of these tests should confirm that a Guidermd command call calls the
correct queue with the correct parameters.

If these tests work correctly, each masterThread function should work
correctly when called via a GuiderCmd (assuming test_masterThread clears).
"""
import unittest
from Queue import Queue

import guiderTester
from actorcore import TestHelper

import guiderActor
import guiderActor.myGlobals as myGlobals
from guiderActor import masterThread
from guiderActor.Commands import GuiderCmd


class GuiderCmdTester(guiderTester.GuiderTester, unittest.TestCase):

    def setUp(self):
        self.verbose = True
        #self.actor = TestHelper.FakeActor('guider','guiderActor')
        super(GuiderCmdTester, self).setUp()
        self.timeout = 1
        # Do this after super setUp, as that's what creates actorState.
        self.queues = {}
        self.queues[guiderActor.MASTER] = Queue('master')
        myGlobals.actorState.queues = self.queues
        self.guiderCmd = GuiderCmd.GuiderCmd(self.actor)
        #print('actor', self.actor.commandSets.keys())


class GuiderAPOCmdTester(GuiderCmdTester):

    def setUp(self):
        self.name = 'guider'
        super(GuiderAPOCmdTester, self).setUp()
        self.actor = TestHelper.FakeActor(self.name, self.name + 'Actor', location='APO')
        self.guidercmd = self.actor.commandSets['GuiderCmd_APO']

    def test_ping(self):
        """Ping just finishes."""
        self._run_cmd('ping', None)
        self._check_cmd(0, 1, 0, 0, True)


class GuiderLCOCmdTester(GuiderCmdTester):

    def setUp(self):
        self.name = 'guider'
        super(GuiderLCOCmdTester, self).setUp()
        self.actor = TestHelper.FakeActor(self.name, self.name + 'Actor', location='LCO')
        self.guidercmd = self.actor.commandSets['GuiderCmd_LCO']

    def test_ping(self):
        """Ping just finishes."""
        self._run_cmd('ping', None)
        self._check_cmd(0, 1, 0, 0, True)


class GuiderLocalCmdTester(GuiderCmdTester):

    def setUp(self):
        self.name = 'guider'
        super(GuiderLocalCmdTester, self).setUp()
        self.actor = TestHelper.FakeActor(self.name, self.name + 'Actor', location='LOCAL')
        self.guidercmd = self.actor.commandSets['GuiderCmd_LOCAL']

    def test_ping(self):
        """Ping just finishes."""
        self._run_cmd('ping', None)
        self._check_cmd(0, 1, 0, 0, True)


class TestDecentering(GuiderCmdTester, unittest.TestCase):
    """mangaDither, decenter on/off, setDecenter."""

    def _mangaDither(self, expect, args):
        queue = self.queues[guiderActor.MASTER]
        msg = self._run_cmd('mangaDither %s' % (args), queue)
        self.assertEqual(msg.type, guiderActor.Msg.DECENTER)
        self.assertEqual(msg.decenters['decenterRA'], expect['decenterRA'])
        self.assertEqual(msg.decenters['decenterDec'], expect['decenterDec'])
        self.assertEqual(msg.decenters['decenterRot'], expect['decenterRot'])
        self.assertEqual(msg.decenters['mangaDither'], expect['mangaDither'])

    def test_mangaDither_C(self):
        expect = {'decenterRA': 0, 'decenterDec': 0, 'decenterRot': 0, 'mangaDither': 'C'}
        self._mangaDither(expect, 'ditherPos=C')

    def test_mangaDither_N(self):
        expect = {'decenterRA': -0.417, 'decenterDec': 0.721, 'decenterRot': 0, 'mangaDither': 'N'}
        self._mangaDither(expect, 'ditherPos=N')

    def test_mangaDither_S(self):
        expect = {
            'decenterRA': -0.417,
            'decenterDec': -0.721,
            'decenterRot': 0,
            'mangaDither': 'S'
        }
        self._mangaDither(expect, 'ditherPos=S')

    def test_mangaDither_E(self):
        expect = {'decenterRA': 0.833, 'decenterDec': 0, 'decenterRot': 0, 'mangaDither': 'E'}
        self._mangaDither(expect, 'ditherPos=E')

    def _decenter(self, expect, args):
        queue = self.queues[guiderActor.MASTER]
        msg = self._run_cmd('decenter %s' % (args), queue)
        self.assertEqual(msg.type, guiderActor.Msg.DECENTER)
        self.assertEqual(msg.enable, expect['on'])
        self.assertIsNone(getattr(msg, 'finish', None))

    def test_decenter_on(self):
        expect = {'on': True}
        self._decenter(expect, 'on')

    def test_decenter_off(self):
        expect = {'on': False}
        self._decenter(expect, 'off')

    def _setDecenter(self, expect, args, didFail=False):
        queue = self.queues[guiderActor.MASTER]
        if didFail:
            with self.assertRaises(AttributeError):
                msg = self._run_cmd('setDecenter %s' % (args), None, empty=True)
                self.assertEquals(msg, None)
                self._check_cmd(0, 0, 0, 0, True, True)
                self.assertTrue(msg.finish)
        else:
            msg = self._run_cmd('setDecenter %s' % (args), queue)
            self.assertEqual(msg.type, guiderActor.Msg.DECENTER)
            self.assertIsNone(getattr(msg, 'finish', None))
            self.assertEqual(msg.decenters['decenterRA'], expect.get('decenterRA', 0))
            self.assertEqual(msg.decenters['decenterDec'], expect.get('decenterDec', 0))

    def test_setDecenter_ra(self):
        expect = {'decenterRA': 10}
        self._setDecenter(expect, 'decenterRA=10')

    def test_setDecenter_dec(self):
        expect = {'decenterDec': 10}
        self._setDecenter(expect, 'decenterDec=10')

    def test_setDecenter_rot(self):
        self._setDecenter({}, 'decenterRot=10', didFail=True)


class TestSetRefractionBalance(GuiderCmdTester, unittest.TestCase):

    def _setRefractionBalance(self, args, expect, didFail=False):
        queue = self.queues[guiderActor.MASTER]
        msg = self._run_cmd('setRefractionBalance %s' % (args), queue)
        self.assertEqual(msg.type, guiderActor.Msg.SET_REFRACTION)

        result = masterThread.set_refraction(self.cmd,
                                             self.gState,
                                             corrRatio=msg.corrRatio,
                                             plateType=msg.plateType,
                                             surveyMode=msg.surveyMode)

        self.assertEqual(self.gState.refractionBalance, expect.get('corrRatio', None))
        self.assertEqual(result, not didFail)

    def test_corrRatio_1(self):
        self.gState.refractionBalance = 0
        args = 'corrRatio=1'
        expect = {'corrRatio': 1}
        self._setRefractionBalance(args, expect)

    def test_corrRatio_fails(self):
        self.gState.refractionBalance = 0
        args = 'corrRatio=10'
        expect = {'corrRatio': 0}
        self._setRefractionBalance(args, expect, didFail=True)

    def test_apogee2(self):

        self.gState.refractionBalance = 0
        args = 'plateType=APOGEE-2 surveyMode=None'
        expect = {'corrRatio': 1}
        self._setRefractionBalance(args, expect, didFail=False)

    def test_bad_input(self):

        self.gState.refractionBalance = 0
        args = ''
        expect = {'corrRatio': 0}
        self._setRefractionBalance(args, expect, didFail=True)


class TestGuideOnOff(GuiderCmdTester, unittest.TestCase):

    def _guideOn(self, args, expect={}):
        queue = self.queues[guiderActor.MASTER]
        msg = self._run_cmd('on %s' % (args), queue)
        self.assertEqual(msg.type, guiderActor.Msg.START_GUIDING)
        self.assertEqual(msg.expTime, expect.get('time', None))
        self.assertEqual(msg.stack, expect.get('stack', 1))
        self.assertEqual(msg.oneExposure, expect.get('oneExposure', False))
        self.assertEqual(msg.force, expect.get('force', False))
        self.assertEqual(msg.camera, expect.get('camera', 'gcamera'))

    def test_guideOn(self):
        self._guideOn('')

    def test_guideOn_force(self):
        self._guideOn('force', {'force': True})

    def test_guideOn_time(self):
        self._guideOn('time=15', {'time': 15})

    def test_guideOn_oneExposure(self):
        self._guideOn('oneExposure', {'oneExposure': True})

    def test_guideOn_stack(self):
        self._guideOn('stack=3', {'stack': 3})

    def test_guideOn_ecam(self):
        self.gState.plateType = 'ecamera'
        self._guideOn('', {'camera': 'ecamera'})

    def test_guideOff(self):
        queue = self.queues[guiderActor.MASTER]
        msg = self._run_cmd('off', queue)
        self.assertEqual(msg.type, guiderActor.Msg.STOP_GUIDING)


class TestEcam(GuiderCmdTester, unittest.TestCase):

    def _findstar(self, args, expect={}):
        queue = self.queues[guiderActor.MASTER]
        msg = self._run_cmd('findstar %s' % (args), queue)
        self.assertEqual(msg.type, guiderActor.Msg.START_GUIDING)
        self.assertEqual(msg.expTime, expect.get('time', 5))
        self.assertEqual(msg.bin, expect.get('bin', 1))
        self.assertEqual(msg.oneExposure, True)
        self.assertEqual(msg.camera, 'ecamera')

    def test_findstar(self):
        self._findstar('')

    def test_findstar_nondefault(self):
        self._findstar('time=11 bin=2', {'time': 11, 'bin': 2})


if __name__ == '__main__':
    verbosity = 2

    suite = None
    # to test just one piece
    # suite = unittest.TestLoader().loadTestsFromTestCase(TestClassifyCartridge)
    if suite:
        unittest.TextTestRunner(verbosity=verbosity).run(suite)
    else:
        unittest.main(verbosity=verbosity)
