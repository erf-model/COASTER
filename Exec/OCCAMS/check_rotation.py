#!/usr/bin/env python3
"""Check that the atmosphere-ocean vectors are turned between the grid axes correctly.

Vectors cross the ERF-REMORA exchange as eastward/northward components: ERF turns its
wind and stress from its grid axes with its lat/lon, REMORA turns them onto its own axes
with its grid `angle`, and the surface current goes the other way. This checks it on a run
of the OCCAMS decks inputs_OCCAMS_rotcheck_state / _flux (see their comments).

  1. REMORA, exactly. The driver's atmos->ocean exchange plotfile holds the east/north
     lanes. Turned onto REMORA's axes with `angle` they must equal what REMORA applied:
     Uwind/Vwind in its history (state mode), or, made kinematic and averaged to the u/v
     faces, sustr/svstr (flux mode; the scale factor is fitted and should be -1/rho0).
  2. ERF, against WRF. ERF's grid-axis 10 m wind (u_10m, v_10m) turned with WRF's own
     COSALPHA/SINALPHA must match ERF's earth-relative u_east_10m/v_north_10m.
  3. End to end. At every ocean point, the direction of the wind REMORA applied, turned
     back to east/north, minus the direction of ERF's earth-relative 10 m wind there,
     against delta = ROMS angle - WRF alpha. A missing rotation gives a slope of 1 and an
     inverted one -1; the fix gives no trend. Scatter comes from the remap and the height
     of the wind ERF sends (its lowest cell, not 10 m).
  4. The surface current (with driver.couple_currents): the ocean->atmos exchange Uoce/Voce
     against REMORA's top-level current turned to east/north, as in 3.

usage:
  check_rotation.py --run DIR --wrfinput wrfinput_d01 [--history FILE] [--erf2d PREFIX]
                    [--rho0 1025]

DIR is the run directory (exchange_a2o*, exchange_o2a* and the ERF 2D plotfiles in it).
--history defaults to the one *_his_d01.nc in DIR; --erf2d to occams_rotcheck_erf_2d.
Needs numpy, scipy and netCDF4.
"""
import argparse
import glob
import os
import re
import sys

import numpy as np
from netCDF4 import Dataset
from scipy.spatial import cKDTree


# --------------------------------------------------------------------------- plotfiles
def read_plotfile(path):
    """Level 0 of an AMReX plotfile: (dict name -> 2D array [i, j] at the lowest k, time).

    Only what this check needs: one level, cell data, doubles or floats. Cells no box
    covers are NaN.
    """
    with open(os.path.join(path, "Header")) as f:
        lines = f.read().split("\n")
    nvar = int(lines[1])
    names = [lines[2 + n].strip() for n in range(nvar)]
    time = float(lines[2 + nvar + 1])
    dom = re.findall(r"\((-?\d+),(-?\d+),(-?\d+)\)", lines[2 + nvar + 6])
    lo = np.array(dom[0], dtype=int)
    hi = np.array(dom[1], dtype=int)
    shape = (hi[0] - lo[0] + 1, hi[1] - lo[1] + 1)
    out = {n: np.full(shape, np.nan) for n in names}

    with open(os.path.join(path, "Level_0", "Cell_H")) as f:
        cell_h = f.read()
    fabs = re.findall(r"FabOnDisk: (\S+) (\d+)", cell_h)
    for fname, offset in fabs:
        with open(os.path.join(path, "Level_0", fname), "rb") as f:
            f.seek(int(offset))
            header = b""
            while not header.endswith(b"\n"):
                header += f.read(1)
            h = header.decode()
            m = re.match(r"FAB \(\((\d+), \(([\d ]+)\)\),\((\d+), \(([\d ]+)\)\)\)", h)
            nbytes = int(m.group(3))
            order = m.group(4).split()
            endian = "<" if order[0] == str(nbytes) else ">"
            dtype = np.dtype(f"{endian}f{nbytes}")
            box = re.findall(r"\((-?\d+),(-?\d+),(-?\d+)\)", h)
            blo = np.array(box[0], dtype=int)
            bhi = np.array(box[1], dtype=int)
            ncomp = int(h.split(")")[-1])
            n = bhi - blo + 1
            data = np.fromfile(f, dtype=dtype, count=int(np.prod(n)) * ncomp)
            data = data.reshape((ncomp, n[2], n[1], n[0]))     # Fortran order on disk
        for c in range(ncomp):
            # lowest k of this box; the exchange and 2D plotfiles are one cell deep
            slab = data[c, 0].T                                 # [i, j]
            out[names[c]][blo[0] - lo[0]:bhi[0] - lo[0] + 1,
                          blo[1] - lo[1]:bhi[1] - lo[1] + 1] = slab
    return out, time


