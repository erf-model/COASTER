.. _COASTERvsCOAWST:

COASTER vs COAWST
=================

How COASTER compares with COAWST, the coupled WRF/ROMS system it most closely
follows, and how a COAWST configuration translates to COASTER inputs.

.. note::

   This page is being written. It will cover:

   * Similarities and differences in the coupling approach
   * How WRF, ROMS and COAWST settings map to COASTER inputs
   * What is at parity and what is not

COASTER's state contract follows the COAWST state exchange (Warner et al.,
2010, Fig. 5, Block B), and its ``coawst`` donor-fill mode reproduces COAWST's
``check_weights``. The COAWST source files COASTER's coupling follows are:

* ``Master/mct_roms_wrf.h``: the ``ATM2OCN_FLUXES`` and ``BULK_FLUXES``
  pathways
* ``ROMS/Nonlinear/atm2ocn_flux.F``: the directly imported flux path
* ``ROMS/Nonlinear/bulk_flux.F``: the state-driven bulk-flux path
* ``Lib/SCRIP_COAWST/scrip.f``: ``check_weights``

``Exec/OCCAMS/translation_map.tsv`` maps each setting of the reference
WRF/ROMS/COAWST OCCAMS run to its COASTER equivalent.

References
----------

Warner, J. C., B. Armstrong, R. He, and J. B. Zambon (2010). Development of a
Coupled Ocean–Atmosphere–Wave–Sediment Transport (COAWST) modeling system.
*Ocean Modelling*. https://doi.org/10.1016/j.ocemod.2010.07.010

Zambon et al. (2014), a COAWST hurricane application with direct exchange of
stress and heat fluxes.

.. Content to migrate here: Exec/OCCAMS/translation_map.tsv
