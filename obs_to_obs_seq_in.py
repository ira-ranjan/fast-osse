
# %%
import pydartdiags.obs_sequence.obs_sequence as obsq
import pandas as pd
import datetime as dt
from pathlib import Path

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

def split_obs_seq_and_write(obs_seq: obsq.ObsSequence, column_name: str, output_dir: str):
    """
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
    """
    dfs_list = [group for _, group in obs_seq.df.groupby(f'{column_name}', sort=False)]
    for ii in range(len(dfs_list)):
        df_day = dfs_list[ii].to_dict(orient='records')
        obs_seq_group = create_obs_seq_in()
        add_list_to_df(df_day,obs_seq_group)
        obs_seq_group.write_obs_seq(f"obs_seq_{dfs_list[ii][f'{column_name}'].iloc[0].in")

    def split_obs_seq_by_time(obs_seq: obsq.ObsSequence, output_dir: str = '.') -> None:
    """
    Splits an ObsSequence into separate obs_seq.in files grouped by unique
    values in the 'time' column, which contains datetime objects.

    Each unique datetime produces one output file named by that datetime.
    Equivalent to split_obs_seq_and_write but operates on datetime objects
    in the 'time' column rather than integer 'days' values.

    Args:
        obs_seq (obsq.ObsSequence): Source ObsSequence to split.
        output_dir (str): Directory to write output files. Defaults to
            current working directory.

    Returns:
        None: Writes one obs_seq_<datetime>.in file per unique time value.

    Example:
        >>> split_obs_seq_by_time(obs_seq, output_dir='/path/to/output')
        # Writes: obs_seq_2015-01-01 00:00:00.in
        #         obs_seq_2015-01-01 03:00:00.in ...
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    dfs_list = [group for _, group in obs_seq.df.groupby('time', sort=False)]

    for ii in range(len(dfs_list)):
        df_group = dfs_list[ii].to_dict(orient='records')
        obs_seq_group = create_obs_seq_in()
        add_list_to_df(df_group, obs_seq_group)

        time_val = dfs_list[ii]['time'].iloc[0]
        # Format datetime to avoid colons in filename (invalid on some systems)
        time_str = time_val.strftime('%Y-%m-'+'0'+'%d-%H')
        out_path = output_path / f"obs_seq_{time_str}.in"
        obs_seq_group.write_obs_seq(str(out_path))

def split_obs_seq_by_time(obs_seq: obsq.ObsSequence, output_dir: str = '.'):
        
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    dfs_list = [group for _, group in obs_seq.df.groupby('time', sort=False)]

    for ii in range(len(dfs_list)):
        df_group = dfs_list[ii].to_dict(orient='records')
        obs_seq_group = create_obs_seq_in()
        add_list_to_df(df_group, obs_seq_group)

        time_val = dfs_list[ii]['time'].iloc[0]
        time_str = time_val.strftime('%Y-%m-%d-%H')
        out_path = output_path / f"obs_seq_{time_str}.in"
        obs_seq_group.write_obs_seq(str(out_path))




