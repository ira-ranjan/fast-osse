import numpy as np
import obs_to_obs_seq_in as obsin
import moored_obs_generator as obsgen
import datetime as dt
import make_uv_samples as makeuv
from pathlib import Path
import sys
import run_pmo_parallel as pmo_run

module_dir = Path("/glade/work/iranjan/tpose24-osse/")
sys.path.append(str(module_dir))

import osse_tools as ost


def opt_loc(loc_list, true_w):
    obs_seq = obsin.create_obs_seq_in()
    start_year, start_month, start_date, start_time = 2015, 9, 4, 0
    end_year, end_month, end_date, end_time = 2015, 9, 25, 2

    for lat, lon in loc_list:
        obsgen.MooredObs(
            obs_seq, lon, lat, 8, 80, 2, "height (m)",
            dt.datetime(start_year, start_month, start_date, start_time),
            dt.datetime(end_year, end_month, end_date, end_time),
            0.001, dt.timedelta(days=7),
        )
    start_year, start_month, start_date, start_time = 2015, 10, 4, 0
    end_year, end_month, end_date, end_time = 2015, 10, 25, 2
    for lat, lon in loc_list:
        obsgen.MooredObs(
            obs_seq, lon, lat, 8, 80, 2, "height (m)",
            dt.datetime(start_year, start_month, start_date, start_time),
            dt.datetime(end_year, end_month, end_date, end_time),
            0.001, dt.timedelta(days=7),
        )
    out_path = "/glade/derecho/scratch/iranjan/weekly_eep_osse"
    obsin.split_obs_seq_by_date(
        obs_seq, out_path, "EEP_MITgcm185Lvgrid_Whitt2026hgrid.mom6.h.z."
    )
    PMO_SCRIPT = "/glade/work/iranjan/fast-osse/run_pmo_qint.sh"
    pmo_run.run_pmo_parallel(out_path, PMO_SCRIPT, max_concurrent=128)
    joined_obs_seq = makeuv.join_obs_seq_outputs(out_path + "/outputs")
    uv_samples = makeuv.reshape_obs_to_uv_samples(joined_obs_seq.df)

    est_w = ost.compute_w_planefit(uv_samples, extrapolate_to_surface=False)
    #w_est = est_w['w_est'].mean('time').values

    return np.linalg.norm(makeuv.compute_w_difference(true_w, est_w))