# COASTER

COASTER couples the atmosphere model [ERF](https://github.com/erf-model/ERF)
and the ocean model [REMORA](https://github.com/remora-ocean/REMORA) in a
single executable. A driver owns the coupling clock, remaps the exchanged
fields between the two grids, and moves surface state and fluxes between the
solvers. ERF and REMORA never call each other directly.

## Quick start

```bash
git clone --recursive git@github.com:erf-model/COASTER
cd COASTER
cmake -S . -B build
cmake --build build -j 8 --target coaster
cd Exec/Upwelling
../../build/coaster inputs_oneway max_step=10
```

## Documentation

The user documentation is at <https://coaster-model.readthedocs.io/en/latest/>:
building, inputs, the example problems, how to read the driver's output, the
coupling contract, time coupling, remapping, and testing. Its source is in
`Docs/sphinx_doc`; to build it locally:

```bash
pip install -r Docs/sphinx_doc/requirements.txt
make -C Docs/sphinx_doc html
```

and open `Docs/sphinx_doc/_build/html/index.html`.

ERF and REMORA have their own documentation:

- ERF: <https://erf.readthedocs.io/en/latest/>
- REMORA: <https://remora-ocean.readthedocs.io/en/latest/>

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to contribute to COASTER
development. All participants are expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).

## Citation

See [CITATION.md](CITATION.md) for the ERF and REMORA papers to cite when
using COASTER.
