.. _CouplingOverview:

Coupling Overview
=================

COASTER advances ERF (atmosphere) and REMORA (ocean) in one executable. Both
solvers are built as libraries, and a driver owns everything that connects
them.

The architectural rule
----------------------

ERF and REMORA never call each other directly. The driver owns:

* the coupling clock, which decides when each solver advances and when they
  exchange;
* the exchange caches, one ``Vector<MultiFab*>`` per direction, which hold the
  exchanged fields (see :ref:`CouplingContract`);
* the remapping between the two grids (see :ref:`Remapping`);
* the calls that move data between the solvers and the caches.

This follows the "conductor" pattern used in AMReX multiblock coupling work,
and keeps the changes needed inside each solver small.

Pack and apply
--------------

Data crosses between the solvers in two steps:

#. The source solver **packs** its surface state into the driver's cache for
   that direction. ERF packs near-surface atmospheric state, or surface
   fluxes, depending on the contract; REMORA packs its SST and, optionally, its
   surface current.
#. The driver remaps the cache onto the destination grid, and the destination
   solver **applies** it as surface forcing or as a surface boundary condition.

The pack and apply calls are the only interface between the solvers.

One-way and two-way coupling
----------------------------

``driver.coupling_direction`` selects the direction:

``ERFtoREMORA``
   One-way. ERF forces REMORA; nothing returns to the atmosphere, which keeps
   its own SST.

``two_way``
   Both directions. In addition to the atmosphere-to-ocean exchange, REMORA's
   SST replaces ERF's surface temperature over the ocean, through ERF's
   coupled-SST path (``erf.use_coupled_sst``, which the driver sets). With
   ``driver.couple_currents = true``, REMORA's surface current is also sent to
   ERF; see :ref:`sec:SurfaceCurrents`.

How the two solvers are advanced relative to each other within an exchange is
described in :ref:`TimeCoupling`.
