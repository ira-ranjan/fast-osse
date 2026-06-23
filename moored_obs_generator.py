# %%

# lat/lon format in dart ?
# removed type as input -> automatically adds obs for u_velocity and v_velocity and ssh
# are we generating obs_err_var ?

# documentation written using claude

# %%
import datetime as dt
import obs_to_obs_seq_in as obsin
import numpy as np


# %%
def interpolate_times(start: dt.datetime, end: dt.datetime, frequency: float):
    """
    Generate a list of evenly-spaced datetimes between two times.

    Produces timestamps from ``start`` to ``end`` (inclusive) at intervals
    of ``frequency`` minutes. If ``end`` is not exactly reachable at the
    given interval, the last timestamp will be the largest multiple of
    ``frequency`` that does not exceed ``end``.

    Args:
        start (datetime.datetime): The first timestamp in the sequence.
        end (datetime.datetime): The upper bound of the sequence (inclusive
            if exactly reachable).
        frequency (float): Sampling interval in minutes. Must be positive.

    Returns:
        list[datetime.datetime]: Ordered list of datetimes from ``start``
            to ``end``, spaced ``frequency`` minutes apart.

    Example:
        .. code-block:: python

            times = interpolate_times(
                start=dt.datetime(2023, 3, 2, 12, 0),
                end=dt.datetime(2023, 3, 2, 12, 30),
                frequency=10,
            )
            # Returns a list of datetimes at 12:00, 12:10, 12:20, 12:30
    """
    times = []
    step = dt.timedelta(minutes=frequency)
    current_time = start
    while current_time <= end:
        times.append(current_time)
        current_time += step
    return times

# %%
class MooredObs:
    """
    Initialize a moored buoy instrument at a fixed geographic location.

    Generates synthetic observation data over a vertical profile and time
    period, for converting into an ObsSequence file.

    Attributes:
        lat (float): Latitude of the moored instrument (degrees).
        lon (float): Longitude of the moored instrument (degrees).
        vert_start (float): Start of the vertical range, in units of
            ``self.vert_unit``.
        vert_end (float): End of the vertical range, in units of
            ``self.vert_unit``.
        vert_gap (float): The gap between two points of observation in depth,
            in units of ``self.vert_unit``.
        vert_unit (str): Unit of the vertical coordinate. Must be one of:
            ``'undefined'``, ``'surface (m)'``, ``'model level'``,
            ``'pressure (Pa)'``, ``'height (m)'``, ``'scale height'``.
        start_time (datetime.datetime): Start of the monitoring period.
        end_time (datetime.datetime): End of the monitoring period.
        obs_err_var (float): Observation error variance applied to all
            generated observations.
        frequency (int): Temporal sampling interval in minutes.
        metadata (list): Optional metadata attached to each
            observation. Defaults to an empty list.
        external_FO (list): Optional external forward-operator
            data. Defaults to an empty list.
    
    Raises:
            ValueError: If ``vert_unit`` is not a recognised vertical unit.

    Example:
        .. code-block:: python

            buoy = MooredBuoy(
                lat=0.0,
                lon=140.8,
                vert_unit='surface (m)',
                start_time=dt.datetime(2023, 3, 2, 12, 30),
                end_time=dt.datetime(2023, 6, 5, 15, 30),
            )
    """
    vert = {
                    -2: "undefined",
                    -1: "surface (m)",
                    1: "model level",
                    2: "pressure (Pa)",
                    3: "height (m)",
                    4: "scale height",
                }
    
    def __init__(self, lat: float, lon: float, vert_start: float, vert_end: float, vert_gap: float, vert_unit: str, start_time: dt.datetime, end_time: dt.datetime, obs_err_var: float, frequency: float, metadata = [], external_FO = []):
        if vert_unit not in self.vert.values():
            raise ValueError(
                f"Invalid vert_unit '{vert_unit}'. "
                f"Must be one of: {sorted(self.vert.values())}"
            )
        self.lat = lat
        self.lon = lon
        self.vert_unit = vert_unit
        self.start_time = start_time
        self.end_time = end_time
        self.metadata = self.data_generator(vert_start, vert_end, vert_gap, obs_err_var, frequency, metadata, external_FO)

    def data_generator(self, vert_start: float, vert_end: float, vert_gap: float, obs_err_var: float, frequency: float, metadata = [], external_FO = []) -> list:
        """
        Create a list with U, V velocity observations and sea surface height over a
        vertical profile and time series.

        Observations are generated at evenly-spaced
        vertical levels between ``vert_start`` and ``vert_end`` at ``vert_gap`` intervals, at each
        timestep produced by ``interpolate_times``.

        Args:
            vert_start (float): Start of the vertical range, in units of
                ``self.vert_unit``.
            vert_end (float): End of the vertical range, in units of
                ``self.vert_unit``.
            vert_gap (float): The gap between two points of observation in depth,
                in units of ``self.vert_unit``.
            obs_err_var (float): Observation error variance applied to all
                generated observations.
            frequency (int): Temporal sampling interval in minutes.
            metadata (list): Optional metadata attached to each
                observation. Defaults to an empty list.
            external_FO (list): Optional external forward-operator
                data. Defaults to an empty list.

        Returns:
            list:  A list of metadata for the new observations.
        """
        list_obs = []
        vert_list = np.arange(vert_start, vert_end + (vert_gap / 2), vert_gap)
        time_list = interpolate_times(self.start_time, self.end_time, frequency) #frequency in mins
        for time in time_list:
            for vert in vert_list:
                obsin.add_obs_to_list(list_obs, self.lon, self.lat, float(vert), self.vert_unit, 'U_VELOCITY', time, obs_err_var, metadata, external_FO)
                obsin.add_obs_to_list(list_obs, self.lon, self.lat, float(vert), self.vert_unit, 'V_VELOCITY', time, obs_err_var, metadata, external_FO)
                obsin.add_obs_to_list(list_obs, self.lon, self.lat, float(vert), self.vert_unit, 'SEA SURFACE HEIGHT', time, obs_err_var, metadata, external_FO)
        return list_obs

# %%

# %%



