# Claude made most of this
# TO-DO: figure out what it did

import pydartdiags.obs_sequence.obs_sequence as obsq
import xarray as xr
import sys
import os
import dask
import numpy as np
import pandas as pd
from pathlib import Path

def join_obs_seq_outputs(output_dir: str) -> obsq.ObsSequence:
    """
    Reads all *_obs_seq.out files from a directory and joins them into
    a single ObsSequence using obsq.ObsSequence.join().

    Args:
        output_dir (str): Directory containing obs_seq_*.out files.

    Returns:
        obsq.ObsSequence: Single joined ObsSequence containing all
            observations from all files, sorted by time.
    """
    output_path = Path(output_dir)
    out_files = sorted(output_path.glob("*_obs_seq.out"))

    if not out_files:
        raise FileNotFoundError(f"No *_obs_seq.out files found in {output_dir}")

    print(f"Found {len(out_files)} obs_seq.out files")

    obs_seqs = []
    for f in out_files:
        obs_seqs.append(obsq.ObsSequence(str(f)))
        
    joined = obsq.ObsSequence.join(obs_seqs)
    print(f"Total obs in joined sequence: {len(joined.df)}")

    return joined

def _infer_cadence(times):
    """
    Infer the nominal sampling cadence from the data itself, as the most
    common gap between consecutive unique timestamps. This avoids hardcoding
    a cadence that might not match your actual obs interval.
    """
    unique_sorted = np.sort(pd.unique(times))
    if len(unique_sorted) < 2:
        return pd.Timedelta(0)
    diffs = np.diff(unique_sorted)
    vals, counts = np.unique(diffs, return_counts=True)
    return pd.Timedelta(vals[np.argmax(counts)])

def reshape_obs_to_uv_samples(df, depth_round=None, time_tolerance=None):
    """
    Convert a flat obs DataFrame (as returned by load_obs_files_to_df) into
    the gridded (time, glider, obs_depth) structure compute_w_planefit
    requires.
 
    Parameters
    ----------
    df : pd.DataFrame
        Concatenated obs rows with 'type', 'observation', 'latitude',
        'longitude', 'vertical', 'time' columns. 'vertical' assumed
        POSITIVE-down and will be negated.
    depth_round : int or None
        Decimal places to round 'vertical' to, if depths carry float noise.
    time_tolerance : pd.Timedelta or None
        Snap timestamps within this tolerance of the inferred nominal
        cadence's grid to a shared value, so gliders sampling at "the same"
        nominal time but with slightly different clock offsets get grouped
        into one (time, glider, obs_depth) cell instead of each getting
        their own near-duplicate time coordinate (which is what was
        blowing up the pivot). If None, tolerance defaults to half the
        inferred cadence.
    """
    df = df.copy()
 
    # --- 1. snap timestamps to a shared nominal grid ---
    cadence = _infer_cadence(df['time'])
    if cadence <= pd.Timedelta(0):
        print("WARNING: could not infer a nonzero cadence from timestamps; "
              "skipping time snapping. Check df['time'] manually.")
    else:
        tol = time_tolerance if time_tolerance is not None else cadence / 2
        t0 = df['time'].min()
        offset = (df['time'] - t0)
        n_steps = (offset / cadence).round()
        snapped = t0 + n_steps * cadence
        max_shift = (df['time'] - snapped).abs().max()
        if max_shift > tol:
            print(f"WARNING: snapping timestamps to inferred cadence "
                  f"({cadence}) required shifts up to {max_shift}, which "
                  f"exceeds tolerance ({tol}). Cadence may be mis-detected "
                  f"— inspect df['time'].diff() manually before trusting "
                  f"this pivot.")
        df['time'] = snapped
        print(f"Inferred cadence: {cadence}. Snapped timestamps to this grid "
              f"(max shift applied: {max_shift}).")
 
    # --- 2. assign glider id from unique (lat, lon) pairs ---
    pos_key = list(zip(df['latitude'].round(6), df['longitude'].round(6)))
    unique_pos = sorted(set(pos_key))
    pos_to_glider = {p: i for i, p in enumerate(unique_pos)}
    df['glider'] = [pos_to_glider[p] for p in pos_key]
    print(f"Found {len(unique_pos)} distinct glider positions.")
 
    # --- 3. flip depth sign: positive-down -> negative-down ---
    depth = -df['vertical'].astype(float)
    if depth_round is not None:
        depth = depth.round(depth_round)
    df['obs_depth'] = depth
 
    # --- 4. split U and V by type ---
    is_u = df['type'].str.contains('U_CURRENT')
    is_v = df['type'].str.contains('V_CURRENT')
    if not is_u.any() or not is_v.any():
        raise ValueError(
            f"Expected types containing 'U_CURRENT' / 'V_CURRENT', "
            f"found: {df['type'].unique()}"
        )
    df_u = df.loc[is_u, ['time', 'glider', 'obs_depth', 'observation', 'latitude', 'longitude']]
    df_v = df.loc[is_v, ['time', 'glider', 'obs_depth', 'observation', 'latitude', 'longitude']]
 
    # --- 5. check for duplicate (time, glider, obs_depth) after snapping ---
    for name, d in [('U', df_u), ('V', df_v)]:
        dup = d.duplicated(subset=['time', 'glider', 'obs_depth'], keep=False)
        if dup.any():
            print(f"WARNING: {dup.sum()} duplicate (time, glider, obs_depth) rows "
                  f"in {name} after time snapping — pivot will keep only the "
                  f"last of each. If this count is large, your inferred "
                  f"cadence/tolerance may be too coarse.")
 
    # --- 6. pivot each to (time, glider, obs_depth) ---
    u_da = (df_u.set_index(['time', 'glider', 'obs_depth'])['observation']
                .to_xarray().rename('U'))
    v_da = (df_v.set_index(['time', 'glider', 'obs_depth'])['observation']
                .to_xarray().rename('V'))
 
    # --- 7. align U and V ---
    u_da, v_da = xr.align(u_da, v_da, join='outer')
    n_nan_u = int(u_da.isnull().sum())
    n_nan_v = int(v_da.isnull().sum())
    if n_nan_u or n_nan_v:
        print(f"WARNING: after aligning U and V, found {n_nan_u} NaN in U and "
              f"{n_nan_v} NaN in V. compute_w_planefit's plane fit does not "
              f"handle NaNs — drop or fill before running it.")
 
    # --- 8. one lat/lon per glider (mean position) ---
    glider_lat = df.groupby('glider')['latitude'].mean()
    glider_lon = df.groupby('glider')['longitude'].mean()
    pos_std = df.groupby('glider')[['latitude', 'longitude']].std().max().max()
    if pos_std > 1e-6:
        print(f"NOTE: glider positions vary within a glider (max std "
              f"{pos_std:.4g} deg) — using the mean position collapses that "
              f"drift into a single point for the plane fit.")
 
    out = xr.Dataset({'U': u_da, 'V': v_da})
    out = out.assign_coords(
        lat=('glider', glider_lat.reindex(out.glider.values).values),
        lon=('glider', glider_lon.reindex(out.glider.values).values),
    )
    out = out.sortby('obs_depth', ascending=False)
    
    # --- 9. confirm uniform depth spacing across the full range ---
    depths = np.sort(out.obs_depth.values)
    dz = np.diff(depths)
    if not np.allclose(dz, dz[0], rtol=1e-4):
        print(f"WARNING: obs_depth spacing is not uniform across the full range "
              f"(min dz={dz.min()}, max dz={dz.max()}).")
 
    return out

