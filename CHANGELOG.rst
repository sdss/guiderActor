.. _guiderActor-changelog:

==========
Change Log
==========

This document records the main changes to the guiderActor code.

.. _changelog-master:

master
------

[View commits](https://github.com/sdss/guiderActor/compare/3.9.1...HEAD)


.. _changelog-3.9.1:

3.9.1 (unreleased)
------------------

Fixed
^^^^^
* Remove non-ascii character in ``guider_movie`` (fixes `ticket #2922 <https://trac.sdss.org/ticket/2922>`__.


.. _changelog-3.9.0:

3.9.0 (2018-05-30)
------------------

Added
^^^^^
* When starting, guiderActor check whether ``$GUIDERACTOR_DIR/lib/libguide.so`` exists and fails if it does not. This prevents problems when observing if the guide tools have not been compiled. (#8).
* ``guideStep`` now executes all the offsets at once making use of ``tcc guide`` (#3).

Refactored
^^^^^^^^^^
* Applied recursive autoformatting and isort (#5).
* Removed references to LCO in files and functions.
* Rewritten ``setup.py``. Now it does not use ``sdss3tools`` and the link to ``build/lib.XXX`` is created when building.

[View commits](https://github.com/sdss/guiderActor/compare/3.8.1...3.9.0)


.. _changelog-3.8.1:

3.8.1 (2018-05-03)
------------------

Modified
^^^^^^^^
* Ticket `#2325 <https://trac.sdss.org/ticket/2325>`_: if the number of valid stars is <= 2 (e.g., during centre-up), does not apply the fitting algorithm. Instead, uses the mean of the dRA and dDec offsets.

Fixed
^^^^^
* Sets ``fittingAlgorithm='NA'`` when ``FrameInfo`` is instantiated. Fixes `#2866 <https://trac.sdss.org/ticket/2866>`_


.. _changelog-3.8.0:

3.8.0 (2018-04-04)
------------------

Added
^^^^^
* Implemented use of ``bumpversion``.
* Implemented ``GuiderActor.version`` (needs ``actorcore >= v4_1_3``).
* Ticket `#2030 <https://trac.sdss.org/ticket/2030>`_: proc-gimg shows parameters we are guiding on.
* Allows to choose the fitting algorithm between the default, traditional one, and Umeyama. The fitting algorithm can be defined in the configuration file and overridden via de `setFittingAlgorithm` command.
* Added ``POSERROR`` keyword to the header to show the goodness of the fit.

Modified
^^^^^^^^
* Using ``X.Y.Z`` instead of ``vX_Y_Z``.
* Updated ``gcamFiberInfo.par``.
* Some improvements to the `reprocessFile` command. It may work at APO.

Fixed
^^^^^
* ``GUIDEAXE``, ``GUIDEFOC``, and ``GUIDESCL`` in the ``proc-gimg`` headers now should be updated correctly (for MJD >= 58212).

Removed
^^^^^^^
* ``python/guiderActor/obsolete`` (as for ticket `#2596 <https://trac.sdss.org/ticket/2596>`_).


.. _changelog-v3_7:

v3_7 (2017-06-11)
-----------------

Added
^^^^^
* Ticket `#1762 <https://trac.sdss.org/ticket/1762>`_: Guider should give better warnings about blank flats. Guider will check if FFS are closed and FF lamps are on before even trying a flat.
* Ticket `#2359 <https://trac.sdss.org/ticket/2359>`_: command to reset guider scale parameters

Fixed
^^^^^
* Ticket `#2729 <https://trac.sdss.org/ticket/2729>`_: Incorrect guider behavior when PID coefficients adjusted during MANGA exposures
* Ticket `#2759 <https://trac.sdss.org/ticket/2759>`_: Misbehavior of SOP bypasses. Restores some keywords for ``setRefractionBalance`` that allow SOP bypasses to work.
* Cleaner exit when ``guiderStep`` fails.


.. x.y.z (unreleased)
.. ------------------
..
.. A short description
..
.. Added
.. ^^^^^
.. * TBD
..
.. Changed
.. ^^^^^^^
.. * TBD
..
.. Fixed
.. ^^^^^
.. * TBD
