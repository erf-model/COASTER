.. _ParallelLayout:

Parallel Layout
===============

ERF and REMORA each own their own ``BoxArray`` and ``DistributionMapping``, so
a given patch of ocean is generally held by different ranks in the two
solvers. This page describes how the driver bridges the two layouts.

.. note::

   This page is still being written. ``driver.max_grid_size`` and its
   per-direction variants, and MPI and OpenMP usage, will be added.

Staging the remap inputs
------------------------

Remap weights are built rank-locally. Before building them, the driver copies
the remap inputs from one solver's layout onto the other's: for the
atmosphere-to-ocean weights, the ERF region that overlaps each REMORA box; for
the ocean-to-atmosphere weights, the REMORA corners and wet mask that overlap
each ERF box. Startup reports both staging plans:

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

Layout assumptions
------------------

The staging asserts three assumptions about the solver layouts:

* REMORA's psi boxes are nodal versions of its rho mask boxes.
* ``lon_psi`` and ``lat_psi`` share box indexing and processor mapping.
* ERF's corners are nodal versions of the ocean-to-atmosphere weight boxes.

If a layout violates one, the run aborts on the assertion rather than
mis-mapping silently.
