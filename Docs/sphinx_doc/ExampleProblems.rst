.. _ExampleProblems:

Example Problems
================

The coupled cases are in ``Exec/``. Each is split into a coupled deck that sets
the ``driver.*`` controls and the two solver decks it imports with ``FILE =``.
Run the coupled deck, from its own directory.

.. list-table::
   :header-rows: 1
   :widths: 38 16 46

   * - Deck
     - Direction
     - Notes
   * - ``Exec/Upwelling/inputs_oneway``
     - ``ERFtoREMORA``
     - Idealized; needs no external data. Run this first on a new build.
   * - ``Exec/Upwelling/inputs_twoway``
     - ``two_way``
     - REMORA SST into ERF's surface layer.
   * - ``Exec/OCCAMS/inputs_OCCAMS_smoke``
     - ``ERFtoREMORA``
     - Fast startup and exchange check; minutes, not a queue slot.
   * - ``Exec/OCCAMS/inputs_OCCAMS_oneway``
     - ``ERFtoREMORA``
     - Real OCCAMS domain.
   * - ``Exec/OCCAMS/inputs_OCCAMS_state``
     - ``two_way``
     - State contract.
   * - ``Exec/OCCAMS/inputs_OCCAMS_flux``
     - ``two_way``
     - Flux contract.
   * - ``Exec/OCCAMS/inputs_OCCAMS_rotcheck_state``,
       ``Exec/OCCAMS/inputs_OCCAMS_rotcheck_flux``
     - ``two_way``
     - Check of the vector rotation between grid axes.
   * - ``Exec/OCCAMS/inputs_OCCAMS_maximal_1day``
     - ``two_way``
     - Flux contract; one day at the ROMS ocean step, with RRTMGP radiation.

Upwelling
---------

``Exec/Upwelling`` is the coastal upwelling problem of Perlin et al. (2007).
It is used for validation and for the MPI, OpenMP and restart regression
tests, and needs no external data.

``inputs_oneway``
^^^^^^^^^^^^^^^^^

One-way (``ERFtoREMORA``) idealized upwelling: ERF forces REMORA and no SST
returns to the atmosphere.

.. code-block:: bash

   cd Exec/Upwelling
   ../../build/coaster inputs_oneway

``inputs_twoway``
^^^^^^^^^^^^^^^^^

Two-way idealized upwelling: REMORA's SST feeds ERF's surface layer through
the coupled-SST path (``erf.use_coupled_sst``, which the driver sets).

.. code-block:: bash

   cd Exec/Upwelling
   ../../build/coaster inputs_twoway

Check that the SST arriving in ERF is physical (not zero and not a
placeholder), and that the coupling clock and the ocean steps advance
together.

.. note::

   The Upwelling grids are matched one to one and are entirely ocean, so this
   deck reports complete coverage by construction. It checks the remap for
   regressions but does not exercise coverage, masking or the coverage
   threshold. Use OCCAMS for those.

OCCAMS
------

``Exec/OCCAMS`` is a realistic regional domain. The decks reference absolute
paths on NERSC systems for ``wrfinput_d01``, ``wrfbdy_d01``, the REMORA
initial, grid and boundary files, and the forcing file. None of this data is
in the repository, so the decks do not run elsewhere without editing those
paths. See :ref:`sec:BuildingPerlmutter` for the build and
``Exec/OCCAMS/run_occams.sh``, which runs the decks and summarizes the
coupling diagnostics.

The decks are run with, for example:

.. code-block:: bash

   cd Exec/OCCAMS
   srun -N 1 -n 16 ../../build_cpu_noahmp/coaster inputs_OCCAMS_oneway

``inputs_OCCAMS_oneway``
^^^^^^^^^^^^^^^^^^^^^^^^

One-way on the real domain: the atmosphere forces the ocean only.

``inputs_OCCAMS_state``
^^^^^^^^^^^^^^^^^^^^^^^

Two-way with the state contract (see :ref:`CouplingContract`). Exercises the
ocean-to-atmosphere SST return in the spherical frame.

``inputs_OCCAMS_flux``
^^^^^^^^^^^^^^^^^^^^^^

Two-way with the flux contract: the same SST return as
``inputs_OCCAMS_state``, with the surface-flux lanes on top.

``inputs_OCCAMS_smoke``
^^^^^^^^^^^^^^^^^^^^^^^

A fast check of everything that is expensive to reach: ERF's WRF
initialization, REMORA's NetCDF initialization (grid, masks, boundaries,
forcing), construction of the spherical remap weights, the ERF-to-REMORA
staging copy, and one full exchange. It runs one ocean step and two ERF steps,
so it takes minutes and can be rerun after every pull:

.. code-block:: bash

   ./run_occams.sh smoke

Unlike the production decks it sets ``amrex.fpe_trap_invalid = 1``, so
floating-point errors abort instead of propagating. It also sets
``driver.remap_frame = spherical`` and ``driver.remap_v = 1``, and writes no
plotfiles or checkpoints: the coupling diagnostics are the pass/fail signal.

Two ERF steps are not enough to expose a dynamical instability, so a blowup
that appears at step 5 of a production run does not show up here. Use
``inputs_OCCAMS_oneway`` for that.

``inputs_OCCAMS_rotcheck_state`` and ``inputs_OCCAMS_rotcheck_flux``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These check that vectors crossing the exchange are turned correctly between
the two grids' axes. The WRF/ERF and ROMS/REMORA grids differ in orientation
by up to 5.4 degrees over the OCCAMS ocean (``compare_grid_angles.py`` maps
the difference). Winds and stresses cross as east and north components; see
:ref:`sec:VectorFrames`.

