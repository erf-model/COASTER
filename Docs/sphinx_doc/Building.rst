.. _Building:

Building
========

COASTER is built with a single CMake superbuild. It compiles AMReX, ERF and
REMORA from the submodules under ``Submodules/`` as libraries and links them
into the ``coaster`` executable. For build options that belong to one solver,
see the `ERF documentation <https://erf.readthedocs.io/en/latest/>`_ and the
`REMORA documentation <https://remora-ocean.readthedocs.io/en/latest/>`_.

MPI-only build (default)
------------------------

From the repository root:

.. code-block:: bash

   cmake -S . -B build
   cmake --build build -j 8 --target coaster

MPI + OpenMP build
------------------

Use a separate build directory to keep the MPI-only build.
``ERF_REMORA_ENABLE_OPENMP=ON`` also turns on ``Kokkos_ENABLE_OPENMP`` and
``Kokkos_ENABLE_SERIAL`` alongside the per-solver OpenMP flags, so those do not
need to be passed by hand:

.. code-block:: bash

   cmake -S . -B build_omp \
     -DCMAKE_C_COMPILER=mpicc \
     -DCMAKE_CXX_COMPILER=mpicxx \
     -DCMAKE_Fortran_COMPILER=mpif90 \
     -DERF_REMORA_ENABLE_OPENMP=ON
   cmake --build build_omp -j 8 --target coaster

.. _sec:CMakeOptions:

CMake options
-------------

These options belong to COASTER's top-level ``CMakeLists.txt``, not to ERF or
REMORA.

.. list-table::
   :header-rows: 1
   :widths: 35 15 50

   * - Option
     - Default
     - Meaning
   * - ``ERF_REMORA_ENABLE_MPI``
     - ``ON``
     - Build AMReX, ERF and REMORA with MPI.
   * - ``ERF_REMORA_ENABLE_OPENMP``
     - ``OFF``
     - Build with OpenMP, including the Kokkos OpenMP backend.
   * - ``ERF_REMORA_ENABLE_TESTS``
     - ``OFF``
     - Register the CTest suite; see :ref:`Testing`.
   * - ``ERF_REMORA_ENABLE_FCOMPARE``
     - same as ``ERF_REMORA_ENABLE_TESTS``
     - Build AMReX's ``fcompare``, used by the regression tests.
   * - ``ERF_REMORA_PARALLEL_TEST_NRANKS``
     - ``2;4``
     - MPI rank counts swept by the parallel tests. ``2;4;6;8`` gives the full
       sweep.

The superbuild also sets several solver options so that the coupled build
works without extra flags:

* ``ERF_ENABLE_MULTIBLOCK``, ``ERF_ENABLE_TINY_PROFILE`` and
  ``REMORA_ENABLE_TINY_PROFILE`` are forced on, and ``ERF_ENABLE_HDF5`` is
  forced off. With the TinyProfiler on, every run ends with a timing table.
* ``ERF_ENABLE_NETCDF``, ``ERF_ENABLE_PNETCDF``, ``REMORA_ENABLE_PNETCDF`` and
  ``ERF_ENABLE_RRTMGP`` default to on.
* ``ERF_ENABLE_CRAY_AUTO_FIXES`` defaults to on and detects a Cray environment
  itself.

Run-time data and tools
-----------------------

RRTMGP data files
^^^^^^^^^^^^^^^^^

ERF cases that turn on radiation need the RRTMGP coefficient data files at run
time. Set ``RRTMGP_DIR`` before running one:

.. code-block:: bash

   export RRTMGP_DIR=/path/to/rrtmgp-data-files

``erf.rrtmgp_file_path`` only has an effect when ERF is built with RRTMGP,
which the superbuild does by default.

``fcompare``
^^^^^^^^^^^^

With ``ERF_REMORA_ENABLE_FCOMPARE=ON`` the superbuild builds ``fcompare`` and
sets ``FCOMPARE_EXE`` to it at configure time. To use a different binary in
manual workflows, set it in the environment:

.. code-block:: bash

   export FCOMPARE_EXE=/path/to/fcompare

If ``FCOMPARE_EXE`` is not set, the helper script falls back to
``command -v fcompare`` and fails if none is on ``PATH``.

.. _sec:SymbolIsolation:

Linking ERF and REMORA into one executable
------------------------------------------

Linking both solvers into one executable raises two kinds of hazard:

#. **Header collisions.** Both solvers' public headers declare globally named
   symbols with the same names, such as ``Problem``, ``ProblemBase`` and
   ``SolverChoice``.
