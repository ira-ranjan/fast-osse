import xarray as xr
from pathlib import Path
import sys
import shutil
import re
import pydartdiags.obs_sequence.obs_sequence as obsq
import datetime as dt


def _convert_to_dart_time(time: dt.datetime):
    """Converts datetime object to a list of seconds, days after 1601"""
    dart_time = time - dt.datetime(1601, 1, 1)
    return [dart_time.seconds, dart_time.days]

def split_single_hz_file(input_file: str, output_dir: str, static_file: str,
                         ocean_geom_file: str, pmo_exec: str, input_nml: str, obs_to_ncdf: str):
    """
    Splits a single daily MOM6 h.z file containing 8 x 3-hourly records into
    individual files, each in its own subdirectory.

    Args:
        input_file (str): Path to a single daily h.z nc file.
        output_dir (str): Path to root output directory. Each 3-hourly
            snapshot is written to its own subdirectory within output_dir.
    """
    input_path = Path(input_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)  # makes a directory to store output subdirectories

    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}")
        sys.exit(1)

    ds = xr.open_dataset(str(input_path))

    n_times = ds.sizes["time"]
    if n_times != 8:
        print(f"WARNING: expected 8 time steps, got {n_times}")

    hours = [f"{(i+1)*3:02d}" for i in range(n_times)]

    for i in range(n_times):
        out_name = "mom6.r.nc"
        sub_dir = output_path / f"{input_path.stem}-{hours[i]}"
        sub_dir.mkdir(parents=True, exist_ok=True)
        out_path = sub_dir / out_name

        ds_slice = ds.isel(time=i).expand_dims("time")
        ds_slice.to_netcdf(str(out_path))
        print(f"  wrote: {sub_dir.name}/{out_name}")

        # Copy static files and PMO executable into subdirectory
        shutil.copy(static_file, sub_dir/"mom6.static.nc")
        shutil.copy(ocean_geom_file, sub_dir/"ocean_geometry.nc")
        shutil.copy(pmo_exec, sub_dir/"perfect_model_obs")
        shutil.copy(obs_to_ncdf, sub_dir/"obs_seq_to_netcdf")
        dest_file = sub_dir / "input.nml"
        shutil.copy(input_nml, dest_file)
        raw_time = ds_slice.time.isel(time=0).values
        py_datetime = dt.datetime.fromisoformat(str(raw_time)[:19])
        (seconds_val, days_val) = _convert_to_dart_time(py_datetime)
        text = dest_file.read_text()
        text = re.sub(r'(init_time_days\s*=\s*)[-\d]+', f'\\g<1>{days_val+2}', text)
        text = re.sub(r'(init_time_seconds\s*=\s*)[-\d]+', f'\\g<1>{seconds_val}', text)
        dest_file.write_text(text)
        
        pmo_path = sub_dir / Path(pmo_exec).name
        pmo_path.chmod(0o755)
    ds.close()
    print(f"Done: {input_path.name}")


if __name__ == "__main__":
    if len(sys.argv) != 8:
        print("Usage: python split_one_hz_file.py <input_file> <output_dir>")
        sys.exit(1)

    split_single_hz_file(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7])