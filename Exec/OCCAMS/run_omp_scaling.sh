#!/bin/bash
#SBATCH -A m4304
#SBATCH -C cpu
#SBATCH -q debug
#SBATCH -N 2
#SBATCH -t 00:30:00
#SBATCH -J occams_omp
#SBATCH -o occams_omp_%j.out
#
# OpenMP thread sweep for the coupled driver on two Perlmutter CPU nodes.
#
# The total core count stays fixed at 2 x 128 physical cores, and each run trades
# MPI ranks for OpenMP threads: 1 thread x 256 ranks, 2 x 128, 4 x 64, 8 x 32,
# 16 x 16. Each rank gets 2*threads logical CPUs (one core per thread, with both
# hyperthreads of that core), the layout NERSC recommends for CPU nodes.
#
# Needs a driver built with -DERF_REMORA_ENABLE_OPENMP=ON (INSTALL.md, MPI + OpenMP
# build). A build without it ignores OMP_NUM_THREADS, so every run just measures
# fewer ranks. The script checks the log for AMReX's OpenMP banner and flags a run
# that lacks it.
#
# Runs happen one after another in Exec/OCCAMS, because the deck reads namelist.erf,
# NoahmpTable.TBL and the FILE= base decks from there. Plot and checkpoint
# output is turned off. Logs go to $OUT.
#
# Boxes: the deck's amr.max_grid_size of 64 gives 120 ERF and 108 REMORA boxes, so
# at 256 ranks about half the ranks would have none, and the 1-thread point would
# measure idle ranks rather than MPI-vs-OpenMP. The sweep uses 32 instead: 20 x 24 =
# 480 ERF boxes (637 x 754) and 18 x 24 = 432 REMORA boxes (563 x 751), at least
# one per rank at every point. Every point uses the same size, so the decomposition
# doesn't change across the sweep. Set MAX_GRID=64 to time the deck as written.
#
# Tiles: on CPU, AMReX hands OpenMP threads one tile at a time. The deck sets
# fabarray.mfiter_tile_size = 1024 1024 1024, so each box is one tile and threads
# can only share work by taking whole boxes. TILE="x y" overrides the horizontal
# tile size for every point, e.g. TILE="16 16"; left unset, the deck's value stands.
# z is always the whole column (1024000). The tile size is one AMReX setting shared
# by both codes: REMORA's loops assume whole columns (REMORA's own main forces
# 16 16 1024000, but the driver doesn't run it), and ERF's column loops (PBL,
# microphysics, implicit vertical solves) use TileNoZ, which keeps x and y and
# drops z anyway.
#
# Usage, from anywhere:
#   EXE=$SCRATCH/build_cpu_omp/erf-remora-driver sbatch Exec/OCCAMS/run_omp_scaling.sh
#
# Environment overrides:
#   EXE          driver executable (required)
#   DECK         inputs file in Exec/OCCAMS (default inputs_OCCAMS_maximal_1day)
#   THREADS      thread counts to sweep (default "1 2 4 8 16")
#   MAX_GRID     amr.max_grid_size_x/y for ERF and REMORA (default 32)
#   TILE         horizontal fabarray.mfiter_tile_size, "x y" (default: the deck's)
#   MAX_STEP     ocean steps per run (default 40; 40 x 15 s = 10 min, 60 ERF steps)
#   RUN_MINUTES  wall limit per run, so one slow run can't use up the job (default 5)
#   OUT          log directory (default $SCRATCH/occams_omp_<jobid>)
#   EXTRA_ARGS   additional driver key=value overrides

set -u

OCCAMS_DIR=${OCCAMS_DIR:-${SLURM_SUBMIT_DIR:-$PWD}}
# sbatch copies the script, so BASH_SOURCE doesn't point into the repo. Accept
# submission from the repo root or from Exec/OCCAMS.
[ -f "$OCCAMS_DIR/namelist.erf" ] || OCCAMS_DIR=$OCCAMS_DIR/Exec/OCCAMS

EXE=${EXE:?set EXE to the OpenMP driver executable}
DECK=${DECK:-inputs_OCCAMS_maximal_1day}
THREADS=${THREADS:-"1 2 4 8 16"}
MAX_GRID=${MAX_GRID:-32}
MAX_STEP=${MAX_STEP:-40}
TILE=${TILE:-}
RUN_MINUTES=${RUN_MINUTES:-5}
OUT=${OUT:-$SCRATCH/occams_omp_${SLURM_JOB_ID:-manual}}
EXTRA_ARGS=${EXTRA_ARGS:-}

