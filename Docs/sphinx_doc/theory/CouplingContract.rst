.. _CouplingContract:

Coupling Contract
=================

The coupling contract is the set of fields that cross between the atmosphere
and the ocean, with their units, locations and owners. Each exchanged field
occupies one **lane** of the exchange cache for its direction. The lane
definitions are in ``Source/CoasterCouplingContract.H``.

Atmosphere to ocean
-------------------

``driver.atm2ocn_mode`` selects which atmosphere-to-ocean lanes are active.
The selection is fixed for the whole run.

``state`` (the default)
   ERF exports near-surface atmospheric state, and REMORA computes the surface
   fluxes itself through its bulk-flux formulation. This follows the COAWST
   state-passing exchange (Warner et al., 2010) and is the most thoroughly
   tested path. Lanes: ``Uwind``, ``Vwind``, ``Patm``, ``Qair``, ``Tair``,
   ``cloud``, ``rain``, ``SWrad``, ``LWrad``.

``flux``
   ERF exports the surface fluxes it has computed, and REMORA applies them
   directly. Lanes: ``tau_x``, ``tau_y``, ``SHflux``, ``LHflux``, ``SWrad``,
   ``LWrad``, ``rain``, ``evap``. The flux lanes are live from the first ocean
   step, because the atmosphere-to-ocean pack happens after the atmosphere has
   advanced. This path is less exercised than the state path.

The atmosphere-to-ocean cache is allocated as the union of both lane sets, so
switching contract does not change the allocation.

Ocean to atmosphere
-------------------

In a two-way run, REMORA sends:

* ``SST``, which replaces ERF's surface temperature over ocean cells covered
  by the remap. Elsewhere ERF keeps its own SST.
* With ``driver.couple_currents = true``, the surface current ``Uoce`` and
  ``Voce``.

Lane reference
--------------

