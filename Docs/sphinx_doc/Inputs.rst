.. _Inputs:

Inputs
======

A coupled run reads one inputs file, parsed by AMReX ``ParmParse``, that
supplies parameters to the driver and to both solvers at once. This page
describes how that file is organized, the solver parameters the driver
requires or sets, and every ``driver.*`` parameter. Parameters that belong to
ERF (``erf.*``) or REMORA (``remora.*``) are documented in the `ERF inputs
reference <https://erf.readthedocs.io/en/latest/Inputs.html>`_ and the `REMORA
inputs reference <https://remora-ocean.readthedocs.io/en/latest/Inputs.html>`_.

Structure of a coupled deck
---------------------------

Each case in ``Exec/`` is split into three files: a coupled deck and the two
solver decks it imports. Parameters are dispatched by prefix:

* ``driver.*`` is read by COASTER.
* ``erf.*`` is read by ERF, and ``remora.*`` by REMORA.
* Shared keys (``amr.*``, ``geometry.*``, ``max_step``, ``stop_time``) are read
  by the driver and by both solvers.

An example coupled deck:

.. code-block:: text

   # Import the two solver decks. FILE paths are relative to the directory the
   # driver runs in, not to this file.
   FILE = inputs_REMORA
   FILE = inputs_ERF

   # Driver control
   driver.coupling_direction = two_way
   driver.atm2ocn_mode       = state

   # Coupling cadence (see below)
   erf.fixed_dt    = 3.0
   remora.fixed_dt = 300.0

   max_step = 864

   # Domain size lives on the solvers, not the driver
   erf.n_cell    = 50 20 48
   remora.n_cell = 50 20 40

   # Optional driver controls
   driver.remap_frame        = auto     # auto | spherical | cartesian
   driver.remap_v            = 1        # remap geometry and coverage detail
   driver.v                  = 0        # driver lifecycle detail
   driver.plot_int_exchange  = -1       # exchange-field plotfiles, in ocean steps
   driver.couple_currents    = false    # two-way: send REMORA's surface current to ERF

Run it with:

.. code-block:: bash

   ./build/coaster /path/to/inputs

Solver parameters the driver requires or sets
---------------------------------------------

Required:

* ``erf.fixed_dt`` and ``remora.fixed_dt``. Both solvers run at fixed time
  steps. The exchange interval must be an integer multiple of each; see
  :ref:`TimeCoupling`.
* ``max_step`` or ``stop_time`` (or both, in which case the earlier wins).
  ``max_step`` counts ocean steps. The run must end on an exchange boundary:
  ``max_step`` must be a multiple of the ocean steps per exchange, and a
  ``stop_time`` that is not on a boundary is rounded down to one, with a
  warning.
* ``erf.prob_lo``, one of ``erf.prob_hi`` or ``erf.prob_extent``,
  ``erf.n_cell`` and ``erf.is_periodic``; and ``remora.prob_lo``,
  ``remora.prob_hi``, ``remora.n_cell`` and ``remora.is_periodic``. The
  horizontal periodicity of the two must match.
* For a restart, ``erf.restart`` and ``remora.restart`` together; see
  :ref:`CheckpointRestart`. ``amr.restart`` is rejected.

Set by the driver:

* ``erf.use_coupled_sst = 1`` in a two-way run, and
  ``erf.use_coupled_currents = 1`` with ``driver.couple_currents``. Setting
  ``erf.use_coupled_currents`` yourself without ``driver.couple_currents`` is
  an error.
* Defaults for the mesh layout, applied unless the deck sets them; see
  :ref:`ParallelLayout`.
* ``remora.max_step`` and ``remora.stop_time`` are removed: the driver decides
  when REMORA stops. With a nonzero ``driver.ocean_time_offset``, REMORA's
  stop time is set from ``stop_time`` on REMORA's clock, and a user-supplied
  ``remora.stop_time`` is discarded with a warning.
* ``amr.check_int``, ``amr.check_per``, ``amr.check_int_time``,
  ``amr.regrid_int``, ``amr.do_substep`` and ``amr.iterate_grids`` are removed
  after the solvers are initialized. Use each solver's own checkpoint
  controls (``erf.check_int``, ``remora.check_int``).

When the two grids differ in horizontal extent or their cell counts are not in
an integer ratio, the driver prints a ``coupled grids are non-conformal``
warning and continues; the remap handles such grids.

.. _sec:DriverParameters:

Driver parameters
-----------------

Coupling
^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 32 18 50

   * - Parameter
     - Default
     - Meaning
   * - ``driver.coupling_direction``
     - required
     - ``ERFtoREMORA`` (one-way) or ``two_way``. Case-insensitive. See
       :ref:`CouplingOverview`.
   * - ``driver.atm2ocn_mode``
     - ``state``
     - ``state`` or ``flux``: which atmosphere-to-ocean lanes are exchanged.
       See :ref:`CouplingContract`.
   * - ``driver.couple_currents``
     - ``false``
     - Send REMORA's surface current to ERF, which then computes its surface
       stress from the wind relative to it. Two-way only. See
       :ref:`sec:SurfaceCurrents`.
   * - ``driver.atm2ocn_lane_source.<lane>``
     - ``auto``
     - ``erf``, ``remora`` or ``auto``: override which model supplies one
       atmosphere-to-ocean state lane. A misspelled lane name aborts. See
       :ref:`sec:LaneProvenance`.

