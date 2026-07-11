import xarray as xr
from pathlib import Path
import sys
import shutil


def split_single_hz_file(input_file: str, output_dir: str, static_file: str,
                         ocean_geom_file: str, pmo_exec: str):
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
        out_name = f"{input_path.stem}-{hours[i]}.nc"
        sub_dir = output_path / f"{input_path.stem}-{hours[i]}"
        sub_dir.mkdir(parents=True, exist_ok=True)
        out_path = sub_dir / out_name

        ds_slice = ds.isel(time=i).expand_dims("time")
        ds_slice.to_netcdf(str(out_path))
        print(f"  wrote: {sub_dir.name}/{out_name}")

        # Copy static files and PMO executable into subdirectory
        shutil.copy(static_file, sub_dir)
        shutil.copy(ocean_geom_file, sub_dir)
        shutil.copy(pmo_exec, sub_dir)
        pmo_path = sub_dir / Path(pmo_exec).name
        pmo_path.chmod(0o755)
    ds.close()
    print(f"Done: {input_path.name}")


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python split_one_hz_file.py <input_file> <output_dir>")
        sys.exit(1)

    split_single_hz_file(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])