.. _ParallelLayout:

Parallel Layout
===============

ERF and REMORA each own their own ``BoxArray`` and ``DistributionMapping``, so
a given patch of ocean is generally held by different ranks in the two
solvers. This page describes the layouts COASTER uses and how the driver
bridges them.

Solver layouts
--------------

Each solver decomposes its own domain, using the usual AMReX controls
(``amr.max_grid_size``, ``amr.blocking_factor`` and so on) and the solver's
own options. The driver sets these defaults for both solvers, unless the deck
sets them:

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Parameter
     - Default
     - Reason
   * - ``amr.max_grid_size``
     - 2048
     - Large, so that any splitting to give each rank work happens in x and y
       only, as in the standalone ERF and REMORA executables.
   * - ``amr.blocking_factor``
     - 1
     -
   * - ``amr.n_proper``
     - 2
     -
   * - ``amr.no_box_split_dir``
     - 2
     - Never split grids in z. ERF's default implicit substepping requires
       this.
   * - ``amr.refine_grid_layout_x``, ``_y``, ``_z``
     - 1, 1, 0
     - Allow splitting in x and y, not z.

Exchange layouts
----------------

The exchange caches and remap weights are horizontal, single-cell-thick
arrays, and each lives on one solver's layout:

* The atmosphere-to-ocean cache and weights live on REMORA's rho-point
  layout.
* The ocean-to-atmosphere cache and weights (two-way runs only) live on ERF's
  surface layout.

So the exchange data is distributed as the destination solver's surface is,
and the exchange has no layout controls of its own: to change it, change the
solvers' decomposition.

Staging the remap inputs
------------------------

Remap weights are built rank-locally. In the spherical frame, before building
them, the driver copies
the remap inputs from one solver's layout onto the other's: for the
atmosphere-to-ocean weights, the ERF region that overlaps each REMORA box; for
the ocean-to-atmosphere weights, the REMORA corners and wet mask that overlap
each ERF box (two-way runs only). Startup reports both staging plans:

.. code-block:: text

   [driver] remap staging plan: remora_boxes=... erf_boxes=... staged_cells=...
            (erf domain ...) max_box_cells=... remora_boxes_without_overlap=...
   [driver] O2A remap staging plan: erf_boxes=... remora_boxes=... staged_cells=...

``staged_cells`` far exceeding the domain's cell count means boxes are being
copied more often than the decomposition requires. Under ``driver.v = 1``,
``[coupling-layout]`` lines dump the ``BoxArray`` and processor maps behind
this.

``remora_boxes_without_overlap`` counts REMORA boxes whose grown geographic
footprint intersects no ERF box. Those boxes hold a placeholder staged region
rather than a real one, and the ``coawst`` donor search refuses to fill them
(see :ref:`sec:DonorFill`). If the count is zero, that case never arises in
your configuration.

Under ``driver.remap_v = 2`` each box's footprint is printed, one line per box:

.. code-block:: text

   [driver] remap staging box <d> bbox=[(<lon_lo>, <lat_lo>), (<lon_hi>, <lat_hi>)]

That is the same region the ``coawst`` donor search restricts its candidates
to.

The staging copy is kept and reused on every exchange, not just when the
weights are built.

Layout assumptions
------------------

The staging asserts three assumptions about the solver layouts:

* REMORA's psi boxes are nodal versions of its rho mask boxes.
* ``lon_psi`` and ``lat_psi`` share box indexing and processor mapping.
* ERF's corners are nodal versions of the ocean-to-atmosphere weight boxes.

If a layout violates one, the run aborts on the assertion rather than
mis-mapping silently.

MPI and OpenMP
--------------

The remap weights do not depend on how boxes are assigned to ranks. They can
depend on the box layout itself, through the order in which a cell's overlaps
are stored (see :ref:`Output`), and under ``driver.remap_donor_fill = coawst``
the donor choice can depend on REMORA's box layout (see
:ref:`sec:DonorFill`). The parallel tests check that runs on several rank
counts match the serial run (see :ref:`Verification`). For an MPI + OpenMP
build, see :ref:`Building`.
