.. _Testing:

Testing
=======

COASTER's tests are registered with CTest when the build is configured with
``-DERF_REMORA_ENABLE_TESTS=ON``. Most of them run the Upwelling decks with
command-line overrides; OCCAMS is not in the suite, since its external data is
not in the repository. :ref:`Verification` describes what the tests establish.

Building for the tests
----------------------

The test scripts expect a lightweight build without radiation or NetCDF:

.. code-block:: bash

   cmake -S . -B build_ci \
     -DCMAKE_BUILD_TYPE=RelWithDebInfo \
     -DCMAKE_C_COMPILER=mpicc \
     -DCMAKE_CXX_COMPILER=mpicxx \
     -DERF_REMORA_ENABLE_TESTS=ON \
     -DREMORA_ENABLE_PNETCDF=OFF \
     -DERF_ENABLE_NETCDF=OFF \
     -DERF_ENABLE_RRTMGP=OFF
   cmake --build build_ci --parallel

``ERF_REMORA_PARALLEL_TEST_NRANKS`` (default ``2;4``) sets the MPI rank counts
the parallel tests sweep; pass ``"2;4;6;8"`` for the full sweep.

Running the suite
-----------------

Run the suite one label at a time, not in a single ``ctest`` call:

.. code-block:: bash

   ctest --test-dir build_ci -L compile  --output-on-failure --no-tests=error
   ctest --test-dir build_ci -L coupling --output-on-failure --no-tests=error
   ctest --test-dir build_ci -L restart  -j4 --output-on-failure --no-tests=error
   ctest --test-dir build_ci -L parallel -j4 --output-on-failure --no-tests=error

The labels are ``compile``, ``coupling``, ``parallel``, ``reproducer`` and
``restart``.

.. warning::

   ``compile_coaster`` must not run alongside any other test. It invokes the
   build, which relinks the driver and replaces the binary underneath any test
   currently running it. Those tests die with ``SIGILL`` (exit code 132) and an
   ``mpiexec ... could not access or execute`` message that points at the
   executable rather than at the cause. A plain ``ctest -jN`` over the whole
   suite schedules the compile test alongside the others and produces exactly
   these failures. The CI workflow runs ``ctest`` once per label for this
   reason.

Within a label, running tests concurrently is fine: each test has its own
working directory, and ``PROCESSORS`` is set from the rank count so ``ctest``
does not oversubscribe the larger MPI tests. Two suites sharing one build
directory do collide, because the working directories are named by test, not
by run; use separate build directories.

Test names
----------

The Upwelling tests are generated from the coupling options, so any slice can
be selected with ``-R``:

.. code-block:: text

   reproducer_restart_<direction>_<contract>_<variant>
   parallel_upwelling_<direction>_<contract>_<variant>_np<N>_<kind>

``<direction>``
   ``oneway`` or ``twoway``.

``<contract>``
   ``state`` or ``flux``.

``<variant>``
   ``matched`` (one ocean step per atmosphere step), ``substep`` (several
   atmosphere steps per ocean step), or ``average_state_lanes_substep`` /
   ``average_flux_lanes_substep`` (substepping with that contract's
   time-averaging control on).

``<N>``
   A rank count from ``ERF_REMORA_PARALLEL_TEST_NRANKS``.

``<kind>``
   ``smoke`` (does it run) or ``compare_to_np1`` (does it match the serial
   run).

Two more restart tests, ``reproducer_restart_independent_exchange_30`` and
``_60``, run ``inputs_twoway`` with the flux contract and time-averaged flux
lanes, with ``driver.exchange_interval`` set to 30 or 60 s so that both
solvers take several steps per exchange.

Running one test or one slice
-----------------------------

A single test:

.. code-block:: bash

   ctest --test-dir build_ci -R '^reproducer_restart_twoway_state_matched$' \
     --output-on-failure

Anchor the regular expression with ``^...$``. Without it,
``-R parallel_upwelling_twoway_state`` matches every variant and rank count,
and ``-R ..._np4`` also matches the paired ``_smoke`` test. Use ``-N`` to list
what a selection would run without running it:

.. code-block:: bash

   ctest --test-dir build_ci -N -R np4_compare_to_np1

A slice across the matrix, for example one contract at one rank count:

.. code-block:: bash

   ctest --test-dir build_ci -R '_flux_.*_np4_compare_to_np1' --output-on-failure
   ctest --test-dir build_ci -R 'reproducer_restart_twoway' --output-on-failure

Other tests
-----------

``compile_coaster``
   The build gate; other tests depend on it.

``coupled_cadence``
   A unit test of the cadence arithmetic: steps per exchange, the exchange
   boundary check, and rejection of intervals that are not a multiple of both
   time steps.

``reproducer_coupled_sst_coverage``
   Runs ``inputs_twoway`` four times with different
   ``driver.remap_min_coverage_frac`` values and domain overrides, and checks
   the counts of covered cells rather than temperatures. It is the only test
   that exercises the coverage threshold, since the Upwelling grids are
   otherwise fully covered.

``reproducer_coupled_surface_current``
   Checks ``driver.couple_currents``: the ocean-to-atmosphere exchange
   plotfile carries nonzero ``Uoce`` and ``Voce``; ERF's velocities differ
   from a run without the current by far more than two runs without it differ
   from each other; and the option without two-way coupling, or
   ``erf.use_coupled_currents`` without the driver option, stops at startup.

``reproducer_lane_provenance``
   Runs ``inputs_oneway`` three times, once per contract and averaging
   combination, and checks the ``exchange_info`` file in each exchange
   plotfile: every lane belongs to its contract exactly once and in contract
   order, and each lane's character and averaging follow the contract and the
   ``driver.time_average_atm2ocn_*`` controls.

``reproducer_cold_start_average``
   Runs ``inputs_oneway`` with two atmosphere steps per exchange and checks,
   lane by lane at zero tolerance, that every averaged lane of the first
   exchange plotfile holds the atmosphere state after its first step, and that
   an unaveraged lane holds the state after its second (see
   :ref:`sec:TimeAveraging`). ``rain`` is not checked, since it is weighted per
   ERF step. Without RRTMGP, ``SWrad``, ``LWrad``, ``Qair`` and ``cloud`` do
   not change over those two steps, so the test cannot check their weights.

``reproducer_nonfinite_guards`` and ``parallel_nonfinite_guards_np<N>``
   Run ``inputs_twoway`` four times with ``driver.debug_inject_nan_lane`` and
   ``amrex.fpe_trap_invalid = 0``. Each run must abort with the message of the
   guard meant to catch its NaN: the two post-pack checks (SST, Tair), and the
   wet-cell validation count on a state lane (Tair) and a stress lane
   (tau_x). See :ref:`Diagnostics`.

The CI workflow runs only the ``compile``, ``restart`` and ``parallel``
labels, so it runs ``parallel_nonfinite_guards_np<N>`` but not the serial
tests above. Run those locally with ``-L coupling``.

What the suite does not cover
-----------------------------

The Upwelling decks are matched one to one, entirely ocean, with uniform SST
and uniform surface stress. That makes them blind to the spherical remap, wet
masks, partial coverage and donor fill. A passing suite means no regression
against the idealized case; it is not evidence that the coverage or masking
paths work. Those first run in the OCCAMS cases:

.. code-block:: bash

   cd Exec/OCCAMS
   ./run_occams.sh smoke      # startup and one exchange
   ./run_occams.sh            # oneway, state, flux
