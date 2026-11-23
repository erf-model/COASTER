.. _CheckpointRestart:

Checkpoint and Restart
======================

A coupled run is checkpointed by the two solvers themselves; the driver
writes no checkpoint of its own. On restart, the driver reads both solvers'
checkpoint headers, checks that they describe the same coupled time, and
resumes the coupling clock from there. A restarted run reproduces an
uninterrupted one; the restart tests check this (see :ref:`Verification`).

Writing checkpoints
-------------------

Use each solver's own checkpoint controls, as in ``Exec/Upwelling/inputs_twoway``:

.. code-block:: text

   erf.check_file    = erfchk
   erf.check_int     = 2000      # ERF steps
   remora.check_file = remorachk
   remora.check_int  = 20        # ocean steps

The driver removes the shared ``amr.check_int``, ``amr.check_per`` and
``amr.check_int_time`` keys after the solvers are initialized, so set the
solver-prefixed ones.

Choose the two intervals so that ERF and REMORA write checkpoints at the same
times, and on exchange boundaries. In the example above, with 100 ERF steps
and one ocean step per exchange, both write every 20 exchanges. A restart
needs one checkpoint from each solver at the same coupled time.

Nothing else needs saving. The time-averaging accumulators are consumed within
each exchange interval (see :ref:`sec:TimeAveraging`), the remap weights are
rebuilt at startup, and ERF's surface precipitation accumulators, from which
the rain lane is differenced, are part of ERF's checkpoint.

Restarting
----------

Set both restart keys together:

.. code-block:: text

   erf.restart    = erfchk02000
   remora.restart = remorachk00020

Setting only one is an error, and so is ``amr.restart``.

``max_step`` and ``stop_time`` keep their meaning as the end of the whole run,
counted from the original start, not from the restart. The driver subtracts
the ocean steps already completed, and aborts if the checkpoint is already
past the requested end.

Checks on restart
^^^^^^^^^^^^^^^^^

The driver reads the step, time step and time from each checkpoint's
``Header`` and aborts unless:

* each checkpoint is self-consistent: its time equals its step count times
  its time step (plus ``driver.ocean_time_offset`` for REMORA);
* the two checkpoints are at the same coupled time, after removing the ocean
  clock offset from REMORA's time;
* that time is a whole number of the configured ERF and REMORA time steps,
  and falls on an exchange boundary.

If a checkpoint's time step differs from the one now configured, the driver
warns and continues, as long as the checkpoint time still lines up with the
configured cadence. It then prints the restored state:

.. code-block:: text

   Restored coupled restart state: time=... atm_tick=... completed_ocean_steps=...

On a restart the first interval's atmosphere-to-ocean average is formed
normally, since ERF's flux arrays are restored from the checkpoint; the
cold-start reconstruction described in :ref:`TimeCoupling` applies only to a
cold start.
