.. _CouplingOverview:

Coupling Overview
=================

The overall design of a coupled COASTER run: what the driver owns, how ERF and REMORA are advanced as libraries, and how one-way and two-way coupling differ.

.. note::

   This page is being written. It will cover:

   * The architectural rule: the driver owns the clock and the exchange; the solvers never call each other
   * One-way versus two-way coupling
   * Pack and apply: how each solver hands state to and receives state from the driver
   * What runs where in a coupled time step

.. Content to migrate here: README.md (Architectural Rule, Coupling Roadmap)
