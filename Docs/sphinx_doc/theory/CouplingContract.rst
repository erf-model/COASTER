.. _CouplingContract:

Coupling Contract
=================

Which fields cross between the atmosphere and the ocean, in what units, at which grid locations, and which model computes the surface fluxes.

.. note::

   This page is being written. It will cover:

   * Lanes and caches
   * The state contract: the atmosphere exports near-surface state and REMORA computes bulk fluxes
   * The flux contract: the atmosphere exports stresses, heat, moisture and radiation fluxes
   * Ocean-to-atmosphere lanes: SST and surface currents
   * Units, staggering and vector frames
   * Forcing lane ownership and per-lane fallbacks

.. Content to migrate here: README.md (Coupling Contract, Exchanged fields); Source/CoasterCouplingContract.H; Exec/README.md (The rain lane)
