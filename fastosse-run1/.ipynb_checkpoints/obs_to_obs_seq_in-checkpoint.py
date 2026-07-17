
# %%
import pydartdiags.obs_sequence.obs_sequence as obsq
import make_uv_samples as makeuv
import pandas as pd
import datetime as dt
from pathlib import Path
import subprocess
import shutil
import os

# %%
def create_obs_seq_in():
    """
    Creates and returns a new, empty ObsSequence object initialized with
    0 copies and an empty structured DataFrame (in the format of an obs_seq.in file), ready for ingesting observation
    metadata. 
 
    Initializes the following attributes on the ObsSequence object:
        - loc_mod (str): Location module set to 'loc3d' (3D location format).
        - copie_names (list): Names of all copy fields (empty at creation).
        - qc_copie_names (list): Names of QC copy fields (empty at creation).
        - non_qc_copie_names (list): Names of non-QC copy fields (empty at creation).
        - n_copies (int): Total number of copy fields, initialized to 0.
        - n_non_qc (int): Number of non-QC copies, initialized to 0.
        - n_qc (int): Number of QC copies, initialized to 0.
        - df (pd.DataFrame): Empty DataFrame with columns from _column_headers(),
          reordered so 'obs_num' and 'linked_list' are the first two columns
          (as required by ObsSequence.write_obs_seq()).

    Column reordering:
        'obs_num' is moved to position 0 and 'linked_list' to position 1 to
        satisfy the column order expected by ObsSequence.write_obs_seq() in pyDARTdiags.

    Returns:
        obsq.ObsSequence: A blank ObsSequence instance with a zero-observation
        header and an empty, correctly ordered DataFrame, in the format of an obs_seq.in file.
    """
    obs_seq = obsq.ObsSequence(None)
    obs_seq.loc_mod = 'loc3d'
    obs_seq.copie_names = []
    obs_seq.qc_copie_names = []
    obs_seq.non_qc_copie_names = []
    obs_seq.n_copies = 0
    obs_seq.n_non_qc = 0
    obs_seq.n_qc = 0
    obs_seq.df = pd.DataFrame(columns=obs_seq._column_headers())
    obs_seq.create_header(0)
    #moves columns to fulfill ObsSeq.write_obs_seq() requirements
    column_to_move = obs_seq.df.pop('obs_num')
    obs_seq.df.insert(0, 'obs_num', column_to_move)
    column_to_move = obs_seq.df.pop('linked_list')
    obs_seq.df.insert(1, 'linked_list', column_to_move)
    return obs_seq

# %% adds observations to a list
def add_obs_to_list(list_rows: list, latitude: float, longitude: float, vertical: float, vert_unit: int, obs_type: str, timestamp: dt.datetime, obs_err_var: float, metadata=[], external_FO=[]) -> None:
    """
    Constructs a single observation dictionary and appends it in-place to
    list_rows. The observation is converted to DART time format before storage.

    Args:
        list_rows (list): Accumulator list to which the new observation dict
            is appended. Modified in-place; nothing is returned.
        latitude (float): Latitude of the observation in degrees.
        longitude (float): Longitude of the observation in degrees.
        vertical (float): Vertical coordinate of the observation (value
            interpreted according to vert_unit).
        vert_unit (int): DART vertical coordinate type code (e.g. pressure,
            height, model level).
        obs_type (str): DART observation type string
            (e.g. 'RADIOSONDE_TEMPERATURE').
        datetime (dt.datetime): Observation time. Converted internally to
            DART time (seconds, days) via convert_to_dart_time(); also stored
            as an 'HH:MM:SS' time string.
        obs_err_var (float): Observation error variance (not standard
            deviation). Units must match the observation type.
        metadata (list, optional): Additional metadata fields associated with
            the observation. Defaults to [].
        external_FO (list, optional): External forward operator values.
            Defaults to [].

    Returns:
        None: list_rows is mutated directly.
    """
    dart_time = obsq._convert_to_dart_time(timestamp)
    new_obs = {'longitude': float(longitude), 'latitude': float(latitude), 'vertical': vertical, 'vert_unit': vert_unit, 'type': obs_type, 'metadata': metadata, 'external_FO': external_FO, 'seconds': dart_time[0], 'days':dart_time[1],'time' : timestamp, 'obs_err_var': obs_err_var}
    list_rows.append(new_obs)