def compute_w_difference(ds_true, ds_est, time_tolerance_days=2):
    """
    Aligns est_w with true_w and subtracts them. Both are already weekly
    datasets with a 'time' dimension — this just fixes the depth sign
    convention and matches timestamps between them (nearest-match, in case
    the two pipelines label a given week's timestamp slightly differently,
    e.g. week-start vs week-midpoint).
 
    Parameters
    ----------
    ds_true : xr.Dataset
        Contains 'w_true_mean' (or similar) on dims (time, depth), one
        weekly timestamp per row.
    ds_est : xr.Dataset
        Contains 'w_est' on dims (time, depth), one weekly timestamp per row.
    time_tolerance_days : float
        Max allowed gap between a ds_est timestamp and its matched ds_true
        timestamp. If any match exceeds this, it's flagged rather than
        silently paired — a large gap likely means the two datasets'
        weeks aren't actually the same weeks.
 
    Returns
    -------
    xr.DataArray
        (time, depth) — True w minus estimated w, on ds_true's time coordinate.
    """
    w_est_da = ds_est['w_est']
 
    # depth back to positive, to match ds_true's convention
    w_est_da = w_est_da.assign_coords(depth=np.abs(w_est_da.depth))
 
    if w_est_da.sizes['time'] != ds_true.sizes['time']:
        print(f"WARNING: ds_est has {w_est_da.sizes['time']} weekly "
              f"timestamps but ds_true has {ds_true.sizes['time']} — "
              f"expected these to match if both are already weekly. "
              f"Proceeding with nearest-time matching, but check why "
              f"the counts differ (e.g. incomplete obs coverage for "
              f"some weeks).")
 
    true_times = pd.to_datetime(ds_true.time.values)
    est_times = pd.to_datetime(w_est_da.time.values)
 
    # match each true_w timestamp to its nearest est_w timestamp
    true_df = pd.DataFrame({'true_time': true_times}).sort_values('true_time')
    est_df = pd.DataFrame({'est_time': est_times}).sort_values('est_time')
    matched = pd.merge_asof(
        true_df, est_df, left_on='true_time', right_on='est_time',
        direction='nearest',
    )
    matched['gap_days'] = (matched['true_time'] - matched['est_time']).abs().dt.total_seconds() / 86400
    too_far = matched['gap_days'] > time_tolerance_days
    if too_far.any():
        print(f"WARNING: {too_far.sum()} of {len(matched)} true_w weeks have "
              f"no est_w timestamp within {time_tolerance_days} days "
              f"(closest gap: {matched.loc[too_far, 'gap_days'].max():.1f} "
              f"days). Those weeks will be NaN in the result — check "
              f"est_w and true_w actually cover the same weeks.")
 
    # reindex est_w onto matched true_w timestamps (NaN where no good match)
    est_relabeled = w_est_da.sel(time=matched.loc[~too_far, 'est_time'].values)
    est_relabeled = est_relabeled.assign_coords(
        time=matched.loc[~too_far, 'true_time'].values
    )
    est_aligned = est_relabeled.reindex(time=true_times)
 
    # confirm depth grids match before subtracting
    if not np.allclose(np.sort(est_aligned.depth.values), np.sort(ds_true.depth.values), rtol=1e-6):
        print("WARNING: ds_true and est_w depth grids do not match exactly "
              "— check start_depth/end_depth/depth_step were identical "
              "between compute_true_w_profile and the glider obs generation "
              "(min_depth/max_depth/step in MooredObs). xarray will only "
              "keep overlapping depth values when subtracting.")
 
    var_true = 'w_true_mean' if 'w_true_mean' in ds_true else list(ds_true.data_vars)[0]
    w_diff = ds_true[var_true] - est_aligned
 
    w_diff.name = 'w_difference'
    w_diff.attrs['description'] = 'True w minus Estimated w profile differences'
    return w_diff