Time
^^^^

.. list-table::
   :header-rows: 1
   :widths: 32 18 50

   * - Parameter
     - Default
     - Meaning
   * - ``driver.exchange_interval``
     - ``remora.fixed_dt``
     - Seconds between exchanges. Must be an integer multiple of both
       ``erf.fixed_dt`` and ``remora.fixed_dt``.
   * - ``driver.ocean_time_offset``
     - 0
     - Seconds added to REMORA's clock, so that REMORA's model time is this
       offset plus the elapsed coupled time. ERF's clock starts at 0. See
       :ref:`sec:OceanTimeOffset`.
   * - ``driver.time_average_atm2ocn_state``
     - 0
     - Pass the trapezoidal mean of the state-character lanes over each
       exchange interval instead of the interval-end value. Rejected with
       ``driver.atm2ocn_mode = flux``, which has no state-character lanes. See
       :ref:`sec:TimeAveraging`.
   * - ``driver.time_average_atm2ocn_flux``
     - 0
     - The same for the flux-character lanes.

Remapping
^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 32 18 50

   * - Parameter
     - Default
     - Meaning
   * - ``driver.remap_frame``
     - ``auto``
     - ``auto``, ``spherical`` or ``cartesian``: the coordinate system the
       remap weights are built in. See :ref:`Remapping`.
   * - ``driver.remap_min_coverage_frac``
     - 0.001
     - Smallest covered fraction of a destination cell that counts as covered.
   * - ``driver.remap_donor_fill``
     - ``withhold``
     - ``withhold`` or ``coawst``: what an uncovered wet ocean cell receives.
       Spherical frame only. See :ref:`sec:DonorFill`.
   * - ``driver.remap_donor_max_diagonals``
     - 3.0
     - ``coawst`` only: the farthest a donor may be, in multiples of its own
       cell diagonal. Must be at least 0.
   * - ``driver.remap_bin_cells``
     - 4
     - Target number of ERF cells per bin in the spatial search used to find
       overlapping cells. Affects how fast the weights are built, not which
       overlaps are found.
   * - ``driver.remap_extend_corner_ring``
     - ``false``
     - Extend ERF's corner mesh by one ring of cells, as SCRIP's
       ``create_extra_rho_grid`` does. Needed only when an ocean grid nested
       inside the atmosphere exchanges on its outer ring.

Output and diagnostics
^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 32 18 50

   * - Parameter
     - Default
     - Meaning
   * - ``driver.v``
     - 0
     - Driver verbosity. 1 adds lifecycle and layout detail and per-exchange
       field validation. See :ref:`Output`.
   * - ``driver.remap_v``
     - 0
     - Remap verbosity: 1 adds geometry and coverage detail; 2 adds one line
       per staged box.
   * - ``driver.plot_int_exchange``
     - -1
     - Write plotfiles of the exchanged fields every this many ocean steps;
       -1 writes none.
   * - ``driver.plot_file_exchange_a2o``
     - ``exchange_a2o``
     - Prefix for atmosphere-to-ocean exchange plotfiles.
   * - ``driver.plot_file_exchange_o2a``
     - ``exchange_o2a``
     - Prefix for ocean-to-atmosphere exchange plotfiles.
   * - ``driver.remap_dump_weights``
     - ``false``
     - Write every remap array to ``remap_weights/`` once after building
       them.
   * - ``driver.scrip_weights_file``
     - none
     - Compare the driver's weights with this SCRIP weights file once after
       building them. Reads the file on one rank.
   * - ``driver.scrip_a2o_group``
     - ``atm1_to_ocn1_weights.nc``
     - Group holding the atmosphere-to-ocean weights in a COAWST SCRIP file.
   * - ``driver.scrip_o2a_group``
     - ``ocn1_to_atm1_weights.nc``
     - Group holding the ocean-to-atmosphere weights.

Debugging
^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 32 18 50

   * - Parameter
     - Default
     - Meaning
   * - ``driver.debug_inject_nan_lane``
     - none
     - Write a NaN into one cell of this lane on every exchange, to test the
       non-finite guards. The run is expected to abort. See
       :ref:`Diagnostics`.
   * - ``driver.debug_inject_nan_after_guard``
     - ``false``
     - Inject the NaN after the post-pack check, so only the ``driver.v = 1``
       validation can catch it. Atmosphere-to-ocean lanes only.

Retired parameters
------------------

These keys appear in older decks and no longer exist:
``driver.synthetic_only``, ``driver.dt_atm``,
``driver.atm_substeps_per_ocean_step``, ``driver.ocean_steps``, and the
``driver.atm.*`` and ``driver.ocn.*`` topology keys. Domain size is read from
``erf.n_cell`` and ``remora.n_cell``.

.. warning::

   ``ParmParse`` ignores unknown keys silently, so an old deck runs and
   disregards them without saying so.

``driver.coupled_one_step``, ``driver.synthetic_only`` and
``driver.max_grid_size`` (with its ``_x``, ``_y`` and ``_z`` variants) are
still recognized: the driver ignores them and prints a warning. The exchange
uses the solvers' own grids, so set ``amr.max_grid_size`` instead (see
:ref:`ParallelLayout`).
