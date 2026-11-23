.. _Output:

Output
======

This page explains how to read what a coupled run reports. For ERF and REMORA
plotfiles, checkpoints and their own diagnostics, see the upstream
documentation.

Driver diagnostics are tagged ``[driver]`` or ``[coupling-layout]``; output
from ERF and REMORA is untagged. Most of these lines are not pass/fail.
Several report degraded coupling that does not stop the run and is not
reported anywhere else, so for each one the useful question is what value is
normal.

Verbosity
---------

``driver.v = 1``
   Driver lifecycle and layout queries, and the per-exchange
   ``Exchange validation``, ``Post-pack``, ``Pre-apply`` and ``Post-apply``
   lines. These print each lane's wet-cell minimum and maximum, and abort on
   any non-finite wet value (see :ref:`Diagnostics`).

``driver.remap_v = 1``
   Remap geometry: corner ranges, extents, stencil occupancy, the resolved
   donor-fill mode, and per-direction coverage summaries.

``driver.remap_v = 2``
   Also the longitude-latitude bounding box of each staged REMORA box, one
   line per box. This is the region the ``coawst`` donor search is restricted
   to, so raise it when a donor choice looks wrong.

Warnings and the coverage summary print at any verbosity, and so do the
donor-fill warnings: choosing a non-default mode is never silent. Raise
``driver.remap_v`` when a coverage number looks wrong and you need the
geometry behind it.

The solvers' own flags control their side of the exchange:

``erf.v = 2``
   ERF's coupled-SST check (the ``Coupled SST apply`` summary and its range
   warning) on every ERF step. Below 2 it runs once, on the first step, since
   the driver hands ERF the same SST on every step of an exchange and REMORA
   has already checked it.

``remora.v = 1``
   REMORA's ``ApplyAtmosphericFluxes validation`` block and its wet
   surface-temperature range on every exchange. Below 1 the block prints once
   per run. This also turns on all other REMORA ``v = 1`` output.

REMORA's surface-temperature range warning is checked on every exchange at any
verbosity, and repeats only when a later exchange is worse.

Startup
-------

Which contract is running
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   Atmos->ocean contract mode: <name> (<N> active layers)
   Atmos->ocean active lanes: <names>

The lane set is fixed for the whole run; see :ref:`CouplingContract`. With
the flux contract and no ERF radiation model, ``SWrad`` and ``LWrad`` are
passed as zero from the first step.

Where each lane's data comes from
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Startup prints one row per atmosphere-to-ocean lane:

.. code-block:: text

   Atmos->ocean lane provenance (configured mode=state)
     lane    source  reason
     Uwind   ERF     packed by ERF
     Qair    REMORA  ERF does not fill it; REMORA default stands
     rain    REMORA  remora.rain_type or its value set in deck
     LWrad   ERF     packed by ERF; REMORA longwave set to external downward

See :ref:`sec:LaneProvenance` for how each lane is resolved and how to
override it.

Which geometry the remap chose
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   [driver] BuildRemapWeights: remap frame = spherical (requested auto)

On a real-world domain such as OCCAMS this must say ``spherical``. If it says
``cartesian``, neither solver provided longitude and latitude; the run will
complete and the answer will be wrong. This is the most important line in the
startup output.

Under ``driver.remap_v = 1`` the frame is followed by the geometry derived
from it: corner ranges in the spherical frame, ``remap Cartesian extents``
otherwise, and

.. code-block:: text

   [driver] remap ERF corner mesh: nodes=... max corner-mean offset from cell centers=... deg

ERF's corners are averaged from its cell-centered ``XLONG`` and ``XLAT``. The
corner-mean offset is how far the average of each cell's four corners lands
from the cell's reported center. A small offset is expected, from the grid's
curvature. An offset that is a sizable fraction of a cell means the mesh is
misplaced, for example by a staggering mismatch between ERF and the driver.

The longitude convention is reconciled automatically:

.. code-block:: text

   [driver] remap: shifting ERF longitudes by <n> deg to match the REMORA convention

That is routine: one grid is on [-180, 180] and the other on [0, 360]. This
form is not:

.. code-block:: text

   [driver] WARNING remap: ERF longitudes [...] and REMORA longitudes [...] do not
   overlap under any 360-degree shift.

It means the two grids do not describe a common region, and every coverage
count will be zero.