.. list-table::
   :header-rows: 1
   :widths: 14 14 22 20 30

   * - Lane
     - Contract
     - Units
     - REMORA key
     - Meaning
   * - ``Uwind``, ``Vwind``
     - state
     - m s\ :sup:`-1`
     - ``uwind_type``, ``vwind_type``
     - Eastward and northward near-surface wind
   * - ``Patm``
     - state
     - Pa
     - ``pair_type``
     - Surface air pressure
   * - ``Qair``
     - state
     - kg kg\ :sup:`-1` or 0–1
     - ``qair_type``
     - Near-surface humidity; ERF does not currently fill it
   * - ``Tair``
     - state
     - K
     - ``tair_type``
     - Near-surface air temperature
   * - ``cloud``
     - state
     - 0–1
     - ``cloud_type``
     - Cloud fraction
   * - ``rain``
     - both
     - kg m\ :sup:`-2` s\ :sup:`-1`
     - ``rain_type``
     - Precipitation rate; see :ref:`sec:RainLane`
   * - ``SWrad``
     - both
     - W m\ :sup:`-2`
     - ``swrad_type``
     - Shortwave radiation
   * - ``LWrad``
     - both
     - W m\ :sup:`-2`
     - ``lwrad_type``
     - Downward longwave radiation
   * - ``tau_x``, ``tau_y``
     - flux
     - N m\ :sup:`-2`
     -
     - Eastward and northward surface stress
   * - ``SHflux``
     - flux
     - W m\ :sup:`-2`
     -
     - Sensible heat flux
   * - ``LHflux``
     - flux
     - W m\ :sup:`-2`
     -
     - Latent heat flux
   * - ``evap``
     - flux
     - kg m\ :sup:`-2` s\ :sup:`-1`
     -
     - Evaporation rate
   * - ``SST``
     - two-way
     - K
     -
     - Sea-surface temperature (REMORA's top-level temperature)
   * - ``Uoce``, ``Voce``
     - two-way
     - m s\ :sup:`-1`
     -
     - Eastward and northward surface current; with
       ``driver.couple_currents`` only

The REMORA key is the ``remora.<key>`` that configures that forcing in a
REMORA deck; setting it keeps the lane with REMORA (see
:ref:`sec:LaneProvenance`). REMORA interprets ``Qair`` as specific humidity
or as a relative-humidity fraction depending on its magnitude.

.. _sec:SurfaceCurrents:

Surface currents
^^^^^^^^^^^^^^^^

With ``driver.couple_currents = true`` (two-way only), REMORA sends its
top-level current as east and north components, remapped with the SST's
weights and coverage. ERF then computes its surface stress from the wind
relative to the current, as COAWST's WRF does with ROMS's ``UOCE`` and
``VOCE``. The driver sets ERF's ``erf.use_coupled_currents`` itself; setting
that alone is an error. REMORA's own relative-wind option,
``remora.bulk_flux_relative_wind``, is the ocean-side counterpart for the
state contract.

.. _sec:VectorFrames:

Grid locations and vector components
------------------------------------

Every lane crosses at cell centers (REMORA's rho points). Vectors
(``Uwind``/``Vwind``, ``tau_x``/``tau_y``, ``Uoce``/``Voce``) cross as
eastward and northward components:

* ERF turns its vectors from its grid axes to east/north using its latitude
  and longitude.
* REMORA turns them onto its own grid axes with its grid ``angle``, and
  averages the stresses to its u and v faces.
* The driver remaps every lane with the same weights and rotates nothing.

The rotation-check decks described in :ref:`ExampleProblems` verify this on
the OCCAMS grids.

.. _sec:LaneProvenance:

Which model supplies each lane
------------------------------

Each atmosphere-to-ocean lane has exactly one source, resolved at startup and
printed as a provenance table (see :ref:`Output`). Each lane is resolved in
this order:

#. A lane the REMORA deck configures explicitly stays with REMORA.
#. Otherwise ERF supplies it, if ERF's pack fills it.
#. Otherwise the lane is **withheld**, and REMORA's own default stands.

At present ERF never fills ``Qair``; fills ``rain`` only with a microphysics
scheme that precipitates; fills ``SWrad`` and ``LWrad`` only with a radiation
model; and fills ``cloud`` only with cloud liquid or ice.

Withholding is how the driver declines a lane, not a failure. REMORA treats
any lane it receives as authoritative, so a lane of zeros would read as real
forcing and displace REMORA's own. Withheld lanes appear in validation output
as ``<lane>: withheld (not supplied by ERF)``.

The flux contract is the exception: REMORA drops the whole apply if any flux
lane is missing. So with ``driver.atm2ocn_mode = flux``, ``SWrad``, ``LWrad``
and ``rain`` come from ERF, or are zero where ERF computes none, even when the
REMORA deck sets its own (``remora.rain_type = netcdf``, for example). The
provenance table says so.

``LWrad`` gets one extra step. ``remora.lwrad_type`` defaults to
``computed``, under which REMORA's bulk fluxes ignore the field entirely, so
when the lane resolves to ERF the driver points REMORA at it. A deck that sets
``remora.lwrad_type`` owns the lane.

To override the resolution for one lane, set
``driver.atm2ocn_lane_source.<lane> = erf | remora | auto``, using the lane
name as printed. Asking for ``erf`` on a lane ERF cannot fill aborts rather
than passing an unwritten lane, and asking for ``remora`` on ``SWrad``,
``LWrad`` or ``rain`` under the flux contract also aborts.

.. _sec:RainLane:

The rain lane
-------------

REMORA takes rain as a rate in kg m\ :sup:`-2` s\ :sup:`-1` (1 kg m\ :sup:`-2`
s\ :sup:`-1` is 1 mm s\ :sup:`-1` of liquid water). ERF's microphysics keeps no
surface rate, only cumulative surface accumulations per column
(``rain_accum``, ``snow_accum`` and so on, in mm, which is kg m\ :sup:`-2` of
liquid water). ERF sums them as liquid water, using the scheme's total where
it has one, and on each pack sends the accumulation gained since its previous
pack divided by the ERF time elapsed since then:

* With time averaging off, the driver packs once per exchange, so the lane is
  exactly the mean rate over the exchange interval.
* With either averaging control on, ERF packs after every ERF step, and the
  driver averages those step rates weighted by step length rather than by the
  trapezoidal rule, which gives the same interval mean.

Either way the ocean receives exactly the water the atmosphere rained out over
the interval. The difference starts from the accumulators at the first ERF step
of the run, so a restart, whose accumulators come from the checkpoint, loses
nothing.

Snow, graupel and hail are sent as positive rain, since over open water they
freshen the ocean as rain does. (REMORA reads negative rain as snow, which ERF
never sends.) REMORA's rain heat flux then treats them as liquid, without the
latent heat of melting. A microphysics scheme without precipitation
(``Kessler_NoRain``, ``SAM_NoPrecip_NoIce``, ``SatAdj``, and so on) leaves the
lane to REMORA.

References
----------

Warner, J. C., B. Armstrong, R. He, and J. B. Zambon (2010). Development of a
Coupled Ocean–Atmosphere–Wave–Sediment Transport (COAWST) modeling system.
*Ocean Modelling*. https://doi.org/10.1016/j.ocemod.2010.07.010
