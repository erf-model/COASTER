.. _Remapping:

Remapping
=========

The ERF and REMORA grids generally do not coincide: they can have different
resolutions, extents, orientations and land masks. The driver moves every
exchanged field between them with first-order conservative remapping, in the
SCRIP formulation of Jones (1999), and reports how much of each destination
grid the source grid covers.

The remap frame
---------------

``driver.remap_frame`` selects the coordinate system the weights are built in:

``auto`` (the default)
   Spherical if both grids carry longitude and latitude (ERF initialized from
   WRF input, and a REMORA grid file with ``lon_psi`` and ``lat_psi``), and
   cartesian if neither does. If only one side has them the driver aborts,
   since degrees and projected meters cannot be mixed.

``spherical``
   Weights are built on the sphere from the two grids' longitudes and
   latitudes. The driver aborts if either side lacks them.

``cartesian``
   Weights are built from the two grids' Cartesian extents
   (``prob_lo``/``prob_hi``).

Several remapping controls, including donor fill, have an effect only in the
spherical frame.

.. warning::

   On a real-world domain the frame must resolve to spherical. If neither
   solver provides longitude and latitude, ``auto`` resolves to cartesian, and
   the run completes with wrong answers. The frame chosen is printed at
   startup; see :ref:`Output`. Setting ``driver.remap_frame = spherical`` on
   such a domain turns this into an abort.

Grid geometry
-------------

Conservative weights need the corners of each cell. REMORA provides its
corners directly, as the psi points ``lon_psi`` and ``lat_psi``. ERF provides
only cell-centered ``XLONG`` and ``XLAT``, so the driver reconstructs ERF's
corner mesh by averaging neighboring centers.

If one grid's longitudes are on [-180, 180] and the other's on [0, 360], the
driver shifts ERF's longitudes to match REMORA's convention.

Weights are built rank-locally. Because the two solvers distribute their
boxes differently, the driver first copies the inputs each box needs from the
other solver's layout (the "staged" region): the overlapping ERF region for
each REMORA box, and the overlapping REMORA corners and wet mask for each ERF
box. See :ref:`ParallelLayout`.

Normalization and coverage
--------------------------

Before normalization, the sum of a destination cell's weights is the fraction
of its area covered by valid source cells. The remap uses ``fracarea``
normalization, dividing by that covered fraction, so a partly covered cell
still receives a properly weighted mean of the source cells it overlaps.

A cell whose covered fraction is below ``driver.remap_min_coverage_frac``
(default 0.001) is treated as uncovered. A sliver of overlap is worse than
none, because normalization would turn a covered fraction of 10\ :sup:`-6` into
a confident-looking answer. Discarding negligible destination fractions is
ordinary practice in conservative remapping; the default follows the
thresholds used in the CESM and OASIS3-MCT couplers. These values have not yet
been checked against either coupler's source.

Only wet REMORA cells count. A missing wet mask is reported rather than
treated as an all-ocean grid.

Each destination cell's stencil holds at most nine source overlaps. If a cell
overlaps more, the smallest overlaps are dropped and the weights renormalized
over the ones kept, which degrades conservation. This only happens when one
destination cell covers many more source cells than the remap was built for,
that is, at a large resolution ratio; the driver warns when it does (see
:ref:`Output`).

Ocean to atmosphere
^^^^^^^^^^^^^^^^^^^

An ERF surface cell takes the coupled SST only if ERF calls it water and
enough wet REMORA area lies under it. Every other ERF cell keeps its own SST,
for example from ``wrflowinp``. Water cells without a REMORA source are not a
hole in the forcing; they are outside the coupled region.

.. _sec:UncoveredCells:

Atmosphere to ocean: uncovered cells
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Every atmosphere-to-ocean lane, the vectors included, is remapped with the
same weights. A wet REMORA cell that no ERF water cell overlaps, because the
two land masks disagree along the coast or because the ocean grid reaches past
the atmosphere's, receives a per-lane fallback:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Lane
     - What an uncovered wet cell receives
   * - ``Patm``
     - 101325 Pa, sea-level standard
   * - ``Tair``
     - 288.15 K (15 °C), standard
   * - ``Uwind``, ``Vwind``
     - 0 m/s: calm, not a standard-atmosphere value
   * - ``cloud``, ``SWrad``, ``LWrad``, ``rain``
     - 0
   * - all eight flux lanes
     - 0
   * - ``Qair``
     - Not remapped; withheld, so REMORA's own ``remora.air_humidity``
       stands

So only ``Patm`` and ``Tair`` are forced with standard-atmosphere values. For
the wind and flux lanes, an uncovered cell is neither forced nor coupled. The
fallback is an assignment, not retention: the remap zeroes the destination
first and then writes the fallback, so a value set before the remap does not
survive on the lanes that are remapped.

.. _sec:DonorFill:

