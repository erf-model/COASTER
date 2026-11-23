.. _Inputs:

Inputs
======

How the inputs for a coupled run are organized, and a reference for every ``driver.*`` parameter. Parameters that belong to ERF (``erf.*``) or REMORA (``remora.*``) are documented upstream; this page covers only the ones COASTER reads, and the solver parameters COASTER constrains.

.. note::

   This page is being written. It will cover:

   * Structure of a coupled deck: a top-level file that imports ``inputs_ERF`` and ``inputs_REMORA``
   * Which settings stay with each solver, and which the driver requires (``fixed_dt`` divisibility, ``max_step`` counted in ocean steps)
   * ``driver.*`` reference: coupling mode and cadence
   * ``driver.*`` reference: remapping
   * ``driver.*`` reference: output and diagnostics
   * ``driver.*`` reference: parallel layout
   * ``driver.*`` reference: debugging

.. Content to migrate here: INSTALL.md (Unified Inputs Example); Exec/README.md (Inputs); Source/main.cpp and Source/CoasterMBContainer.cpp ParmParse queries
