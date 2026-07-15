import xarray as xr

def weekly_mean_w_est_profile(ds: xr.Dataset,
                               center_lat: float,
                               center_lon: float,
                               box_size: float) -> xr.Dataset:
    """
    Calculates weekly mean vertical profiles of w_est1 within a 1x1 degree
    box, returning a dataset with dimensions (week, zl).

    Args:
        ds (xr.Dataset): MOM6 h.z dataset containing w_est1. Must have
            dimensions (time, zl, yh, xh).
        center_lat (float): Center latitude of box in degrees N. 
        center_lon (float): Center longitude in degrees E (0-360).
        box_size (float): Full width/height of box in degrees.

    Returns:
        xr.Dataset: Dataset with dimensions (week, zl) containing:
            - w_est1_mean: weekly mean w_est1 profile
            - w_est1_std: weekly standard deviation profile
            - week_start: datetime of the start of each week
            - n_timesteps: number of 3-hourly timesteps in each week
    """
    half = box_size / 2.0

    # Spatial subset
    w = ds['w_est1'].sel(
        yh=slice(center_lat - half, center_lat + half),
        xh=slice(center_lon - half, center_lon + half)
    )

    n_lat = w.sizes['yh']
    n_lon = w.sizes['xh']
    print(f"Box: {n_lat} x {n_lon} grid cells")
    print(f"Lat: {float(w.yh.min()):.3f} to {float(w.yh.max()):.3f}")
    print(f"Lon: {float(w.xh.min()):.3f} to {float(w.xh.max()):.3f}")

    if n_lat == 0 or n_lon == 0:
        raise ValueError(
            f"No grid cells in box. xh range is "
            f"{float(ds.xh.min()):.1f} to {float(ds.xh.max()):.1f}. "
            f"Remember MOM6 uses 0-360 lon, so 140W = 220E."
        )

    # Mask below-seafloor zeros before averaging
    w_masked = w.where(w != 0.0)

    # Horizontal mean first -> (time, zl)
    w_horiz = w_masked.mean(dim=['yh', 'xh'])

    # Resample to weekly means
    w_weekly_mean = w_horiz.resample(time='1W').mean(dim='time')
    w_weekly_std  = w_horiz.resample(time='1W').std(dim='time')
    w_weekly_count = w_horiz.resample(time='1W').count(dim='time')

    # Week start times
    week_starts = w_weekly_mean.time.values

    # Build output dataset
    out_ds = xr.Dataset(
        {
            'w_est1_mean': (['week', 'zl'], w_weekly_mean.values),
            'w_est1_std':  (['week', 'zl'], w_weekly_std.values),
            'n_timesteps': (['week'], w_weekly_count.isel(zl=0).values),
            'week_start':  (['week'], week_starts),
        },
        coords={
            'week': np.arange(len(week_starts)),
            'zl':   ds['zl'].values,
        },
        attrs={
            'center_lat': center_lat,
            'center_lon': center_lon,
            'box_size':   box_size,
            'description': f'Weekly mean w_est1 profiles in {box_size}x{box_size} '
                           f'degree box centered at {center_lat}N, {center_lon}E',
        }
    )

    return out_ds