# %% adds list to obs seq dataframe
def add_list_to_df(list_rows, obs_seq) -> None:
    """
    Converts a list of observation dictionaries into a DataFrame and merges it
    into the existing obs_seq.df, then refreshes the ObsSequence header and
    attributes to reflect the updated data.

    Args:
        list_rows (list[dict]): List of observation dictionaries, each
            produced by add_obs_to_list(). All dicts must share the same
            keys; missing keys in any row will produce NaN columns in the
            merged DataFrame.
        obs_seq (obsq.ObsSequence): ObsSequence object to update. Its df,
            header, and attributes are all mutated in-place.

    Returns:
        None: obs_seq is mutated directly.

     Example:
        .. code-block:: python

            obs_seq = create_obs_seq_in()
            rows = []
            add_obs_to_list(rows, latitude=40.0, longitude=-105.3, vertical=850.0, vert_unit=2,
                            obs_type='RADIOSONDE_TEMPERATURE', 
                            datetime=dt.datetime(2024, 1, 15, 12, 0, 0), obs_err_var=1.0)
            add_list_to_df(rows, obs_seq)
    """
    df_new = pd.DataFrame(list_rows)
    obs_seq.df = pd.concat([obs_seq.df, df_new], ignore_index=True)
    obs_seq.create_header_from_dataframe()
    obs_seq.update_attributes_from_df()

# %%

"""def split_obs_seq_and_write(obs_seq: obsq.ObsSequence, output_dir: str, file_stub: str, column_name: str):

    Splits an ObsSequence's DataFrame into groups based on unique values of
    a specified column, then writes each group out as its own obs_seq.in
    file named by that column's value.

    For each unique value in column_name, this creates a fresh, empty
    ObsSequence via create_obs_seq_in(), populates it with that subset's
    rows via add_list_to_df(), and writes the result to disk. Commonly used
    to split a multi-day obs sequence into per-day files (e.g. grouping by
    'days') for separate perfect_model_obs or filter runs.

    Args:
        obs_seq (obsq.ObsSequence): Source ObsSequence containing the full,
            unsplit set of observations in obs_seq.df.
        column_name (str): Name of the column to group by (e.g. 'days').
            Each unique value produces one output file, and the value
            itself is used in the output filename.

    Returns:
        None: Writes one obs_seq_<value>.in file per group to the current
        working directory. Nothing is returned.
    
    Output files:
        Named obs_seq_{value}.in, where {value} is taken from column_name's
        value in the first row of each group.

    Example:
        >>> split_obs_seq_and_write(obs_seq, 'days')
        # Writes: obs_seq_150633.in, obs_seq_150634.in, obs_seq_150635.in, ...

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    dfs_list = [group for _, group in obs_seq.df.groupby(f'{column_name}', sort=False)]

    for group_df in dfs_list:
        df_group = group_df.to_dict(orient='records')
        obs_seq_group = create_obs_seq_in()
        add_list_to_df(df_group, obs_seq_group)
        time_str = f'{dfs_list[ii][{time}].iloc[0].strftime('%Y-%m-'+'0'+'%d')}'
        case_stub = Path(f"{file_stub}{time_str}")
        out_path = output_path / case_stub / "obs_seq.in"
        obs_seq_group.write_obs_seq(str(out_path))
        
    for ii in range(len(dfs_list)):
        df_day = dfs_list[ii].to_dict(orient='records')
        
        obs_seq_group = create_obs_seq_in()
        add_list_to_df(df_day,obs_seq_group)
        obs_seq_group.write_obs_seq(f"obs_seq_{dfs_list[ii][f'{time}'].iloc[0].strftime('%Y-%m-'+'0'+'%d')}.in")"""

from pathlib import Path
import pandas as pd


