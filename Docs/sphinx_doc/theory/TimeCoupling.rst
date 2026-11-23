.. _TimeCoupling:

Time Coupling
=============

This page describes how the two solvers are advanced relative to each other,
when they exchange, and how atmosphere-to-ocean fields are sampled in time.

The exchange interval
---------------------

The solvers exchange every :math:`\Delta t_x` = ``driver.exchange_interval``
seconds, which defaults to ``remora.fixed_dt``. Both solvers run at fixed time
steps, and the interval must hold a whole number of each:

.. math::

   \Delta t_x = n_a \, \Delta t_a = n_o \, \Delta t_o ,

where :math:`\Delta t_a` = ``erf.fixed_dt``, :math:`\Delta t_o` =
``remora.fixed_dt``, and :math:`n_a, n_o \ge 1`. The driver checks this at
startup, to a relative tolerance of :math:`10^{-8}`, and aborts otherwise. For
example, ``erf.fixed_dt = 10``, ``remora.fixed_dt = 15`` and
``driver.exchange_interval = 300`` give 30 ERF steps and 20 REMORA steps per
exchange, while an interval of 15 s is rejected because it is not a multiple
of 10 s.

The driver keeps time with integer step counters rather than by accumulating
floating-point time, so the two clocks do not drift apart. It also checks that
each solver actually took the time step it was asked to, and aborts on any
mismatch.

When the run ends
^^^^^^^^^^^^^^^^^

The run length is set by ``max_step``, which counts ocean steps, by
``stop_time``, or by both, in which case the earlier wins. The driver only
stops on an exchange boundary: ``max_step`` must be a multiple of :math:`n_o`,
and a ``stop_time`` that falls inside an interval is rounded down to the
previous boundary, with a warning. At the end, each solver writes its
final-time output, as its own plotfile and checkpoint controls specify.

Order of operations
-------------------

Each exchange interval :math:`[t, t + \Delta t_x]` proceeds as follows:

#. **Ocean to atmosphere** (two-way runs). REMORA packs its SST (and surface
   current, with ``driver.couple_currents``) at time :math:`t`. The driver
   remaps it to ERF's grid and applies it to ERF once, before ERF's first
   step.
#. **Advance the atmosphere.** ERF takes :math:`n_a` steps from :math:`t` to
   :math:`t + \Delta t_x`, holding the ocean state from step 1 fixed. With
   time averaging on, the atmosphere-to-ocean lanes are sampled after every
   ERF step.
#. **Atmosphere to ocean.** ERF packs the atmosphere-to-ocean lanes at
   :math:`t + \Delta t_x`, or the driver forms their average over the
   interval. The driver remaps them to REMORA's grid.
#. **Advance the ocean.** REMORA takes :math:`n_o` steps from :math:`t` to
   :math:`t + \Delta t_x`. The same atmospheric forcing is applied before every
   REMORA step, since REMORA may refresh its forcing arrays within a step.

The scheme is sequential, with the atmosphere leading. The ocean is forced
over an interval with atmospheric fields from that same interval, which have
already been computed. The atmosphere sees the SST from the start of the
interval, so the ocean's feedback lags by one exchange interval.

The atmosphere-to-ocean fields are packed after the atmosphere has advanced,
so they are live from the first exchange, including ERF's surface fluxes.

.. _sec:TimeAveraging:

Time averaging of atmosphere-to-ocean fields
--------------------------------------------

By default the driver passes the atmosphere state at the end of each exchange
interval. Two independent controls, both off by default, replace selected
lanes with their trapezoidal mean over the same interval, sampled at every ERF
step:

* ``driver.time_average_atm2ocn_state = 1`` averages the state-character
  lanes: ``Uwind``, ``Vwind``, ``Patm``, ``Qair``, ``Tair`` and ``cloud``.
* ``driver.time_average_atm2ocn_flux = 1`` averages the flux-character lanes:
  ``rain``, ``SWrad``, ``LWrad``, ``tau_x``, ``tau_y``, ``SHflux``, ``LHflux``
  and ``evap``.

The control is chosen by the lane's character, not by
``driver.atm2ocn_mode``. In particular ``rain``, ``SWrad`` and ``LWrad``
follow the flux control even though they are also part of the state contract.
Because the flux contract has no state-character lanes,
``driver.time_average_atm2ocn_state = 1`` with ``driver.atm2ocn_mode = flux``
is rejected at startup. The controls can otherwise be used separately or
together. Lanes that are not averaged keep the interval-end sample, and
exchange plotfiles of averaged fields are stamped at the interval midpoint.

When ERF takes more than one step per exchange and no active lane is averaged,
the driver prints a warning that REMORA is forced with the instantaneous
interval-end sample.

The averages are accumulated and consumed within one exchange interval, so
they are not part of the checkpoint; a restart always begins on an exchange
boundary.

``rain`` is always an interval mean, under either control or neither; see
:ref:`sec:RainLane`.

Cold start
^^^^^^^^^^

On the first interval of a cold start, ERF's diagnostic flux arrays are still
zero, so the left endpoint of the interval is not sampled. It is reconstructed
by linear extrapolation from the first two step samples,

.. math::

   f(t_0) = 2 f_1 - f_2 ,

which is exact for forcing that varies linearly in time. With two steps per
interval, the trapezoidal mean is then :math:`f_1`, the value at the interval
midpoint, and :math:`f_2` carries no weight. With one step per interval there
is nothing to extrapolate from, and the mean is the single sample
:math:`f_1`. ``rain`` is weighted per ERF step instead, so this reconstruction
does not apply to it. On a restart the endpoint is sampled normally.

.. _sec:OceanTimeOffset:

The ocean clock offset
----------------------

ERF's clock starts at 0. ``driver.ocean_time_offset`` (default 0) sets
REMORA's start time, so that REMORA's model time is the offset plus the
elapsed coupled time. This lets REMORA keep its own time reference, so that
its NetCDF boundary and forcing files, which are placed on REMORA's clock
(see ``remora.time_ref``), line up with the start of the coupled run. The
OCCAMS decks, for example, use an offset of 578 days from a 2020-01-01
reference date.

``max_step`` and ``stop_time`` are always given in elapsed time. With a
nonzero offset, the driver converts ``stop_time`` to REMORA's clock for REMORA
itself. REMORA's checkpoints hold REMORA's model time, and the driver allows
for the offset when it checks that ERF and REMORA checkpoints match on
restart.
