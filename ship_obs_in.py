# %%
import datetime as dt
import obs_to_obs_seq_in as obsin
import numpy as np

# %%
def interpolated_list(lat0, lon0, t0, lat1, lon1, t1, number):
    ts0 = t0.timestamp()
    ts1 = t1.timestamp()
    coords = np.linspace([lat0, lon0], [lat1, lon1], number)
    times = np.linspace([ts0], [ts1], number)
    points =[]
    for ii in range(len(times)):
        points.append([float(coords[ii][0]), float(coords[ii][1]), dt.datetime.fromtimestamp(times[ii][0])])
    return points

# %%
def ship_data(list_ship, lat0, lon0, t0, lat1, lon1, t1, number, vert):
    vert_unit = 'height (m)'
    type = 'RADIOSONDE TEMPERATURE'
    metadata = []
    external_FO = []
    obs_err_var = 0.01
    locations = interpolated_list(lat0, lon0, t0, lat1, lon1, t1, number)
    for coords in locations:
            obsin.add_obs_to_list(list_ship, coords[0], coords[1], vert, vert_unit, type, coords[2], obs_err_var, metadata, external_FO)
    return list_ship

# %%