"""def split_obs_seq_by_week(obs_seq: "obsq.ObsSequence", output_dir: str, file_stub: str, sim_start):

    Splits an ObsSequence into weekly groups, where each calendar month
    RESTARTS its own week-0 anchor at sim_start's day-of-month (rather than
    binning continuously across month boundaries). E.g. if sim_start is the
    4th, weeks within September start at the 4th, 11th, 18th, 25th — and
    October independently restarts its own week-0 at the 4th, not continuing
    from wherever September's last week left off.

    Each week's obs_seq.in is written into its own subdirectory, named
    {file_stub}{YYYY}-{MM:02d}-{DD:03d} using that week's actual start date
    (DD zero-padded to 3 digits, matching the existing per-hour directory
    convention, e.g. ...h.z.2015-01-001-24).

    Args:
        obs_seq: Source ObsSequence with the full, unsplit observations.
        output_dir: Base directory under which week subdirectories are created.
        file_stub: Filename prefix for each subdirectory
            (e.g. "EEP_MITgcm185Lvgrid_Whitt2026hgrid.mom6.h.z.").
        sim_start: datetime-like (str or pd.Timestamp) — reference date whose
            day-of-month defines each month's week-0 anchor. Required
            explicitly; guessing wrong silently shifts every week boundary.

    Output:
        One {output_dir}/{file_stub}{week_start_date}/obs_seq.in per
        (month, week) group.

    Returns:
        None.
    
    sim_start = pd.Timestamp(sim_start)
    anchor_day = sim_start.day
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    df = obs_seq.df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['time']):
        raise TypeError(
            f"obs_seq.df['time'] is not a datetime dtype "
            f"({df['time'].dtype}) — check the ObsSequence was loaded "
            f"correctly before splitting."
        )

    # each row's month-anchor = same year/month as the row, but day = anchor_day
    # (e.g. anchor_day=4 -> Sept rows anchor to Sept 4, Oct rows to Oct 4)
    month_anchor = pd.to_datetime(
        {'year': df['time'].dt.year, 'month': df['time'].dt.month, 'day': anchor_day}
    )
    days_since_anchor = (df['time'] - month_anchor).dt.days
    if (days_since_anchor < 0).any():
        n_before = (days_since_anchor < 0).sum()
        print(f"NOTE: {n_before} obs fall before their month's anchor day "
              f"({anchor_day}) — e.g. obs on Sept 1-3 if anchor_day=4. "
              f"These get a negative 'week' bin (-1), grouped separately "
              f"rather than merged into week 0 or dropped. Confirm this is "
              f"what you want; if these should belong to the previous "
              f"month's last week instead, this function does not handle "
              f"that — flag it and I'll adjust.")

    df['month_key'] = df['time'].dt.to_period('M')
    df['week'] = days_since_anchor // 7

    groups = [group for _, group in df.groupby(['month_key', 'week'], sort=True)]
    print(f"Found {len(groups)} (month, week) groups spanning "
          f"{df['time'].min()} to {df['time'].max()}.")

    for group_df in groups:
        month_key = group_df['month_key'].iloc[0]
        week_num = group_df['week'].iloc[0]
        this_anchor = pd.Timestamp(year=month_key.year, month=month_key.month, day=anchor_day)
        week_start = this_anchor + pd.Timedelta(days=int(week_num * 7))

        dir_name = f"{file_stub}{week_start.year}-{week_start.month:02d}-{week_start.day:03d}"
        out_dir = output_path / dir_name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "obs_seq.in"

        actual_start = group_df['time'].min()
        if abs((actual_start - week_start).days) > 6:
            print(f"NOTE: week starting {week_start.date()} — first actual "
                  f"obs is {actual_start} (>6 days off nominal start). "
                  f"Check for gaps in obs coverage for this week.")

        df_group = group_df.drop(columns=['month_key', 'week']).to_dict(orient='records')
        obs_seq_group = create_obs_seq_in()
        add_list_to_df(df_group, obs_seq_group)
        obs_seq_group.write_obs_seq(str(out_path))
        print(f"Wrote {len(group_df)} obs to {out_path}")"""


