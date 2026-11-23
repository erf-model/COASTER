.. _Diagnostics:

Diagnostics and Debugging
=========================

COASTER checks the exchanged fields for non-finite values and, at higher
verbosity, validates their ranges on every exchange. For the coverage and
remap diagnostics, see :ref:`Output`.

Non-finite guards
-----------------

Every packed lane is checked for NaN and infinity right after it is packed,
in every valid cell (land included) and every component, at any verbosity:

.. code-block:: text

   Non-finite value detected in PackSurfaceState output, lane '<name>'.
   Non-finite value detected in PackAtmosphericStates output, lane '<name>'.

Either one aborts the run before the bad values reach the other solver. The
check tests each value (``MultiFab::contains_nan`` and ``contains_inf``)
rather than looking at the minimum and maximum. A min/max reduction is not a
reliable NaN test: ``amrex::min(d, r)`` is ``(r < d) ? r : d``, so a NaN
survives the reduction only if it is visited first, which depends on the rank
count, the box layout and the GPU block layout.

Field validation
----------------

Under ``driver.v = 1``, the per-exchange validation lines (``Post-pack``,
``Pre-apply``, ``Post-apply``) also count non-finite values over wet cells and
abort on a nonzero count:

.. code-block:: text

   Post-pack atmos->ocean validation: <n> non-finite value(s) in field '<name>' (wet only) at ocean_step=<s>

The minimum and maximum they print cover the finite wet cells only.

On CPU, ``amrex.fpe_trap_invalid = 1`` (set in the Upwelling decks) often
traps first. On GPU nothing traps, so these checks are the only thing that
stops a NaN.

Testing the guards
------------------

``driver.debug_inject_nan_lane = <lane>`` writes a NaN into one cell of that
lane on every exchange, to check that the guards fire. Adding
``driver.debug_inject_nan_after_guard = 1`` writes it after the post-pack
check instead, so that only the ``driver.v = 1`` validation can catch it; this
works for atmosphere-to-ocean lanes only. Both are test hooks, and a run with
them set is expected to abort.
