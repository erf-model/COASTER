.. COASTER documentation master file.

COASTER
=======

COASTER couples the atmosphere model `ERF <https://github.com/erf-model/ERF>`_
and the ocean model `REMORA <https://github.com/remora-ocean/REMORA>`_ in a
single executable. A driver owns the coupling clock, remaps the exchanged
fields between the two grids, and moves surface state and fluxes between the
solvers. ERF and REMORA never call each other directly.

ERF, REMORA and the `AMReX <https://github.com/AMReX-Codes/amrex>`_ framework
they are built on each have their own documentation. This documentation covers
what COASTER adds: how a coupled run is built and configured, which fields
cross between the models and how, the remapping and time-coupling algorithms,
and the assumptions behind them. Anything already documented upstream is
summarized and linked rather than repeated.

* `ERF documentation <https://erf.readthedocs.io/en/latest/>`_
* `REMORA documentation <https://remora-ocean.readthedocs.io/en/latest/>`_
* `AMReX documentation <https://amrex-codes.github.io/amrex/docs_html/>`_

.. toctree::
   :caption: USER GUIDE
   :maxdepth: 1

   GettingStarted
   Building
   Inputs
   ExampleProblems
   Output
   Glossary
   HowToCite

.. toctree::
   :caption: THEORY
   :maxdepth: 1

   theory/CouplingOverview
   theory/CouplingContract
   theory/TimeCoupling
   theory/Remapping
   theory/Assumptions

.. toctree::
   :caption: IMPLEMENTATION
   :maxdepth: 1

   CodeStructure
   ParallelLayout
   CheckpointRestart
   Diagnostics

.. toctree::
   :caption: COASTER vs COAWST
   :maxdepth: 1

   COASTERvsCOAWST

.. toctree::
   :caption: TESTING
   :maxdepth: 1

   Testing
   Verification

Indices and tables
==================

* :ref:`search`
