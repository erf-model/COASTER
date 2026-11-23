.. _Glossary:

Glossary
========

This page collects the terms COASTER uses for its own concepts. Where a term
has more than one name, the preferred term is given first; new prose should
use it.

Exchange
--------

.. glossary::

   Lane
      One exchanged variable's slot in an exchange cache, such as ``Uwind``,
      ``SST`` or ``SHflux``. Also seen as *layer*. Lanes are addressed by the
      index enums in ``Source/CoasterCouplingContract.H``. A lane is *active*
      when the running contract selects it, and allocated but inactive
      otherwise.

   Cache
      The driver-owned ``Vector<MultiFab*>`` holding all lanes for one
      direction, ``m_atmos_to_ocean`` and ``m_ocean_to_atmos``. It is
      allocated as a superset, so switching contract mode does not change the
      allocation.

   Slab
      A single level's ``MultiFab`` within a lane. The term appears only in
      the source; documentation should say "lane", or name the ``MultiFab``
      directly.

   Contract
      Which set of lanes is active for atmosphere-to-ocean exchange, selected
      by ``driver.atm2ocn_mode``:

      * ``state``: the atmosphere exports near-surface states and REMORA
        computes surface fluxes internally through its bulk-flux path.
      * ``flux``: the atmosphere exports computed stress, heat, moisture and
        radiation lanes directly.

   A2O
   O2A
      Atmosphere-to-ocean and ocean-to-atmosphere. Used in parameter names
      (``driver.plot_file_exchange_a2o``) and diagnostic output.

   Pack
   Apply
      The driver-owned interface between the solvers. The source solver
      *packs* its state into a cache; the destination solver *applies* it.
      ERF and REMORA never call each other directly.

Remapping
---------

.. glossary::

   Frame
      The coordinate system the remap weights are built in, set by
      ``driver.remap_frame``: cartesian or spherical. Several controls are
      inert in the cartesian frame.

   Coverage
      The fraction of a destination cell's area reached by valid source
      cells. It is thresholded on area rather than on any overlap;
      ``driver.remap_min_coverage_frac`` sets the threshold.

   Withhold
      The default donor-fill mode. When a wet destination cell has no valid
      source overlap, no stencil is written. The cell is counted as uncovered
      and receives its per-lane fallback. This is what the production
      couplers do with an unmapped point.

   Donor fill
      Grafting a stencil for an otherwise uncovered cell, pointing at a
      nearby source cell. Selected by ``driver.remap_donor_fill``; ``coawst``
      mode reproduces COAWST's ``check_weights`` behavior. Donor-filled cells
      are counted separately from genuinely covered ones.

   fracarea
   dstarea
      The two conservative-remap normalizations distinguished by SCRIP
      (Jones, 1999). ``fracarea`` divides by the covered fraction;
      ``dstarea`` divides by the full destination area.

   Staged box
      A REMORA-side region (psi corners and wet mask) copied onto the ERF box
      layout so that weight construction is rank-local.

Wet mask
--------

.. glossary::

   Wet
   Dry
      Ocean versus land cells in REMORA's mask. Coverage counts only wet
      destination cells; a missing wet mask is reported rather than treated
      as an all-wet sheet.
