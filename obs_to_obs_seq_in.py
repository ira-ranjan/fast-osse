# %%
import pydartdiags.obs_sequence.obs_sequence as obsq
import pandas as pd
import datetime as dt

# %% converts datetime object to DART readable sconds, days
def convert_to_dart_time(time: dt.datetime):
    """Converts datetime object to a list of seconds, days after 1601"""
    dart_time = time - dt.datetime(1601, 1, 1)
    return [dart_time.seconds, dart_time.days]

# %% creates a new obs_seq object with 0 copies (obs_seq.in)
def create_obs_seq_in():
    """Creates new obs_sequence object with column titles, header, and attributes"""
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
    #moves columns to fulfill list_to_obs requirements
    column_to_move = obs_seq.df.pop('obs_num')
    obs_seq.df.insert(0, 'obs_num', column_to_move)
    column_to_move = obs_seq.df.pop('linked_list')
    obs_seq.df.insert(1, 'linked_list', column_to_move)
    return obs_seq

# %% creates an empty list to store observations
def create_obs_list():
    list_rows = []
    return list_rows

# %% adds observations to a list
def add_obs_to_list(list_rows: list, latitude: float, longitude: float, vertical: float, vert_unit: int, obs_type: str, datetime: dt.datetime, obs_err_var: float, metadata=[], external_FO=[]):
    dart_time = convert_to_dart_time(datetime)
    new_obs = {'longitude': float(longitude), 'latitude': float(latitude), 'vertical': vertical, 'vert_unit': vert_unit, 'type': obs_type, 'metadata': metadata, 'external_FO': external_FO, 'seconds': dart_time[0], 'days':dart_time[1],'time' : datetime.strftime("%H:%M:%S"), 'obs_err_var': obs_err_var}
    list_rows.append(new_obs)

# %% adds list to obs seq dataframe
def add_list_to_df(list_rows, obs_seq):
    df_new = pd.DataFrame(list_rows)
    obs_seq.df = pd.concat([obs_seq.df, df_new], ignore_index=True)
    obs_seq.create_header_from_dataframe()
    obs_seq.update_attributes_from_df()

# %%



