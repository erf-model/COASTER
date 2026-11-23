.. _GettingStarted:

Getting Started
===============

This page gets a first coupled run going on a workstation: clone COASTER with
its submodules, build the ``coaster`` executable, and run the idealized
Upwelling case, which needs no external data.

Quick start
-----------

.. code-block:: bash

   git clone --recursive git@github.com:erf-model/COASTER
   cd COASTER
   cmake -S . -B build
   cmake --build build -j 8 --target coaster
   cd Exec/Upwelling
   ../../build/coaster inputs_oneway max_step=10

ERF, REMORA and AMReX are git submodules under ``Submodules/``. The
``--recursive`` clone fetches them; in an existing clone, run
``git submodule update --init --recursive``.

The default build uses MPI and enables ERF's RRTMGP radiation and NetCDF
support. See :ref:`Building` for the options, the MPI + OpenMP build, and HPC
systems.

Running a case
--------------

Run a coupled deck from its own directory. Each case is split into three
files: a coupled deck that sets the ``driver.*`` controls, and the ERF and
REMORA decks it imports with ``FILE =`` lines. Those paths are relative to the
directory the executable runs in, so running from elsewhere fails to find
them. Run the coupled deck, not ``inputs_ERF`` or ``inputs_REMORA`` directly.

Any parameter can be overridden on the command line after the deck, as with
``max_step=10`` above.

``inputs_oneway`` is ERF forcing REMORA with nothing returned to the
atmosphere. It is the case to run first on a new build. ``inputs_twoway``
adds the ocean-to-atmosphere SST return. See :ref:`ExampleProblems` for both
and for the realistic OCCAMS case, and :ref:`Output` for how to read what the
driver prints.

ERF cases that turn on radiation also need the RRTMGP coefficient data at run
time; see :ref:`Building`. The Upwelling case does not.
