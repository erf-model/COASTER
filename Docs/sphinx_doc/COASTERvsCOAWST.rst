.. _COASTERvsCOAWST:

COASTER vs COAWST
=================

COAWST (Warner et al., 2010) couples the atmosphere model WRF, the ocean model
ROMS and wave and sediment models. COASTER follows its atmosphere-ocean
coupling closely, with ERF in place of WRF and REMORA in place of ROMS. This
page summarizes where the two agree and differ, and how a COAWST
configuration translates to COASTER inputs.

Similarities
------------

* **Exchanged fields.** COASTER's state contract is COAWST's state exchange
  (Warner et al., 2010, Fig. 5, Block B), in which the ocean computes its own
  bulk fluxes from the atmospheric state (ROMS's ``BULK_FLUXES`` path,
  ``ROMS/Nonlinear/bulk_flux.F``). The flux contract corresponds to ROMS's
  ``ATM2OCN_FLUXES`` path (``ROMS/Nonlinear/atm2ocn_flux.F``), in which the
  ocean applies fluxes computed by the atmosphere. Both are selected in COAWST
  in ``Master/mct_roms_wrf.h``. See :ref:`CouplingContract`.
* **Ocean feedback.** The ocean returns SST and, optionally, its surface
  current, which the atmosphere uses for a relative-wind surface stress, as
  WRF does with ROMS's ``UOCE`` and ``VOCE``.
* **Conservative remapping.** Both use first-order conservative remapping in
  the SCRIP formulation (Jones, 1999), with ``fracarea`` normalization, in a
  spherical frame on real-world grids. See :ref:`Remapping`.
* **Donor fill.** ``driver.remap_donor_fill = coawst`` reproduces COAWST's
  ``check_weights`` (``Lib/SCRIP_COAWST/scrip.f``), which fills wet ocean
  cells that no atmosphere cell overlaps from the nearest atmosphere water
  cell.

Differences
-----------

* **Coupling infrastructure.** COAWST exchanges fields through the Model
  Coupling Toolkit (MCT) between separate model components. COASTER links
  both models into one executable and moves fields through its own driver;
  it does not use MCT.
* **Remap weights.** COAWST reads weights computed beforehand by SCRIP from a
  weights file (such as ``scrip_coawst.nc``). COASTER computes its weights at
  startup from the two models' grids. It can read a COAWST weights file, but
  only to compare against (``driver.scrip_weights_file``; see :ref:`Output`).
* **Uncovered cells.** COASTER's default, ``withhold``, leaves an uncovered
  wet ocean cell unmapped, so it receives a per-lane fallback, as production
  couplers do. COAWST's donor fill is available but not the default, because
  it makes the atmosphere-to-ocean remap non-conservative. See
  :ref:`sec:DonorFill`.
* **Waves and sediment.** COASTER has no wave or sediment model, and REMORA
  has no wave-current coupling, so COAWST's wave-mediated terms (Stokes drift,
  vortex force, wave-dependent surface roughness and breaking) have no
  counterpart.

Translating a COAWST configuration
----------------------------------

``Exec/OCCAMS/translation_map.tsv`` maps each setting of the reference
WRF/ROMS/COAWST OCCAMS run to its COASTER equivalent: WRF's
``namelist.input``, ROMS's ``ocean.in`` and ``cppdefs.h`` and the CPP options
recorded in its history file, the input data files, and the build. Each row
gives the source setting and value, the COASTER input file and key it maps to,
the transformation or assumption involved, and evidence from the reference
run.

Each row's ``status`` is one of:

.. list-table::
   :header-rows: 1
   :widths: 15 10 75

   * - Status
     - Rows
     - Meaning
   * - ``copied``
     - 58
     - Carried over unchanged.
   * - ``adapted``
     - 98
     - Carried over with a transformation, such as a unit or convention
       change.
   * - ``added``
     - 2
     - A COASTER setting with no COAWST counterpart.
   * - ``deferred``
     - 55
     - Not yet carried over.
   * - ``dropped``
     - 48
     - Deliberately not carried over, usually because it does not apply.
   * - ``unresolved``
     - 8
     - The correct translation is not yet known.

Each row's ``mismatch_tier`` gives the size of any gap: ``tier1_toggle``
(an input setting), ``tier2a_rebuild`` (needs a different build),
``tier2b_short_code`` (needs a small code change), or ``tier3_substantial``
(a missing capability).

What is not at parity
^^^^^^^^^^^^^^^^^^^^^

The largest gaps, from the ``tier3_substantial`` and ``tier2`` rows, are:

* **Atmosphere:** WRF's microphysics scheme (ERF uses a fallback),
  observational nudging (FDDA), canopy drag, gravity-wave drag, sixth-order
  hyperdiffusion, and the land-surface model (Noah-MP is available in ERF but
  not yet configured for OCCAMS).
* **Ocean:** wave-current coupling and wave-dependent surface roughness;
  several vertical-mixing options (spline-based vertical diffusion, GLS
  interpolation and Richardson-number options, viscosity and diffusivity
  limits); the density-Jacobian pressure-gradient scheme; spatially variable
  density in the barotropic pressure gradient; and the inverse-barometer
  effect of atmospheric pressure.

The ``unresolved`` rows include the humidity convention of the forcing file,
ozone above the model top in the radiation, and the reconstruction of WRF's
pressure top as an ERF domain height.

References
----------

Warner, J. C., B. Armstrong, R. He, and J. B. Zambon (2010). Development of a
Coupled Ocean–Atmosphere–Wave–Sediment Transport (COAWST) modeling system.
*Ocean Modelling*. https://doi.org/10.1016/j.ocemod.2010.07.010

Zambon et al. (2014), a COAWST hurricane application with direct exchange of
stress and heat fluxes.

Jones, P. W. (1999). First- and second-order conservative remapping schemes
for grids in spherical coordinates. *Monthly Weather Review*.
https://doi.org/10.1175/1520-0493(1999)127%3C2204:FASOCR%3E2.0.CO;2