def plotfiles(run, prefix):
    return sorted(p for p in glob.glob(os.path.join(run, prefix + "[0-9]" * 5))
                  if os.path.isdir(p))


# --------------------------------------------------------------------------- helpers
def to_grid(east, north, angle):
    """East/north onto axes at `angle` from east (counterclockwise), as REMORA does."""
    c, s = np.cos(angle), np.sin(angle)
    return east * c + north * s, -east * s + north * c


def to_earth(u, v, angle):
    c, s = np.cos(angle), np.sin(angle)
    return u * c - v * s, u * s + v * c


def wrap_deg(x):
    return (x + 180.0) % 360.0 - 180.0


def unit_vectors(lon_deg, lat_deg):
    lon, lat = np.radians(lon_deg), np.radians(lat_deg)
    return np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])


def rel_err(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    scale = np.max(np.abs(b[ok])) if ok.any() else 0.0
    return (np.max(np.abs(a[ok] - b[ok])) / scale) if scale > 0 else np.nan


def slope_vs_delta(d_deg, delta_deg, label):
    """Least-squares slope of d against delta, with its standard error"""
    ok = np.isfinite(d_deg) & np.isfinite(delta_deg)
    x, y = delta_deg[ok], d_deg[ok]
    if x.size < 10 or np.ptp(x) == 0:
        print(f"  {label}: too few points, or delta does not vary")
        return
    A = np.column_stack([x, np.ones_like(x)])
    coef, res, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    se = np.sqrt(np.sum(resid ** 2) / (x.size - 2) / np.sum((x - x.mean()) ** 2))
    print(f"  {label}: {x.size} points, delta {x.min():.2f} to {x.max():.2f} deg; "
          f"median d {np.median(y):+.2f} deg")
    print(f"    slope of d against delta: {coef[0]:+.3f} +/- {se:.3f}   "
          f"(0 = turned correctly, +1 = not turned, -1 = turned the wrong way)")
    verdict = ("PASS" if abs(coef[0]) < 0.3 and abs(coef[0]) < abs(coef[0] - 1)
               and abs(coef[0]) < abs(coef[0] + 1) else "CHECK")
    print(f"    {verdict}")


# --------------------------------------------------------------------------- inputs
def load_history(path):
    h = Dataset(path)
    v = h.variables
    out = {"nrec": len(h.dimensions["ocean_time"]),
           "time": np.asarray(v["ocean_time"][:], dtype=float)}
    # rho points carry the boundary ring: REMORA cell (i, j) is [j+1, i+1]
    out["angle"] = (np.asarray(v["angle"][:], dtype=float) if "angle" in v
                    else None)
    # Grid fields may be written per record; take the first
    for name in ("mask_rho", "lon_rho", "lat_rho"):
        a = np.asarray(v[name][:], dtype=float) if name in v else None
        out[name] = a[0] if a is not None and a.ndim == 3 else a
    if out["angle"] is not None and out["angle"].ndim == 3:
        out["angle"] = out["angle"][0]
    out["h"] = h
    return out


def hist_rec(hist, name, rec):
    v = hist["h"].variables
    if name not in v:
        return None
    a = np.asarray(v[name][rec], dtype=float)
    if np.ma.isMaskedArray(v[name][rec]):
        a = np.ma.filled(v[name][rec].astype(float), np.nan)
    return a


def load_wrf(path):
    with Dataset(path) as w:
        lat = np.asarray(w["XLAT"][0], dtype=float)          # [south_north, west_east]
        lon = np.asarray(w["XLONG"][0], dtype=float)
        alpha = np.arctan2(np.asarray(w["SINALPHA"][0], dtype=float),
                           np.asarray(w["COSALPHA"][0], dtype=float))
    # ERF cell (i, j) is WRF mass point [j, i]
    return lat.T, lon.T, alpha.T


# --------------------------------------------------------------------------- checks
def check_remora_exact(run, hist):
    print("\n1. REMORA turns the exchanged east/north vectors onto its axes")
    a2o = plotfiles(run, "exchange_a2o")
    if not a2o:
        print("  no exchange_a2o plotfiles (driver.plot_int_exchange)")
        return
    ang = hist["angle"]
    if ang is None:
        print("  WARNING: the history has no angle; taking 0")
    for p in a2o:
        lanes, t = read_plotfile(p)
        nx, ny = next(iter(lanes.values())).shape
        a = np.zeros((nx, ny)) if ang is None else ang[1:ny + 1, 1:nx + 1].T
        if "Uwind" in lanes:
            ug, vg = to_grid(lanes["Uwind"], lanes["Vwind"], a)
            best = None
            for rec in range(hist["nrec"]):
                U = hist_rec(hist, "Uwind", rec)
                V = hist_rec(hist, "Vwind", rec)
                if U is None:
                    print("  the history has no Uwind (remora.output_forcing = true)")
                    return
                e = max(rel_err(ug, U[1:ny + 1, 1:nx + 1].T),
                        rel_err(vg, V[1:ny + 1, 1:nx + 1].T))
                if not np.isfinite(e):        # a record with no wind yet (t = 0)
                    continue
                if best is None or e < best[0]:
                    best = (e, rec)
            if best is None:
                print(f"  {os.path.basename(p)}: no history record with wind to compare")
                continue
            # Not turning at all, for scale
            e0 = max(rel_err(lanes["Uwind"], hist_rec(hist, "Uwind", best[1])[1:ny + 1, 1:nx + 1].T),
                     rel_err(lanes["Vwind"], hist_rec(hist, "Vwind", best[1])[1:ny + 1, 1:nx + 1].T))
            if best[0] < 1e-10:
                verdict = "PASS"
            elif e0 < best[0]:
                verdict = "CHECK: REMORA applied the winds unturned"
            else:
                verdict = "CHECK"
            print(f"  {os.path.basename(p)} (t={t:g}): winds match history record {best[1]} "
                  f"to {best[0]:.2e} relative (unturned lanes would differ by {e0:.2e}) "
                  f"{verdict}")
        if "tau_x" in lanes:
            tx, ty = to_grid(lanes["tau_x"], lanes["tau_y"], a)
            su_lane = 0.5 * (tx[:-1, :] + tx[1:, :])            # interior u faces 1..nx-1
            sv_lane = 0.5 * (ty[:, :-1] + ty[:, 1:])            # interior v faces 1..ny-1
            best = None
            for rec in range(hist["nrec"]):
                su = hist_rec(hist, "sustr", rec)
                sv = hist_rec(hist, "svstr", rec)
                if su is None or sv is None:
                    print("  the history has no sustr/svstr")
                    return
                mu = hist_rec(hist, "mask_u", rec)
                mv = hist_rec(hist, "mask_v", rec)
                # sustr is (eta_rho, xi_u): the face between cells i-1 and i is xi_u index
                # i, and cell row j is eta_rho index j+1; svstr is (eta_v, xi_rho) likewise
                su_h = su[1:ny + 1, 1:nx].T
                sv_h = sv[1:ny, 1:nx + 1].T
                wu = (mu[1:ny + 1, 1:nx].T > 0.5) if mu is not None else np.isfinite(su_h)
                wv = (mv[1:ny, 1:nx + 1].T > 0.5) if mv is not None else np.isfinite(sv_h)
                # REMORA applies sustr = c * (face mean of the turned stress) on wet faces,
                # with c = -1/rho0; fit c over both components
                xl = np.concatenate([su_lane[wu], sv_lane[wv]])
                yh = np.concatenate([su_h[wu], sv_h[wv]])
                ok = np.isfinite(xl) & np.isfinite(yh)
                if not ok.any() or np.dot(xl[ok], xl[ok]) == 0:
                    continue
                c = np.dot(xl[ok], yh[ok]) / np.dot(xl[ok], xl[ok])
                e = rel_err(c * xl, yh)
                if not np.isfinite(e):
                    continue
                if best is None or e < best[0]:
                    best = (e, rec, c)
            if best is None:
                print("  no usable stress in the history")
                continue
            print(f"  {os.path.basename(p)} (t={t:g}): stress matches history record {best[1]} "
                  f"to {best[0]:.2e} relative, scale {best[2]:.6e} "
                  f"{'PASS' if best[0] < 1e-10 else 'CHECK'}")


def check_erf_vs_wrf(run, prefix, wrf):
    print("\n2. ERF's earth-relative 10 m wind against its grid wind turned with WRF's alpha")
    files = plotfiles(run, prefix)
    if not files:
        print(f"  no {prefix}* plotfiles (erf.plot2d_*_1)")
        return [], None
    _, _, alpha = wrf
    out = []
    t_first = None
    for p in files:
        f, t = read_plotfile(p)
        t_first = t if t_first is None else min(t_first, t)
        if not all(k in f for k in ("u_10m", "v_10m", "u_east_10m", "v_north_10m")):
            print(f"  {os.path.basename(p)}: needs u_10m v_10m u_east_10m v_north_10m")
            continue
        if f["u_10m"].shape != alpha.shape:
            sys.exit(f"ERF's domain {f['u_10m'].shape} is not WRF's mass grid {alpha.shape}")
        bad = (f["u_10m"] <= -998) | (f["u_east_10m"] <= -998)
        e, n = to_earth(f["u_10m"], f["v_10m"], alpha)
        for x in (e, n, f["u_east_10m"], f["v_north_10m"]):
            x[bad] = np.nan
        if not np.any(np.hypot(e, n)[np.isfinite(e)] > 0):
            print(f"  {os.path.basename(p)} (t={t:g}): no wind yet, skipped")
            continue
        err = max(rel_err(f["u_east_10m"], e), rel_err(f["v_north_10m"], n))
        if not np.isfinite(err):
            print(f"  {os.path.basename(p)} (t={t:g}): no wind to compare, skipped")
            continue
        dirdiff = wrap_deg(np.degrees(np.arctan2(f["v_north_10m"], f["u_east_10m"]) -
                                      np.arctan2(n, e)))
        print(f"  {os.path.basename(p)} (t={t:g}): differ by {err:.2e} relative; direction "
              f"difference median {np.nanmedian(dirdiff):+.3f}, max |.| "
              f"{np.nanmax(np.abs(dirdiff)):.3f} deg (ERF's angle is from lat/lon, WRF's from "
              f"its projection: a small difference is expected, a sign error gives ~2 alpha, "
              f"up to {2 * np.degrees(np.abs(alpha)).max():.1f} deg)")
        out.append((t, f))
    return out, t_first


def nearest_erf(wrf, lon, lat):
    wlat, wlon, _ = wrf
    tree = cKDTree(unit_vectors(wlon.ravel(), wlat.ravel()))
    _, idx = tree.query(unit_vectors(lon, lat))
    return np.unravel_index(idx, wlat.shape)


def check_end_to_end(hist, erf2d, t0_erf, wrf, min_speed=2.0):
    print("\n3. End to end: wind REMORA applied, turned back to east/north, against ERF's")
    if not erf2d:
        print("  needs the ERF 2D plotfiles")
        return
    if hist["angle"] is None or hist["lon_rho"] is None:
        print("  needs angle, lon_rho and lat_rho in the history")
        return
    if hist_rec(hist, "Uwind", 0) is None:
        print("  needs Uwind/Vwind in the history (state mode, remora.output_forcing = true)")
        return
    _, _, alpha = wrf
    ang = hist["angle"][1:-1, 1:-1]
    lon = hist["lon_rho"][1:-1, 1:-1]
    lat = hist["lat_rho"][1:-1, 1:-1]
    wet = (hist["mask_rho"][1:-1, 1:-1] > 0.5) if hist["mask_rho"] is not None \
        else np.ones_like(ang, bool)
    ii, jj = nearest_erf(wrf, lon[wet], lat[wet])
    delta = wrap_deg(np.degrees(ang[wet] - alpha[ii, jj]))
    # Each ERF 2D plotfile against the history record nearest in time, both counted from
    # their first output: REMORA's clock may be offset (driver.ocean_time_offset)
    hist_rel = hist["time"] - hist["time"][0]
    for t, f in erf2d:
        rec = int(np.argmin(np.abs(hist_rel - (t - t0_erf)))) if hist["nrec"] > 1 else 0
        U = hist_rec(hist, "Uwind", rec)[1:-1, 1:-1][wet]
        V = hist_rec(hist, "Vwind", rec)[1:-1, 1:-1][wet]
        E, N = to_earth(U, V, ang[wet])
        e, n = f["u_east_10m"][ii, jj], f["v_north_10m"][ii, jj]
        keep = (np.hypot(E, N) > min_speed) & (np.hypot(e, n) > min_speed) & (e > -998)
        d = wrap_deg(np.degrees(np.arctan2(N, E) - np.arctan2(n, e)))
        d[~keep] = np.nan
        print(f"  ERF t={t:g} against history record {rec} (t={hist['time'][rec]:g}); "
              f"winds above {min_speed} m/s")
        slope_vs_delta(d, delta, "wind direction difference")


def check_current(run, hist, wrf, min_speed=0.01):
    o2a = plotfiles(run, "exchange_o2a")
    if not o2a:
        return
    lanes, t = read_plotfile(o2a[-1])
    if "Uoce" not in lanes:
        return
    print("\n4. Surface current: the exchanged Uoce/Voce against REMORA's top-level current")
    if hist["angle"] is None or hist["lon_rho"] is None:
        print("  needs angle, lon_rho and lat_rho in the history")
        return
    _, _, alpha = wrf
    ang = hist["angle"][1:-1, 1:-1]
    lon = hist["lon_rho"][1:-1, 1:-1]
    lat = hist["lat_rho"][1:-1, 1:-1]
    wet = (hist["mask_rho"][1:-1, 1:-1] > 0.5) if hist["mask_rho"] is not None \
        else np.ones_like(ang, bool)
    ii, jj = nearest_erf(wrf, lon[wet], lat[wet])
    delta = wrap_deg(np.degrees(ang[wet] - alpha[ii, jj]))
    best = None
    for p in o2a:
        lanes, t = read_plotfile(p)
        e, n = lanes["Uoce"][ii, jj], lanes["Voce"][ii, jj]
        for rec in range(hist["nrec"]):
            u = hist_rec(hist, "u", rec)
            v = hist_rec(hist, "v", rec)
            if u is None:
                print("  needs u and v in the history")
                return
            ut, vt = u[-1], v[-1]                               # top level
            # rho cell (i, j): u faces xi_u i, i+1 at eta_rho j+1; v faces eta_v j, j+1
            ur = 0.5 * (ut[1:-1, :-1] + ut[1:-1, 1:])
            vr = 0.5 * (vt[:-1, 1:-1] + vt[1:, 1:-1])
            E, N = to_earth(ur[wet], vr[wet], ang[wet])
            keep = (np.hypot(E, N) > min_speed) & (np.hypot(e, n) > min_speed)
            d = wrap_deg(np.degrees(np.arctan2(N, E) - np.arctan2(n, e)))
            d[~keep] = np.nan
            score = np.nanmedian(np.abs(d)) if keep.any() else np.inf
            if best is None or score < best[0]:
                best = (score, p, rec, d)
    if best is None or not np.isfinite(best[0]):
        print(f"  no current above {min_speed} m/s")
        return
    print(f"  {os.path.basename(best[1])} against history record {best[2]}; "
          f"currents above {min_speed} m/s")
    slope_vs_delta(best[3], delta, "current direction difference")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", required=True)
    ap.add_argument("--wrfinput")
    ap.add_argument("--history")
    ap.add_argument("--erf2d", default="occams_rotcheck_erf_2d")
    ap.add_argument("--rho0", type=float, default=1025.0)
    ap.add_argument("--min-wind", type=float, default=2.0,
                    help="winds below this speed [m/s] are left out of check 3")
    ap.add_argument("--min-current", type=float, default=0.01,
                    help="currents below this speed [m/s] are left out of check 4")
    args = ap.parse_args()

    hist_path = args.history
    if hist_path is None:
        cands = glob.glob(os.path.join(args.run, "*_his_d01.nc"))
        if len(cands) != 1:
            sys.exit(f"give --history: found {cands}")
        hist_path = cands[0]
    hist = load_history(hist_path)
    print(f"history {hist_path}: {hist['nrec']} records; expected stress scale "
          f"-1/rho0 = {-1.0 / args.rho0:.6e}")

    check_remora_exact(args.run, hist)
    if args.wrfinput is None:
        print("\nchecks 2-4 need --wrfinput")
        return
    wrf = load_wrf(args.wrfinput)
    erf2d, t0_erf = check_erf_vs_wrf(args.run, args.erf2d, wrf)
    check_end_to_end(hist, erf2d, t0_erf, wrf, args.min_wind)
    check_current(args.run, hist, wrf, args.min_current)


if __name__ == "__main__":
    main()