#. **Link-time collisions.** Both define ``amrex_probinit`` and other global
   symbols.

The superbuild avoids them as follows:

* Every collision-prone symbol carries an explicit prefix on both sides:
  ``ERFProblem``, ``ERFProblemBase``, ``ERFSolverChoice`` and ``erf_probinit``
  for ERF, and ``REMORAProblem``, ``REMORAProblemBase``, ``REMORASolverChoice``
  and ``remora_probinit`` for REMORA.
* ERF-only and REMORA-only includes are kept in separate translation units.
* Exchange between the solvers goes only through the driver's pack and apply
  calls; see :ref:`CouplingOverview`.
* Remaining duplicate global symbols are made file-local (``static``) in the
  solver repositories.

In a static-library build, the weak ``amrex_probinit`` can be skipped during
archive extraction and resolve to a null call target. ERF guards against this
with a small link-anchor symbol, referenced from ``ERF.cpp``, that forces its
problem-initialization file to be extracted.

.. _sec:BuildingPerlmutter:

Perlmutter (NERSC)
------------------

This is the build used for the OCCAMS cases, which need NetCDF and PNetCDF for
the WRF input and the REMORA grid and forcing files.

Environment:

.. code-block:: bash

   source Submodules/ERF/Build/machines/perlmutter_erf.profile
   module load cray-parallel-netcdf

The profile loads ``gcc-native``, ``cmake``, ``cudatoolkit``,
``cray-hdf5-parallel``, ``cray-netcdf-hdf5parallel`` and ``cray-libsci``. It
leaves ``cray-parallel-netcdf`` out, which is why that module is loaded
separately; without it, REMORA's PNetCDF reads do not link.

Configure and build:

.. code-block:: bash

   cmake -S . -B build_cpu_noahmp \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_C_COMPILER=cc \
     -DCMAKE_CXX_COMPILER=CC \
     -DCMAKE_Fortran_COMPILER=ftn \
     -DERF_ENABLE_NOAHMP=ON
   cmake --build build_cpu_noahmp -j16

Everything else the OCCAMS build needs is a default or is set by the
superbuild (see :ref:`sec:CMakeOptions`). Notes on this configuration:

* ``ERF_ENABLE_RRTMGP`` is on. ``inputs_OCCAMS_maximal_1day`` uses it; the
  other OCCAMS decks run without radiation.
* ``ERF_ENABLE_NOAHMP`` pulls in the Noah-MP submodule, which is Fortran,
  hence ``-DCMAKE_Fortran_COMPILER=ftn``. It makes
  ``erf.land_surface_model = NOAHMP`` available at run time; the OCCAMS decks
  still run with the land model off.

.. warning::

   ``cmake --build`` leaves the previous executable in place when it fails, so
   a failed rebuild followed by a run silently runs the old binary. Check that
   the build succeeded before running, especially when looking for
   diagnostics that only the new code prints.

This recipe was last verified with ``cpe/26.03``, ``gcc-native/13.2``,
``cray-mpich/9.0.1``, ``cray-hdf5-parallel/1.14.3.9``,
``cray-netcdf-hdf5parallel/4.9.0.13`` and ``cray-parallel-netcdf/1.12.3.13``.
The profile loads the Cray defaults, so when NERSC changes them an existing
binary stops loading with an error such as
``error while loading shared libraries: libhdf5_hl_parallel_gnu_123.so.200``.
Reconfigure and rebuild into a new directory named for what it contains,
rather than reconfiguring the old one, which records what was run.

Converting REMORA input files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

REMORA reads its NetCDF input through PNetCDF, which cannot open NetCDF-4
files. Convert them with ``nccopy -k cdf5 in.nc out.nc`` (the REMORA
documentation gives the NCO equivalent, ``ncks -5``). CDF-2 works for the
OCCAMS grid, initial and boundary files. The climatology must be CDF-5,
because its ``ocean_time`` axis is not a record dimension and each 3-D field
exceeds CDF-2's 4 GiB per-variable limit.

Running on Perlmutter
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   salloc -N 1 --constraint cpu -A <account> -t 01:00:00 --qos interactive
   cd Exec/OCCAMS
   ./run_occams.sh smoke    # one ocean step: startup and one exchange
   ./run_occams.sh          # oneway, state and flux

See :ref:`ExampleProblems` for what each OCCAMS deck covers, and
``Exec/OCCAMS/run_occams.sh`` for per-case runs and rank overrides.