TILE_ARGS=()
if [ -n "$TILE" ]; then
    read -r -a tile <<< "$TILE"
    [ ${#tile[@]} -eq 2 ] || { echo "TILE needs two integers (x y), got: $TILE" >&2; exit 1; }
    # ParmParse joins argv with spaces, so the three values can be separate words.
    TILE_ARGS=(fabarray.mfiter_tile_size="${tile[0]}" "${tile[1]}" 1024000)
fi

NNODES=${SLURM_JOB_NUM_NODES:-2}
CORES_PER_NODE=128
TOTAL_CORES=$((NNODES * CORES_PER_NODE))

for f in "$EXE" "$OCCAMS_DIR/$DECK" "$OCCAMS_DIR/namelist.erf" \
         "$OCCAMS_DIR/NoahmpTable.TBL"; do
    [ -e "$f" ] || { echo "missing: $f" >&2; exit 1; }
done

mkdir -p "$OUT"
SUMMARY=$OUT/summary.txt
cd "$OCCAMS_DIR"

echo "driver : $EXE ($(date -r "$EXE" '+%Y-%m-%d %H:%M:%S'))"
echo "deck   : $OCCAMS_DIR/$DECK"
echo "nodes  : $NNODES ($TOTAL_CORES cores)  threads: $THREADS  max_step: $MAX_STEP"
echo "grid   : amr.max_grid_size_x/y = $MAX_GRID"
if [ -n "$TILE" ]; then
    echo "tiles  : fabarray.mfiter_tile_size = ${tile[0]} ${tile[1]} 1024000"
else
    echo "tiles  : fabarray.mfiter_tile_size = deck value"
fi
echo "logs   : $OUT"
echo

# Prefix every output line with wall-clock seconds, so the steady-state rate can be
# measured between exchanges, apart from start-up (file reads, remap weights).
stamp () {
    while IFS= read -r line; do
        printf '%s %s\n' "$EPOCHREALTIME" "$line"
    done
}

printf '%-8s %-6s %-8s %-10s %-10s %-12s %-10s %s\n' \
    threads ranks exit wall_s init_s s_per_exch tinyprof note > "$SUMMARY"

for t in $THREADS; do
    ranks=$((TOTAL_CORES / t))
    if [ $((ranks * t)) -ne "$TOTAL_CORES" ]; then
        echo "skipping $t threads: does not divide $TOTAL_CORES cores" >&2
        continue
    fi
    log=$OUT/out_t${t}_n${ranks}.txt

    export OMP_NUM_THREADS=$t
    export OMP_PLACES=threads
    export OMP_PROC_BIND=spread

    echo "=== $t threads x $ranks ranks -> $log"
    start=$EPOCHREALTIME
    timeout $((RUN_MINUTES * 60)) \
        srun -N "$NNODES" -n "$ranks" -c $((2 * t)) --cpu-bind=cores \
            "$EXE" "$DECK" \
            max_step="$MAX_STEP" \
            amr.max_grid_size_x="$MAX_GRID" amr.max_grid_size_y="$MAX_GRID" \
            ${TILE_ARGS[@]+"${TILE_ARGS[@]}"} \
            erf.plot_int_1=-1 erf.check_int=-1 \
            remora.plot_int=-1 remora.check_int=-1 \
            $EXTRA_ARGS 2>&1 | stamp > "$log"
    rc=${PIPESTATUS[0]}
    end=$EPOCHREALTIME

    # Steady state: mean time per exchange from the first completed exchange to the
    # last, which leaves out start-up and the first exchange.
    read -r init per_exch < <(awk -v s="$start" '
        / Completed exchange / { n++; if (n == 1) first = $1; last = $1 }
        END {
            if (n == 0) { print "-", "-"; exit }
            printf "%.1f %s\n", first - s,
                   (n > 1 ? sprintf("%.3f", (last - first) / (n - 1)) : "-")
        }' "$log")

    tiny=$(grep -m1 'TinyProfiler total time across processes' "$log" \
           | awk '{ print $(NF-2) }')   # the avg of [min...avg...max]

    note=""
    grep -qiE 'OMP initialized with [0-9]+ OMP threads' "$log" \
        || note="no OMP banner: build without OpenMP?"
    [ "$rc" -eq 124 ] && note="timed out after ${RUN_MINUTES} min $note"

    printf '%-8s %-6s %-8s %-10.1f %-10s %-12s %-10s %s\n' \
        "$t" "$ranks" "$rc" "$(awk -v a="$start" -v b="$end" 'BEGIN { print b - a }')" "$init" "$per_exch" \
        "${tiny:--}" "$note" >> "$SUMMARY"
    tail -n 1 "$SUMMARY"
done

echo
cat "$SUMMARY"
