import numpy as np
import obs_to_obs_seq_in as obsin
import moored_obs_generator as obsgen
import datetime as dt
import make_uv_samples as makeuv
import xarray as xr
import sys
import run_pmo_parallel as pmo_run
from pathlib import Path
module_dir = Path("/glade/work/iranjan/tpose24-osse/")
sys.path.append(str(module_dir))
import osse_tools as ost

 
def opt_loc(loc_list, true_w):
    obs_seq = obsin.create_obs_seq_in()
    start_year, start_month, start_date, start_time = 2015, 1, 2, 12
    end_year, end_month, end_date, end_time = 2015, 6, 24, 13
 
    for lat, lon in loc_list:
        obsgen.MooredObs(
            obs_seq, round(lon, 6), round(lat, 6), 8, 80, 2, "height (m)",
            dt.datetime(start_year, start_month, start_date, start_time),
            dt.datetime(end_year, end_month, end_date, end_time),
            0.001, dt.timedelta(days=7),
        )
 
    out_path = "/glade/derecho/scratch/iranjan/weekly_eep_osse"
    obsin.split_obs_seq_by_date(
        obs_seq, out_path, "EEP_MITgcm185Lvgrid_Whitt2026hgrid.mom6.h.z."
    )
 
    PMO_SCRIPT = "/glade/work/iranjan/fast-osse/run_pmo_qint.sh"
    pmo_run.run_pmo_parallel(out_path, PMO_SCRIPT, max_concurrent=25)
 
    joined_obs_seq = makeuv.join_obs_seq_outputs(out_path + "/outputs")
    uv_samples = makeuv.reshape_obs_to_uv_samples(joined_obs_seq.df)
    est_w = ost.compute_w_planefit(uv_samples, extrapolate_to_surface=False)
 
    w_diff = est_w['w_est'] - true_w['true_w_mean']
    diff_vals = w_diff.values
 
    # checks
    expected_size = true_w['true_w_mean'].size
    if w_diff.size < expected_size:
        print(f"WARNING: w_diff has {w_diff.size} points but true_w has "
              f"{expected_size} — xarray's automatic alignment silently "
              f"dropped non-matching time/depth values. Check "
              f"est_w['w_est'] and true_w's coordinates actually agree "
              f"exactly, not just conceptually.")
 
    n_valid = np.sum(~np.isnan(diff_vals))
    if n_valid < diff_vals.size:
        print(f"WARNING: {diff_vals.size - n_valid} of {diff_vals.size} diff "
              f"points are NaN — treating this configuration as a failure "
              f"(any missing coverage invalidates the whole score) and "
              f"returning a large penalty.")
        return 1e10
 
    norm_error = np.linalg.norm(diff_vals)
    return norm_error


def opt_loc1(loc_list, true_w):
    obs_seq = obsin.create_obs_seq_in()
    start_year, start_month, start_date, start_time = 2015, 1, 2, 12
    end_year, end_month, end_date, end_time = 2015, 6, 24, 13

    for lat, lon in loc_list:
        obsgen.MooredObs(
            obs_seq, round(lon, 6), round(lat, 6), 8, 80, 2, "height (m)",
            dt.datetime(start_year, start_month, start_date, start_time),
            dt.datetime(end_year, end_month, end_date, end_time),
            0.001, dt.timedelta(days=7),
        )
    out_path = "/glade/derecho/scratch/iranjan/weekly_eep_osse"
    obsin.split_obs_seq_by_date(
        obs_seq, out_path, "EEP_MITgcm185Lvgrid_Whitt2026hgrid.mom6.h.z."
    )
    PMO_SCRIPT = "/glade/work/iranjan/fast-osse/run_pmo_qint.sh"
    pmo_run.run_pmo_parallel(out_path, PMO_SCRIPT, max_concurrent=28)
    joined_obs_seq = makeuv.join_obs_seq_outputs(out_path + "/outputs")
    uv_samples = makeuv.reshape_obs_to_uv_samples(joined_obs_seq.df)

    est_w = ost.compute_w_planefit(uv_samples, extrapolate_to_surface=False)
    w_diff = xr.Dataset({'w_diff': est_w['w_est'] - true_w['true_w_mean']})
    return np.linalg.norm(w_diff['w_diff'].values)