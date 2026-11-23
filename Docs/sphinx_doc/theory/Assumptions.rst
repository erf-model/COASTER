.. _Assumptions:

Assumptions and Limitations
===========================

This page collects the assumptions COASTER makes and the known limitations of
the current implementation. Each is described in more detail on the page
linked.

Assumptions
-----------

* **Time steps.** The exchange interval is an integer multiple of both
  solvers' fixed time steps, and the run ends on an exchange boundary. The
  driver checks this at startup. See :ref:`TimeCoupling`.
* **Geometry.** On a real-world domain both solvers provide longitude and
  latitude, so the remap is built in the spherical frame. ERF's corners are
  reconstructed from its cell centers. See :ref:`Remapping`.
* **Solver layouts.** The weight staging assumes that REMORA's psi boxes are
  nodal versions of its rho mask boxes, that ``lon_psi`` and ``lat_psi`` share
  box indexing and processor mapping, and that ERF's corners are nodal
  versions of the ocean-to-atmosphere weight boxes. The driver asserts each of
  these and aborts if a layout violates one. See :ref:`ParallelLayout`.
* **Resolution ratio.** One destination cell overlaps at most nine source
  cells. Beyond that, overlaps are dropped and conservation degrades, with a
  warning.

Limitations
-----------

* **Vertical refinement.** REMORA does not support refinement in the vertical
  in coupled mode; the z refinement ratio must be 1.
* **Flux contract.** ``driver.atm2ocn_mode = flux`` works from the first
  ocean step but is less exercised than the state contract.
* **Donor fill.** ``driver.remap_donor_fill = coawst`` is not conservative,
  and its donor choice is not proven independent of REMORA's decomposition.
  See :ref:`sec:DonorFill`.
* **Coverage threshold.** The default ``driver.remap_min_coverage_frac``
  follows values attributed to CESM and OASIS3-MCT that have not been checked
  against those couplers' source.
* **Test coverage.** The automated tests use the Upwelling case, whose grids
  are matched, entirely ocean, and uniformly forced. They do not exercise the
  spherical remap, wet masks, partial coverage or donor fill; those run only
  in the OCCAMS cases. See :ref:`Testing`.

Planned extensions
------------------

* Wave-mediated coupling terms, such as Stokes drift and wave-dependent
  surface roughness.