Coverage
--------

Ocean to atmosphere
^^^^^^^^^^^^^^^^^^^

.. code-block:: text

   [driver] O2A SST owner match over <N> ERF surface cells (lon/lat in REMORA's convention):
   [driver]   ERF water, wet ocean donor     <n>  coupled SST
   [driver]   ERF water, outside ocean grid  <n>  keeps ERF SST (e.g. ERF (i,j) lon .. lat ..; i[..] j[..])
   [driver]   ERF water, REMORA dry          <n>  keeps ERF SST; mask disagreement (e.g. ...)
   [driver]   ERF water, thin wet overlap    <n>  keeps ERF SST; wet fraction < remap_min_coverage_frac=0.001
   [driver]   ERF land, REMORA wet           <n>  SST dropped; mask disagreement (e.g. ...)
   [driver]   ERF land, no/thin wet ocean    <n>  masks agree
   [driver]   zero-area ERF cell             <n>  skipped; degenerate corner mesh

Every ERF surface cell is in exactly one row, according to whether ERF calls
it land and what REMORA has under it. Only the first row takes the coupled
SST. The rows must add up to ``<N>``, and a warning says so if they do not.
Each disagreement row names one example cell and the i/j box enclosing the
whole row. The example is the lowest (i, j), so it is the same cell at any rank
count, which is why it tends to sit on the south edge. A narrow box along the
coast is a real coastline; a long straight band is a misalignment.

.. list-table::
   :header-rows: 1
   :widths: 25 35 40

   * - Row
     - Normal on OCCAMS (flux deck)
     - If it is large
   * - ERF water, wet ocean donor
     - 217,989
     -
   * - ERF water, outside ocean grid
     - 2,925. The atmosphere reaches past the ocean grid.
     - Expected; not a signal.
   * - ERF water, REMORA dry
     - 2,058, shaped like the coastline.
     - The grids are misaligned: the ocean land mask lands in the wrong place.
       This is the row that catches a bad corner reconstruction.
   * - ERF water, thin wet overlap
     - 0. Slivers at the edge of the ocean grid.
     - The grids are offset by a fraction of a cell.
   * - ERF land, REMORA wet
     - 1,187, shaped like the coastline.
     - Misalignment in the other direction.
   * - ERF land, no/thin wet ocean
     - 256,139
     -
   * - zero-area ERF cell
     - 0
     - ERF's corner mesh is broken at those cells.

Water cells without a REMORA source keep ERF's own SST (from ``wrflowinp`` on
OCCAMS); see :ref:`Remapping`. Cells in the ``ERF land, REMORA wet`` row keep
their remap stencil, since REMORA's pack zeroes ERF land anyway, but are not
flagged as coupled. That is why the
``remap coverage (O2A SST stencils ...)`` line just above reports fewer
uncovered cells than the table's uncoupled rows add up to.

Atmosphere to ocean
^^^^^^^^^^^^^^^^^^^

Atmosphere-to-ocean coverage is reported once, as ``A2O rho``, since every
lane uses the same weights. Uncovered wet cells produce:

.. code-block:: text

   [driver] WARNING remap (<label>): <N> of <M> REMORA wet cells (e.g. REMORA (i,j);
   i[..] j[..]) have no ERF water source overlap. ApplyConservativeRemap ...
   branches on the -1 index sentinel and assigns a per-lane fallback: ...

The example and box are in REMORA's rho index space. On OCCAMS (flux deck)
``N`` is 168. These cells do not all fall back to a standard atmosphere; see
:ref:`sec:UncoveredCells` for what each lane receives. Expect a small count
along coastlines where the land masks disagree, or where the ocean grid
reaches past the atmosphere's. A large count means the atmosphere does not
cover the ocean grid.

Under ``driver.remap_v = 1``, the summary is:

.. code-block:: text

   [driver] remap coverage (<label>): cells=... uncovered=... no_stencil=...
                                      donor_filled=... frac min/mean/max=.../.../...
                                      max|frac-1|=...

``uncovered``
   Destination cells whose weight sum is zero.

``no_stencil``
   Destination cells whose stored source index is still the ``-1`` sentinel.
   ERF's fallback assignment keys on this, not on the weight sum. The two must
   agree, and the driver asserts that they do, since a cell with an index but
   no weight would receive 0 Pa or 0 K rather than its lane fallback.

