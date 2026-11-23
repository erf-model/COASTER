.. _Inputs:

Inputs
======

A coupled run reads one inputs file, parsed by AMReX ``ParmParse``, that
supplies parameters to the driver and to both solvers at once. This page
describes how that file is organized and which parameters the driver reads or
constrains. Parameters that belong to ERF (``erf.*``) or REMORA (``remora.*``)
are documented in the `ERF inputs reference
<https://erf.readthedocs.io/en/latest/Inputs.html>`_ and the `REMORA inputs
reference <https://remora-ocean.readthedocs.io/en/latest/Inputs.html>`_.

.. note::

   A complete reference table for the ``driver.*`` parameters is still being
   written. Until then, the controls are described on the pages for the
   features they control, linked below.

Structure of a coupled deck
---------------------------

Each case in ``Exec/`` is split into three files: a coupled deck and the two
solver decks it imports. Parameters are dispatched by prefix:

* ``driver.*`` is read by COASTER.
* ``erf.*`` is read by ERF, and ``remora.*`` by REMORA.
* Shared mesh keys (``amr.*``, ``geometry.*``) are read by both solvers.

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
   driver.remap_dump_weights = 0        # write the built remap arrays to remap_weights/
   driver.v                  = 0        # driver lifecycle detail
   driver.plot_int_exchange  = -1       # exchange-field plotfiles, in ocean steps
   driver.couple_currents    = false    # two-way: send REMORA's surface current to ERF

   # What a wet ocean cell with no atmosphere source cell receives.
   # Spherical frame only; inert in the cartesian frame.
   driver.remap_donor_fill          = withhold   # withhold | coawst
   driver.remap_donor_max_diagonals = 3.0        # coawst only
   driver.time_average_atm2ocn_state = 0         # average state-character lanes
   driver.time_average_atm2ocn_flux  = 0         # average flux-character lanes

Run it with:

.. code-block:: bash

   ./build/coaster /path/to/inputs

Requirements on the solver settings
-----------------------------------

The driver checks the solver settings that affect coupling at startup and
aborts if they are inconsistent:

* The solvers exchange every ``driver.exchange_interval`` seconds, which
  defaults to ``remora.fixed_dt``. The interval must be an integer multiple of
  both ``erf.fixed_dt`` and ``remora.fixed_dt``.
* ``max_step`` counts ocean steps, and must end on an exchange boundary.

See :ref:`TimeCoupling` for how the two solvers are advanced within an
exchange interval.

Where each control is described
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Parameters
     - Described in
   * - ``driver.coupling_direction``, ``driver.atm2ocn_mode``,
       ``driver.couple_currents``, ``driver.atm2ocn_lane_source.<lane>``
     - :ref:`CouplingContract`
   * - ``driver.exchange_interval``, ``driver.time_average_atm2ocn_state``,
       ``driver.time_average_atm2ocn_flux``
     - :ref:`TimeCoupling`
   * - ``driver.remap_frame``, ``driver.remap_min_coverage_frac``,
       ``driver.remap_donor_fill``, ``driver.remap_donor_max_diagonals``
     - :ref:`Remapping`
   * - ``driver.v``, ``driver.remap_v``, ``driver.plot_int_exchange``,
       ``driver.remap_dump_weights``, ``driver.scrip_weights_file``,
       ``driver.scrip_a2o_group``, ``driver.scrip_o2a_group``
     - :ref:`Output`
   * - ``driver.debug_inject_nan_lane``, ``driver.debug_inject_nan_after_guard``
     - :ref:`Diagnostics`

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

``driver.coupled_one_step`` is still parsed but ignored, and the driver warns
when it is set.
