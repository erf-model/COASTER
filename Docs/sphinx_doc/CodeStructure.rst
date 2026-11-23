.. _CodeStructure:

Code Structure
==============

This page is a guide to the COASTER source for readers who want to follow or
modify it. The code is in ``Source/``; ERF, REMORA and AMReX are submodules
under ``Submodules/``.

Files
-----

``main.cpp``
   Reads the run plan (time steps, exchange interval, run length, coupling
   direction and contract, restart state), sets the solver parameters the
   driver controls (see :ref:`Inputs`), and constructs and runs the
   container.

``CoupledCadence.H``
   The exchange-interval arithmetic: steps per exchange, conversion of
   ``stop_time`` to ocean steps, and the exchange-boundary check. It has no
   AMReX dependency, so it is unit-tested on its own (the ``coupled_cadence``
   test).

``CoupledRestartUtils.H``, ``.cpp``
   Reads the step, time step and time from an ERF or REMORA checkpoint
   ``Header`` for the restart checks (see :ref:`CheckpointRestart`).

``CoasterCouplingContract.H``
   The lanes: their indices, names, units, the lanes active in each contract,
   and the REMORA input key that configures each one. Its header comment maps
   each lane to its COAWST, ERF and REMORA names.

``CoasterMBContainer.H``, ``.cpp``
   The driver itself; see below.

``StandaloneSolverRuns.H``, ``RunERFStandalone.cpp``, ``RunREMORAStandalone.cpp``
   The interface to the two solvers. ``RunERFStandalone.cpp`` is the only file
   that includes ERF's headers, and ``RunREMORAStandalone.cpp`` the only one
   that includes REMORA's; the driver holds each solver as an opaque handle.
   This keeps the two solvers' headers out of any one translation unit (see
   :ref:`sec:SymbolIsolation`).

The container
-------------

``CoasterMBContainer`` owns the two solver handles, the exchange caches, the
remap weights and the coupling clock. ``main.cpp`` calls it in this order:

``InitializeSolvers()``
   Constructs ERF, then REMORA; passes each the contract and coupling
   direction and sets REMORA's start time from ``driver.ocean_time_offset``;
   calls ERF's ``InitData``; resolves which model supplies each
   atmosphere-to-ocean lane (``ResolveAtmosToOceanLaneSources``); then calls
   REMORA's ``InitData``. The lane resolution has to sit between the two
   ``InitData`` calls: it queries fields ERF allocates during its
   initialization, and it may reconfigure REMORA's longwave input before
   REMORA opens its NetCDF forcing files.

``InitializeBlocks()``
   Allocates the caches on the solvers' layouts, builds the remap weights
   (``BuildRemapWeights``), selects the active lanes, and, in a two-way run,
   packs REMORA's initial SST.

``AdvanceBlocks(ocean_steps)``
   The coupling loop described in :ref:`TimeCoupling`.

Remap weights
^^^^^^^^^^^^^

``BuildRemapWeights`` resolves the frame (``ResolveRemapFrame``) and the
donor-fill mode (``ResolveDonorFillMode``), then:

#. In the spherical frame, builds ERF's corner mesh from its cell centers
   (``BuildERFCornerMesh``) and the staging plans that copy each solver's
   geometry onto the other's layout (``BuildERFStagingPlan``, and for a
   two-way run ``BuildREMORAStagingPlan``).
#. Builds the weights in each direction (``BuildAtmosToOceanWeights``,
   ``BuildOceanToAtmosWeights``) by clipping each destination cell's polygon
   against the source cells found by a bin search, then normalizes them and
   reports coverage (``NormalizeWeightsAndCheckConservation``).
#. Optionally compares them with a SCRIP file, or dumps them
   (``CompareWeightsWithSCRIP``, ``DumpRemapWeights``).

Each destination cell's stencil holds up to ``MAX_STENCIL_SIZE`` (9) source
cells: a weight array with one component per entry, and an index array with
three components per entry giving the source cell.

Pack and apply
^^^^^^^^^^^^^^

``AdvanceBlocks`` passes four callbacks to the loop in
``AdvanceBlocksWithCallbacks``:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Callback
     - What it does
   * - pack surface state
     - ``REMORAPackSurfaceState`` (and ``REMORAPackSurfaceCurrents``) remap
       REMORA's SST (and current) onto ERF's layout; then the non-finite
       guard.
   * - apply surface state
     - ``ERFApplyOceanSurfaceState`` hands ERF the SST, with the coverage flag
       that tells ERF which cells to take it on.
   * - pack atmospheric states
     - ``ERFPackAtmosphericStates`` remaps ERF's lanes onto REMORA's layout
       with the atmosphere-to-ocean weights, masked by REMORA's wet mask; then
       the non-finite guard and validation.
   * - apply atmospheric states
     - ``REMORAApplyAtmosphericStates`` or ``REMORAApplyAtmosphericFluxes``,
       by contract, with lanes REMORA supplies itself withheld.

The remap is carried out inside the solver-side pack functions, using the
weights and staging plan the driver built. The functions themselves live in
the solvers (``Submodules/ERF/Source/Coupling/`` and
``Submodules/REMORA/Source/REMORA_Coupling.cpp``), behind the interface in ``StandaloneSolverRuns.H``.
