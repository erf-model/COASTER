.. _Building:

Building
========

How COASTER is built. A single CMake superbuild compiles AMReX, ERF and REMORA as libraries and links them into the ``coaster`` executable. For build options that belong to one solver, see the ERF and REMORA build documentation.

.. note::

   This page is being written. It will cover:

   * The superbuild and its CMake options
   * MPI-only and MPI + OpenMP builds
   * Symbol isolation between ERF and REMORA
   * Required data files (RRTMGP) and helper tools (``fcompare``)
   * Building on HPC systems (Perlmutter)
   * Known build limitations

.. Content to migrate here: INSTALL.md (Prerequisites, Build); Docs/symbol-isolation.md