def split_obs_seq_by_date(obs_seq: "obsq.ObsSequence", output_dir: str, file_stub: str):
    """
    Splits an ObsSequence into separate daily groups based on the exact date 
    found in the 'time' column.

    Each unique date produces one subdirectory named:
    {file_stub}{YYYY}-{MM:02d}-{DD:03d}
    Where DD is zero-padded to 3 digits to match standard directory conventions
    (e.g., ...h.z.2015-01-001).

    Args:
        obs_seq: Source ObsSequence with the full, unsplit observations.
        output_dir: Base directory under which daily subdirectories are created.
        file_stub: Filename prefix for each subdirectory
            (e.g. "EEP_MITgcm185Lvgrid_Whitt2026hgrid.mom6.h.z.").

    Output:
        One {output_dir}/{file_stub}{date}/obs_seq.in per unique date.

    Returns:
        None.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    df = obs_seq.df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['time']):
        raise TypeError(
            f"obs_seq.df['time'] is not a datetime dtype "
            f"({df['time'].dtype}) — check the ObsSequence was loaded "
            f"correctly before splitting."
        )

    # Extract the pure date (midnight normalized) to group observations cleanly by day
    df['_date_key'] = pd.to_datetime(df['time']).dt.normalize()

    # Group the dataframe by each unique date found in the file
    groups = [group for _, group in df.groupby('_date_key', sort=True)]
    print(f"Found {len(groups)} unique date groups spanning "
          f"{df['time'].min()} to {df['time'].max()}.")

    for group_df in groups:
        # Extract the target date for this specific chunk
        current_date = group_df['_date_key'].iloc[0]
        
        # Format the folder name matching the 3-digit day padding rule: {DD:03d}
        # Example: Day 4 of the month becomes 004
        dir_name = f"{file_stub}{current_date.year}-{current_date.month:02d}-{current_date.day:03d}"
        
        out_dir = output_path / dir_name
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "obs_seq.in"

        # Remove the temporary grouping key before exporting columns to the dictionary
        df_group = group_df.drop(columns=['_date_key']).to_dict(orient='records')
        
        # Build and write the DART observation sequence file
        obs_seq_group = create_obs_seq_in()
        add_list_to_df(df_group, obs_seq_group)
        obs_seq_group.write_obs_seq(str(out_path))
        



# --- usage ---
# split_obs_seq_by_week(
#     obs_seq,
#     output_dir="/glade/derecho/scratch/iranjan/weekly_eep_osse",
#     file_stub="EEP_MITgcm185Lvgrid_Whitt2026hgrid.mom6.h.z.",
#     sim_start="2015-09-04",
# )


def split_obs_seq_by_time(obs_seq: obsq.ObsSequence, output_dir: str, file_stub: str) -> None:
    """
    Splits an ObsSequence into separate obs_seq.in files grouped by unique
    values in the 'time' column, which contains datetime objects.

    Each unique datetime produces one output file named by that datetime.
    Time bins run from 03:00 to 24:00 (i.e. the timestamp reflects the end
    of each 3-hour averaging period).

    Redirects output files into a directory named "outputs".

    Args:
        obs_seq (obsq.ObsSequence): Source ObsSequence to split.
        output_dir (str): Directory to write output files. Defaults to
            current working directory.
        file_stub (str): Optional subdirectory under output_dir. If empty,
            files are written directly to output_dir.

    Returns:
        None: Writes one obs_seq_<datetime>.in file per unique time value.

    Example:
        >>> split_obs_seq_by_time(obs_seq, output_dir='/path/to/output')
        # Writes: obs_seq_2015-01-01_030000.in
        #         obs_seq_2015-01-01_060000.in ...
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    df = obs_seq.df.copy()

    # Shift times so 03:00 is the first bin and 24:00 (midnight) is the last
    # by flooring to 3-hour bins anchored at 03:00
  
    def assign_bin(t):
        # Subtract 1 second so that exactly 03:00, 06:00 etc fall in their own bin
        hour_bin = ((t.hour - 1) // 3 + 1) * 3   # gives 3,6,9,...,24
        if hour_bin == 24:
            # Roll midnight forward to next day
            next_day = t.replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)
            return next_day
        return t.replace(hour=hour_bin, minute=0, second=0, microsecond=0)

    df['_time_bin'] = df['time'].apply(assign_bin)

    dfs_list = [group for _, group in df.groupby('_time_bin', sort=True)]

    for group_df in dfs_list:
        bin_time = group_df['_time_bin'].iloc[0]
        group_df = group_df.drop(columns='_time_bin')

        df_group = group_df.to_dict(orient='records')
        obs_seq_group = create_obs_seq_in()
        add_list_to_df(df_group, obs_seq_group)

        if bin_time.hour == 0:
        # This is the 24:00 bin — label using previous day + 24
            prev_day = bin_time - dt.timedelta(days=1)
            time_str = prev_day.strftime('%Y-%m-'+'0'+'%d') + '-24'
        else:
            time_str = bin_time.strftime('%Y-%m-'+'0'+'%d-%H')
        case_stub = Path(f"{file_stub}{time_str}")
        out_path = output_path / case_stub / "obs_seq.in"
        obs_seq_group.write_obs_seq(str(out_path))