``donor_filled``
   Cells whose stencil is a donor graft rather than a real overlap. Always 0
   under the default ``driver.remap_donor_fill = withhold`` and in the
   cartesian frame (see :ref:`sec:DonorFill`). The field is absent from the
   ``O2A SST`` line, which has no donor mechanism.

``max|frac-1|``
   The coverage error, not a conservation error. Before normalization the
   weight sum is the covered fraction, so a destination cell the source grid
   only half covers reports 0.5 here and is working correctly. What this
   catches is a maximum fraction above 1, which comes from round-off in the
   polygon clipping.

When every wet cell is covered, ``driver.remap_v = 1`` also prints:

.. code-block:: text

   [driver] remap coverage (<label>): all <M> wet cells covered by real source
   overlap (donor_filled=0), min wet frac=<x>

This line is suppressed whenever any cell was donor-filled, so it appears only
when coverage is genuinely complete.

Donor fill
^^^^^^^^^^

Under ``driver.remap_v = 1`` the driver reports which donor-fill mode is in
effect:

.. code-block:: text

   [driver] BuildRemapWeights: donor fill = withhold (inert in the cartesian frame)

Selecting ``coawst`` prints two lines at any verbosity:

.. code-block:: text

   [driver] WARNING remap: driver.remap_donor_fill=coawst grafts a full-weight
   nearest-neighbor stencil into the fracarea-normalized conservative matrix ...
   The resulting atmosphere->ocean operator is NOT conservative.

   [driver] remap: coawst donors are restricted to source cells whose centroid lies
   inside the destination box's own grown lon/lat bounding box, and to within
   driver.remap_donor_max_diagonals=<r> donor diagonals ...

In the cartesian frame a third line says the request has no effect:

.. code-block:: text

   [driver] remap: driver.remap_donor_fill=coawst has no effect in the cartesian
   frame; the donor search only runs when the frame is spherical.

Setting ``driver.remap_donor_max_diagonals`` under ``withhold`` is likewise
reported as having no effect.

Donor-filled cells are reported as their own category and are never counted
as covered:

.. code-block:: text

   [driver] WARNING remap (<label>): <D> of <M> REMORA wet cells (e.g. REMORA (i,j);
   i[..] j[..]) have no ERF source cell of their own and were donor-filled from the
   nearest non-land ERF cell (driver.remap_donor_fill=coawst). ...

Their weight sum is nonzero, so they are not counted in ``uncovered`` or
``no_stencil``, which keep the meaning they have under ``withhold``. They are
counted in ``donor_filled``, excluded from ``min wet frac`` (a graft
normalizes to a perfect 1.0 and would flatter the statistic), and their
presence suppresses the all-covered line.

Warnings that degrade silently
------------------------------

These do not stop the run, and nothing downstream reports them.

.. code-block:: text

   [driver] remap: <N> wet destination cells had no valid source overlap and were
   filled from their nearest non-land source cell (COAWST check_weights behavior).

Printed only under ``driver.remap_donor_fill = coawst``. These cells carry a
neighbor's atmospheric state rather than their own. ``<N>`` counts the same
cells as ``donor_filled`` on the ``A2O rho`` coverage line. Watch the trend: a
count that rises between runs means the two land masks are drifting apart.

.. code-block:: text

   [driver] WARNING BuildOceanToAtmosWeights: <N> ocean overlaps dropped because a
   destination cell exceeded MAX_STENCIL_SIZE=<K> (max overlaps seen = <M>);
   weights normalized over the largest-area overlaps kept.

The stencil overflowed: one destination cell covers more source cells than the
stencil holds. The run continues with weights renormalized over the
largest-area overlaps, so conservation is degraded. The form to check before
that happens, under ``driver.remap_v = 1``, is

.. code-block:: text

   [driver] remap stencils: max overlaps per destination cell = <M> of <K>

If ``<M>`` is close to ``<K>``, the next grid change may overflow.

Two range checks run on the exchanged surface temperature. Both cover only
cells that carry ocean data, and both count NaN as out of range:

