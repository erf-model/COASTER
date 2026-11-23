# Exec

This directory holds the coupled cases. Each is split into a coupled deck that
sets the `driver.*` controls and the two solver decks it imports with
`FILE =`. Run the coupled deck, from its own directory.

- `Upwelling/` — idealized coastal upwelling; needs no external data
- `OCCAMS/` — realistic regional domain; needs data on NERSC systems

They are documented in the COASTER documentation under `Docs/sphinx_doc`:

- `ExampleProblems.rst` — what each deck covers and how to run it
- `Output.rst` — how to read the driver's diagnostics
- `Testing.rst` — the CTest suite built on the Upwelling decks