Each deck includes ``inputs_OCCAMS_state`` or ``inputs_OCCAMS_flux`` and runs
three ocean steps. It writes the exchange plotfiles, ERF's grid-relative and
earth-relative 10 m winds, and REMORA's NetCDF history, which needs a NetCDF or
PNetCDF build. The flux deck also sets ``driver.couple_currents = true``. Run
each like its base deck, then in its run directory:

.. code-block:: bash

   python3 check_rotation.py --run . --wrfinput /path/to/wrfinput_d01

``check_rotation.py`` (which needs numpy, scipy and netCDF4) reports:

#. Whether REMORA's rotation is exact: the exchanged east/north winds (state)
   or stresses (flux, made kinematic and averaged to the faces) against what
   REMORA applied.
#. ERF's earth-relative 10 m wind against its grid-relative wind turned with
   WRF's own ``COSALPHA`` and ``SINALPHA``.
#. End to end (state): the direction of the wind REMORA applied, turned back
   to east/north, minus ERF's, regressed on the ROMS ``angle`` minus the WRF
   rotation angle. The slope is 0 if the vectors are turned correctly, +1 if
   they are not turned, and -1 if they are turned the wrong way.
#. The same slope for the surface current (flux deck, with
   ``driver.couple_currents``).

On a run from 2026-11-18, check 1 was exact to roundoff for both winds and
stress (the fitted stress scale was :math:`-1/\rho_0`); check 2 showed a
direction difference of at most 0.068 degrees; check 3 gave a slope of +0.03
over about 170,000 points; and check 4 a slope of +0.004 ± 0.009 over 216,090
points. The small check-3 slope, about 0.2 degrees across the whole range of
angle differences, comes from the remap and the positions of the points, not
from the rotation, since check 1 is exact.

Notes common to the OCCAMS decks
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Naming.** The two-way decks are ``inputs_OCCAMS_state`` and
``inputs_OCCAMS_flux``, named by contract; there is no
``inputs_OCCAMS_twoway``. ``inputs_OCCAMS_smoke`` and ``inputs_OCCAMS_oneway``
are both one-way.

**Geometry.** ERF runs with ``erf.init_type = "WRFInput"`` and the REMORA grid
file carries ``lon_psi`` and ``lat_psi``, so the remap resolves to the
spherical frame (see :ref:`Remapping`). Do not force
``driver.remap_frame = cartesian`` here. The ``prob_lo`` and ``prob_hi`` in
these decks are REMORA's internal Cartesian geometry, not a longitude and
latitude extent, and remapping against them silently produces a wrong overlap.

The grids do not coincide by design: ERF is 637 × 754 and REMORA is 563 × 751
over the same region. Partial coverage is expected, and the coverage
diagnostics (see :ref:`Output`) carry real information.

**Boundary data.** Every run reads ``wrfbdy_d01`` itself, converting the first
times to ERF's levels at startup and later ones as the run reaches them.
ERF's ``erfbdy`` cache is off on the WRFInput path: it is written only with
``erf.write_erfbdy = true`` and read only with ``erf.use_erfbdy = true``, and
the OCCAMS decks set neither, so a leftover ``Exec/OCCAMS/erfbdy/`` directory
is ignored. If you turn the cache on, nothing records which ERF version wrote
it or for which levels, so delete it after any ERF update or change to the
vertical grid.

**Cadence and stability.** ``max_step`` counts ocean steps. With
``remora.fixed_dt = 300`` and ``erf.fixed_dt = 10`` in the oneway, state and
flux decks, one step is thirty ERF steps and one ocean step, about ten minutes
on sixteen ranks. ``inputs_OCCAMS_maximal_1day`` runs the ocean at the 15 s
step of the ROMS ``ocean.in``, so its one day is ``max_step = 5760``.

Three settings that differ from the ERF and REMORA defaults are needed for
stability; ``translation_map.tsv`` gives the details:

* ``erf.vert_implicit_fac = 1 1 1`` in ``inputs_ERF`` makes the PBL vertical
  diffusion implicit in every RK stage, as WRF's YSU scheme is. With the
  default, the third stage is explicit, and a two-cell vertical mode grows
  over the steepest terrain and kills the run at ERF step 10.
* ``erf.avg_grid_faces_to_nodes = true`` in ``inputs_ERF`` keeps WRF's
  vertical levels. ERF's default rebuilds a grid from the 20 m surface layer
  that is about three times finer than WRF's between 500 m and 2 km, and
  resolved afternoon thermals over the Nevada desert then reach the vertical
  CFL limit at ERF step 64.
* ``remora.ndtfast = 300`` in each 300 s coupled deck (15 in the 15 s maximal
  deck) keeps the barotropic step at the 1 s the ROMS ``ocean.in`` used.
  Inheriting the base deck's value of 15 with a 300 s step makes it 20 s, and
  the ocean's first step fails. Any deck that changes ``remora.fixed_dt`` must
  scale ``remora.ndtfast`` with it.

References
----------

Perlin, N., E. D. Skyllingstad, R. M. Samelson, and P. L. Barbour (2007).
Numerical simulation of air–sea coupling during coastal upwelling. *Journal
of Physical Oceanography*. https://doi.org/10.1175/JPO3104.1
