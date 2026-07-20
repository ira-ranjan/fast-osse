# Claude made most of this
# TO-DO: figure out what it did

import pydartdiags.obs_sequence.obs_sequence as obsq
import xarray as xr
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
 
 
def reshape_obs_to_uv_samples(df, depth_round=None):
    """
    Convert a flat obs DataFrame (as returned by join_obs_seq_outputs().df)
    into the gridded (time, glider, obs_depth) structure compute_w_planefit
    requires.
 
    Parameters
    ----------
    df : pd.DataFrame
        Concatenated obs rows with 'type', 'observation', 'latitude',
        'longitude', 'vertical', 'time' columns. 'vertical' assumed
        POSITIVE-down and will be negated. 'time' is used as-is — no
        cadence inference or snapping, since obs generation now produces
        exact, deterministic timestamps with no jitter to clean up.
    depth_round : int or None
        Decimal places to round 'vertical' to, if depths carry float noise.
    """
    df = df.copy()
    # each unique lat/lon pair becomes a glider
    pos_key = list(zip(df['latitude'].round(6), df['longitude'].round(6)))
    unique_pos = sorted(set(pos_key))
    pos_to_glider = {p: i for i, p in enumerate(unique_pos)}
    df['glider'] = [pos_to_glider[p] for p in pos_key]
    print(f"Found {len(unique_pos)} distinct glider positions.")
 
    # changes depth to negative
    depth = -df['vertical'].astype(float)
    if depth_round is not None:
        depth = depth.round(depth_round)
    df['obs_depth'] = depth
 
    # split type u_velocity and v_velocity
    is_u = df['type'].str.contains('U_CURRENT')
    is_v = df['type'].str.contains('V_CURRENT')
    if not is_u.any() or not is_v.any():
        raise ValueError(
            f"Expected types containing 'U_CURRENT' / 'V_CURRENT', "
            f"found: {df['type'].unique()}"
        )
    df_u = df.loc[is_u, ['time', 'glider', 'obs_depth', 'observation', 'latitude', 'longitude']]
    df_v = df.loc[is_v, ['time', 'glider', 'obs_depth', 'observation', 'latitude', 'longitude']]
 
    # pivot each to (time, glider, obs_depth)
    u_da = (df_u.set_index(['time', 'glider', 'obs_depth'])['observation']
                .to_xarray().rename('U'))
    v_da = (df_v.set_index(['time', 'glider', 'obs_depth'])['observation']
                .to_xarray().rename('V'))
 
    # align
    u_da, v_da = xr.align(u_da, v_da, join='outer')
    n_nan_u = int(u_da.isnull().sum())
    n_nan_v = int(v_da.isnull().sum())
    if n_nan_u or n_nan_v:
        print(f"WARNING: after aligning U and V, found {n_nan_u} NaN in U and "
              f"{n_nan_v} NaN in V. compute_w_planefit's plane fit does not "
              f"handle NaNs — drop or fill before running it.")
 
    # one lat/lon per glider (mean position)
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
 
    # check depth spacing
    depths = np.sort(out.obs_depth.values)
    dz = np.diff(depths)
    if not np.allclose(dz, dz[0], rtol=1e-4):
        print(f"WARNING: obs_depth spacing is not uniform across the full range "
              f"(min dz={dz.min()}, max dz={dz.max()}).")
 
    return out