.. code-block:: text

   WARNING: REMORA surface temperature outside [270.65, 313.15] K on <n> of <M> wet
   cells (<k> NaN; min/max ... K; e.g. REMORA (i,j) = ... K). Repeated only if it gets worse.
   WARNING: coupled SST at t=<t> s outside [260, 320] K on <n> of <M> covered cells
   (<k> NaN; min/max ... K; e.g. ERF (i,j) = ... K).

The first is REMORA's top-level temperature (-2.5 to 40 °C) on its wet cells,
before the remap. It is checked on every exchange and repeated only when a
later exchange has a new extreme or more NaN cells. The second is ERF's check
on the cells the owner-match table calls coupled, run on the first step only
unless ``erf.v = 2``. In COASTER the ERF check can only fire after the REMORA
one, because the coupled SST is a weighted mean of wet REMORA values.

REMORA's received fluxes are summarized over wet cells once per run, or on
every exchange with ``remora.v = 1``:

.. code-block:: text

   REMORA ApplyAtmosphericFluxes validation (wet cells only; srflx W/m2, others kinematic):

``srflx`` is stored in W m\ :sup:`-2` and converted where it enters
``stflux``; the other fluxes are kinematic, as REMORA stores them.

Exchange plotfiles
------------------

``driver.plot_int_exchange`` writes plotfiles of the exchanged fields every
that many ocean steps (checked once per exchange); the default, -1, writes
none. ``driver.plot_file_exchange_a2o`` and ``driver.plot_file_exchange_o2a``
set the file name prefixes (defaults ``exchange_a2o`` and ``exchange_o2a``).
Each plotfile directory contains an ``exchange_info`` file that records each lane's contract membership, character and whether it was
time-averaged. Plotfiles of time-averaged fields are stamped at the interval
midpoint.

Remap weights
-------------

Dumping weights for comparison between runs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``driver.remap_dump_weights = 1`` writes every remap array the exchanges read
to ``remap_weights/`` in the run directory, once, after the weights are built:
the atmosphere-to-ocean weights and indices (``a2o_weight``, ``a2o_index``),
the ``coawst`` donor flags (``a2o_donor_fill``) when that search ran, and on
two-way runs the ocean-to-atmosphere weights, indices, valid flags and
uncoupled mask. Each array is gathered onto one box and written raw
(``<name>.bin``), with its box, component count and type in ``<name>.txt``. An
existing ``remap_weights/`` is renamed aside, as plotfiles are.

The bytes do not depend on the rank count or on how boxes are assigned to
ranks. They can depend on the box layout itself (``amr.max_grid_size``, the
domain), since each box builds its own stencils and may list a cell's overlaps
in a different order. Two runs with the same box layout compare exactly with

.. code-block:: bash

   cmp run_a/remap_weights/a2o_weight.bin run_b/remap_weights/a2o_weight.bin

provided both binaries compile the host-side polygon clipping the same way.
That holds for one binary under different settings, and for CPU and CUDA
builds made with the same host compiler and flags. It does not hold on
Perlmutter between the Cray CPU build and the CUDA build, which round the
clipping arithmetic differently; those agree to about 10\ :sup:`-16` but not
bitwise. ``Exec/OCCAMS/diff_remap_weights.py <a> <b>`` reports how far two
dumps differ, matching each cell's entries by source cell, since a sliver
overlap present in only one build shifts the later entries.

Comparing with an external SCRIP weights file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``driver.scrip_weights_file = <path>`` compares the driver's weights, once
after they are built, with a SCRIP weights file, such as the
``scrip_coawst.nc`` a reference COAWST run used. ``driver.scrip_a2o_group``
and ``driver.scrip_o2a_group`` name the groups inside a COAWST file (defaults
``atm1_to_ocn1_weights.nc`` and ``ocn1_to_atm1_weights.nc``); a plain SCRIP
file without groups is read as is.

.. code-block:: text

   [driver] SCRIP check A2O rho vs atm1_to_ocn1_weights.nc (Conservative remapping):
            <n> cells covered by both, <a> only by ours (e.g. ...), <b> only by SCRIP (e.g. ...).
   [driver] SCRIP check A2O rho: weight L1 over cells covered by both mean <m> max <x> at ...

The weight L1 difference runs from 0 (identical) to 2 (disjoint stencils), and
the file's ``map_method`` is printed alongside. The SCRIP grids may include
ROMS's boundary ring; the index offset is taken from the difference in grid
dimensions. The file is read on one rank, so leave this off for production
runs.
