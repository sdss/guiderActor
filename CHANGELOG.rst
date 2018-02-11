.. _guiderActor-changelog:

==========
Change Log
==========

This document records the main changes to the guiderActor code.

.. _changelog-3.8.0:

3.8.0 (unreleased)
-----------------

Added
^^^^^

* Implemented use of ``bumpversion``.
* Implemented ``GuiderActor.version`` (needs ``actorcore >= v4_1_3``).
* Ticket `#2030 <https://trac.sdss.org/ticket/2030>`_: proc-gimg shows parameters we are guiding on.

Modified
^^^^^^^^

* Using ``X.Y.Z`` instead of ``vX_Y_Z``.
* Updated ``gcamFiberInfo.par``.

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
