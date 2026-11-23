.. _TimeCoupling:

Time Coupling
=============

This page describes how the two solvers are advanced relative to each other
and how atmosphere-to-ocean fields are sampled in time.

.. note::

   This page is still being written. The order of operations within an
   exchange, ``driver.ocean_time_offset`` and the full set of cadence rules
   will be added.

The exchange interval
---------------------

The solvers exchange every ``driver.exchange_interval`` seconds, which
defaults to ``remora.fixed_dt``. Within each interval ERF takes several steps
of ``erf.fixed_dt`` and REMORA one or more steps of ``remora.fixed_dt``. The
driver aborts at startup unless the interval is an integer multiple of both
time steps, and unless ``max_step``, which counts ocean steps, ends on an
exchange boundary.

The atmosphere-to-ocean pack happens after ERF has advanced through the
interval, so the ocean is forced with atmospheric fields from the end of the
interval (or their average over it, below), including on the first exchange.

.. _sec:TimeAveraging:

Time averaging of atmosphere-to-ocean fields
--------------------------------------------

By default the driver passes the atmosphere state at the end of each exchange
interval. Two independent controls, both off by default, replace selected
lanes with their trapezoidal mean over the same interval:

* ``driver.time_average_atm2ocn_state = 1`` averages the state-character
  lanes: ``Uwind``, ``Vwind``, ``Patm``, ``Qair``, ``Tair`` and ``cloud``.
* ``driver.time_average_atm2ocn_flux = 1`` averages the flux-character lanes:
  ``rain``, ``SWrad``, ``LWrad``, ``tau_x``, ``tau_y``, ``SHflux``, ``LHflux``
  and ``evap``.

The control is chosen by the lane's character, not by
``driver.atm2ocn_mode``. In particular ``rain``, ``SWrad`` and ``LWrad``
follow the flux control even though they are also part of the state contract.
The controls can be used separately or together. Lanes that are not averaged
keep the interval-end sample, and exchange plotfiles of averaged fields are
stamped at the interval midpoint.

The averages are accumulated and consumed within one exchange interval, so
they are not part of the checkpoint.

``rain`` is always an interval mean, under either control or neither; see
:ref:`sec:RainLane`.

Cold start
^^^^^^^^^^

On the first interval of a cold start, ERF's diagnostic flux arrays are still
zero, so the left endpoint of the interval is not sampled. It is reconstructed
by linear extrapolation from the first two substep samples,

.. math::

   f(t_0) = 2 f_1 - f_2 .

With two substeps per interval, the trapezoidal mean is then :math:`f_1`, the
value at the interval midpoint, and :math:`f_2` carries no weight. ``rain`` is
weighted per ERF step instead, so this reconstruction does not apply to it.
