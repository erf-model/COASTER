.. _Verification:

Verification
============

These are the checks used to establish that coupling is correct. Most are
automated in the CTest suite; see :ref:`Testing` for how to build and run it.
Prefer the suite to running these checks by hand: it covers more cases.

Rank independence
-----------------

.. code-block:: bash

   ctest --test-dir build_ci -L parallel --output-on-failure --no-tests=error

For every Upwelling direction, contract and cadence, each rank count in
``ERF_REMORA_PARALLEL_TEST_NRANKS`` runs once as a smoke test and once
compared against the serial run with ``fcompare``.

Restart
-------

.. code-block:: bash

   ctest --test-dir build_ci -L restart --output-on-failure --no-tests=error

Each test runs the same case uninterrupted and from a restart, across
direction, contract, cadence and time-averaging options, and compares the two.

Coverage
--------

.. code-block:: bash

   ctest --test-dir build_ci -R reproducer_coupled_sst_coverage --output-on-failure

Runs ``inputs_twoway`` four times and checks the counts of covered cells
rather than temperatures. It is the only test that exercises the coverage
threshold.

Flux coupling
-------------

This check is run by hand:

.. code-block:: bash

   cd Exec/Upwelling
   mpirun -n 1 ../../build/coaster inputs_twoway \
     driver.atm2ocn_mode=flux \
     driver.plot_int_exchange=1

Every ocean step, including the first, should export live flux lanes:
stress, sensible and latent heat, longwave radiation and evaporation. The
driver writes exchange plotfiles on every step. ``Exec/Upwelling/inputs_ERF``
sets nonzero surface-layer coefficients (``erf.most.Cd = 0.0014``,
``erf.most.Ch = 0.0012``, ``erf.most.Cq = 0.0012``), so ERF produces live
fluxes without overrides.

Vector rotation
---------------

The OCCAMS rotation-check decks verify that winds, stresses and surface
currents are turned correctly between the two grids' axes. See
:ref:`ExampleProblems`.

What verification does not cover
--------------------------------

The automated checks all use the Upwelling case, which is blind to the
spherical remap, wet masks, partial coverage and donor fill; see
:ref:`Testing`. Those paths first run in the OCCAMS cases.
