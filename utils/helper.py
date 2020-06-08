import pandas as pd
import math
import numpy as np


def deltatime_to_float(delta):
    if type(delta) is pd._libs.tslibs.timedeltas.Timedelta:
        return delta.to_timedelta64().astype('timedelta64[s]').item().total_seconds() / 3600

    else:
        return None


def calculate_real_time(stop_lat, previous_py, stop_lon, previous_px, py, px, time):
    value = math.sqrt((stop_lat - previous_py)**2 + (stop_lon - previous_px)**2)
    value = value/math.sqrt((py - previous_py)**2 + (px - previous_px)**2)
    return time * value


def validate_time(df, stop_time, ta, index):
    return df[(df['ta'] == ta) & (df['stop_sequence'] == index - 1)]['time'].size != 0 and stop_time - df[(df['ta'] == ta) &
           (df['stop_sequence'] == index - 1)]['time'].values[0] > 0


def get_time_between_stops(index, ta, previous_ta, bus_stop_time, association_df):
    if index > 1:
        if validate_time(association_df, bus_stop_time, ta, index):
            return bus_stop_time - association_df[(association_df['ta'] == ta) & (association_df['stop_sequence'] == index - 1)
                                                  ]['time'].values[0]

        if association_df[(association_df['ta'] == previous_ta) & (association_df['stop_sequence'] == index - 1)]['time'].size != 0:

            time_between_stops = bus_stop_time - association_df[(association_df['ta'] == previous_ta) &
                                                                (association_df['stop_sequence'] == index - 1)]['time'].values[0]

            time_between_stops = time_between_stops + (association_df[(association_df['ta'] == previous_ta) &
                                                       (association_df['stop_sequence'] == index - 1)]['ta'].values[0] -
                                                       np.datetime64('1970-01-01T00:00:00Z'))/np.timedelta64(1, 's')/60

            return time_between_stops - (association_df[(association_df['ta'] == previous_ta) &
                                         (association_df['stop_sequence'] == index - 1)]['previous_ta'].values[0] -
                                         np.datetime64('1970-01-01T00:00:00Z'))/np.timedelta64(1, 's')/60
    return np.nan