Donor fill
----------

``driver.remap_donor_fill`` decides what happens to an uncovered wet REMORA
cell. It has an effect only in the spherical frame; the donor search never
runs in the cartesian frame.

``withhold`` (the default)
   No stencil is written. The cell is counted as uncovered and receives the
   per-lane fallback above. This is what production couplers do with an
   unmapped point: ESMF defaults to ``unmappedaction = ERROR``; CMEPS pre-fills
   and maps with ``zeroregion = REGION_SELECT``; YAC does not interpolate
   unmapped points; CDO pre-fills with a missing value; and CESM withholds by
   merge weight. SCRIP and OASIS are the only comparable codes that fill at
   all, and both fill with zero, which OASIS documents as a deficiency.

``coawst``
   A full-weight stencil is grafted pointing at the nearest non-land ERF cell,
   reproducing COAWST's ``check_weights`` (``Lib/SCRIP_COAWST/scrip.f``).
   Donor-filled cells are counted separately from covered ones, and the driver
   warns that the mode is selected.

.. warning::

   With ``coawst``, the atmosphere-to-ocean operator is **not conservative**.
   ESMF refuses to combine extrapolation with conservative regridding at all
   for this reason, and the graft is exactly that: a full-weight
   nearest-neighbor row inserted into a ``fracarea``-normalized conservative
   matrix. Bounding the donor search, as below, makes *which* cell is grafted
   more reproducible; it does not make the graft conservative.

Bounds on the donor search
^^^^^^^^^^^^^^^^^^^^^^^^^^

Three restrictions apply, in this order. Only the first two are principled.

#. **A destination box with no geographic overlap with ERF is not
   donor-filled at all.** Its staged ERF region is a one-cell placeholder at
   the ERF domain corner, because a ``BoxArray`` cannot hold an empty box.
   Without this rule every wet cell in the box would take the atmospheric
   state of the ERF domain corner. The box is rejected on a recorded flag
   rather than a distance threshold, because no threshold rejects it reliably.

#. **Candidates are restricted to the destination box's own grown
   longitude-latitude bounding box.** Every ERF cell inside that box belongs to
   an ERF box whose bounding box intersects it, and the staging plan includes
   every such ERF box, so the candidate set is identical under every ERF
   decomposition.

   It does not remove dependence on REMORA's decomposition. The bounding box
   is a per-REMORA-box quantity, and a destination cell near the edge of one
   box can have the same donor accepted under one REMORA box layout and
   rejected under another. ``coawst`` mode is bounded and can be checked
   empirically, but it is not proven independent of rank count; only a global
   donor search would make it so.

#. **An acceptance radius**, ``driver.remap_donor_max_diagonals`` (default
   3.0), measured in multiples of the donor cell's own diagonal, in the same
   :math:`\cos(\text{latitude})`-corrected metric the search uses.

   This bound is a deliberate departure from precedent. No production coupler
   bounds a nearest-source fill by distance: ESMF's ``NEAREST_STOD`` is
   explicitly unbounded, and creep fill bounds by iteration count. The value
   3.0 is a judgment call that has not been calibrated against any production
   grid pair. If it matters for your configuration, vary it and watch the
   donor-filled and uncovered counts: a plateau means the value is not
   critical; a steep curve means it is. Under ``withhold`` the setting has no
   effect, and the driver says so.

A rejected donor is not a third outcome: the cell takes the same per-lane
fallback it would under ``withhold``.

Ties in the donor search are broken by the smallest global source index, as
ESMF and YAC do, rather than by scan order. Exact ties are common on a
structured grid (a destination cell centered between two source cells gives
bitwise-equal distances), and scan order depends on the decomposition.

Comparing with SCRIP weights
----------------------------

The driver can compare its weights with an external SCRIP weights file, such
as the one a reference COAWST run used, and can dump its own weights for
comparison between runs. See :ref:`Output`.

References
----------

Jones, P. W. (1999). First- and second-order conservative remapping schemes
for grids in spherical coordinates. *Monthly Weather Review*.
https://doi.org/10.1175/1520-0493(1999)127%3C2204:FASOCR%3E2.0.CO;2

Craig, A., S. Valcke, and L. Coquart (2017). Development and performance of a
new version of the OASIS coupler, OASIS3-MCT_3.0. *Geoscientific Model
Development*. https://doi.org/10.5194/gmd-10-3297-2017

Danabasoglu, G., et al. (2020). The Community Earth System Model Version 2
(CESM2). *Journal of Advances in Modeling Earth Systems*.
https://doi.org/10.1029/2019MS001916

Warner, J. C., B. Armstrong, R. He, and J. B. Zambon (2010). Development of a
Coupled Ocean–Atmosphere–Wave–Sediment Transport (COAWST) modeling system.
*Ocean Modelling*. https://doi.org/10.1016/j.ocemod.2010.07.010
