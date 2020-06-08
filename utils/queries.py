from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px
import time

from utils import helper


engine = create_engine('../database/bus.db')
connection = engine.connect()


def get_routes():
    """Gets all routes from bus database. Returns route long name and id."""
    
    query = text("""SELECT route_id, route_long_name FROM routes""")
    result = connection.execute(query)

    routes = pd.DataFrame(result.fetchall(), columns=result.keys())
    
    return routes


def get_shape(route):
    """Gets the shape of a specific route."""
    if route:
        route = '%' + route + '%'

        # Query accesses trips table where the row's route_id matches the route input. Then it joins the routes table
        # in order to get the route and text's color that should be plotted. Finally, this table is joined with the
        # shapes table and we have access to the coordinates of the polyline.
        query = text("""SELECT route_id, color, text_color, shapes.shape_id, index, shape_pt_lat, shape_pt_lon,
                        shape_pt_sequence, shape_dist_traveled
                        FROM (SELECT trips.route_id, route_color as color, route_text_color as text_color,trips.shape_id
                        FROM trips
                        JOIN routes ON routes.route_id = trips.route_id
                        WHERE trips.route_id LIKE :bus_route) as A
                        JOIN shapes ON A.shape_id = shapes.shape_id;""")

        result = connection.execute(query, bus_route=route)

        shape = pd.DataFrame(result.fetchall(), columns=result.keys())

        shape.sort_values(['shape_id', 'shape_pt_sequence'], ignore_index=True, inplace=True)
    else:
        shape = None
    
    return shape


def get_stops(route):

    if route:

        route = '%' + route + '%'

        # Query accesses trips table where the row's route_id matches the route input. Then it joins the stop_times
        # table as it has the stop_id column. Finally, we join the stops table and have access to all the stops names,
        # latitudes, and longitudes of the route.
        query = text("""SELECT stops.stop_id, stop_name, stop_lat, stop_lon
                        FROM (SELECT *
                        FROM trips
                        INNER JOIN stop_times ON stop_times.trip_id = trips.trip_id
                        WHERE route_id LIKE :bus_route) as A
                        JOIN stops ON stops.stop_id = A.stop_id;""")
        result = connection.execute(query, bus_route=route)

        stops = pd.DataFrame(result.fetchall(), columns=result.keys())

    else:

        stops = None
    
    return stops


def weekly_passengers(route):

    if route:

        # Gets the date of the observation, the number of passenger, and the name of the inputt route.
        route = '%' + route + '%'
        query = text("""SELECT passengers.date, passengers.passengers, passengers.name FROM passengers
                        WHERE routes LIKE :bus_route""")

        result = connection.execute(query, bus_route=route)
        passengers = pd.DataFrame(result.fetchall(), columns=result.keys())

        passengers.sort_values('date', ignore_index=True, inplace=True)

        # Processes the date strings and sets it as index
        passengers['date'] = pd.to_datetime(passengers['date'])
        passengers.set_index('date', inplace=True)

        # Groups everything by day of the week and then by quarter.
        agg = passengers.groupby([(passengers.index.day_name()), passengers.index.quarter.values]).mean()

        # Days of the week are not ordered the right way. Reindexes it with Sunday as the first day.
        days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        agg = agg.reindex(days, level=0)

        # Gives the indexes name
        agg.index.names = ['weekday', 'quarter']
        agg = agg.reset_index()

        # Create a plotly lineplot of the number of passengers per weekday, with quarter as a hue.
        fig = px.line(agg, x='weekday', y='passengers', color='quarter',
                      title=f'Average Number of Passengers X Weekday per Quarter')

    else:

        fig = px.line()

    return fig


def historial_timedelta(route, stop_id_1, stop_id_2, hour):

    print('Historical time query has started!')

    now = time.time()
    query = text("""
                 SELECT A.c, id, p, ta, py, px
                 FROM (SELECT * 
                 FROM api_routes 
                 WHERE c LIKE :bus_route) AS A
                 INNER JOIN bus_position ON A.cl = bus_position.cl;
                 """)

    result = connection.execute(query, bus_route='1012-10')
    bus_position = pd.DataFrame(result, columns=result.keys())

    print('Master query time: ', time.time() - now)

    now = time.time()
    bus_position['ta'] = pd.to_datetime(bus_position['ta']).dt.tz_convert('America/Sao_Paulo')
    bus_position.sort_values(['p', 'ta'], ignore_index=True, inplace=True)

    grouped_cl = bus_position.groupby('p')
    shifted_values = grouped_cl.shift(1)[['ta', 'py', 'px']]
    shifted_values.columns = ['previous_ta', 'previous_py', 'previous_px']
    bus_position = pd.concat([bus_position, shifted_values], axis=1)

    bus_position['timedelta'] = bus_position.apply(
        lambda x: (x['ta'] - x['previous_ta']) if x['previous_ta'] else None, axis=1)

    bus_position['timedelta'] = bus_position['timedelta'].apply(helper.deltatime_to_float)

    query = text("""
                SELECT DISTINCT(B.stop_id), B.route_id, stop_lat, stop_lon, stop_name, B.stop_sequence, B.trip_id
                FROM (SELECT A.route_id, A.trip_id, stop_id, stop_sequence
                FROM (SELECT route_id, trip_id
                FROM trips
                WHERE route_id LIKE :bus_route) as A
                JOIN stop_times ON A.trip_id = stop_times.trip_id) as B
                JOIN stops ON B.stop_id = stops.stop_id
                WHERE B.stop_id = :stop_id_1 OR B.stop_id = :stop_id_2
                ORDER BY stop_sequence;
                 """)
    result = connection.execute(query, bus_route=route, stop_id_1=stop_id_1, stop_id_2=stop_id_2)
    stops = pd.DataFrame(result, columns=result.keys())

    first_stop, second_stop = (stops['stop_name'].unique())

    print('We have done the second query in ', time.time() - now)
    now = time.time()

    index_list = []
    id_list = []
    for index, row in stops.iterrows():

        i_list = list()
        i_list.append(bus_position[
                              (((bus_position['previous_py'] <= row['stop_lat']) & (row['stop_lat'] <= bus_position['py']) & (
                                          bus_position['previous_px'] <= row['stop_lon']) & (
                                            row['stop_lon'] <= bus_position['px'])) |
                               ((bus_position['py'] <= row['stop_lat']) & (row['stop_lat'] <= bus_position['previous_py']) & (
                                           bus_position['px'] <= row['stop_lon']) & (
                                            row['stop_lon'] <= bus_position['previous_px'])) |
                               ((bus_position['py'] <= row['stop_lat']) & (row['stop_lat'] <= bus_position['previous_py']) & (
                                           bus_position['previous_px'] <= row['stop_lon']) & (
                                            row['stop_lon'] <= bus_position['px'])) |
                               ((bus_position['previous_py'] <= row['stop_lat']) & (row['stop_lat'] <= bus_position['py']) & (
                                           bus_position['px'] <= row['stop_lon']) & (
                                            row['stop_lon'] <= bus_position['previous_px'])))]['id'].values)

        for i_value in i_list:
            for value in i_value:
                index_list.append(index)
                id_list.append(value)
    association_df = pd.DataFrame({'index': index_list, 'id': id_list})

    print('Way to go. Since last observation we took ', time.time() - now)
    now = time.time()

    association_df['ta'] = association_df.apply(lambda x: bus_position[bus_position['id'] == x['id']]['ta'].values[0], axis=1)
    association_df['previous_ta'] = association_df.apply(
        lambda x: bus_position[bus_position['id'] == x['id']]['previous_ta'].values[0], axis=1)

    association_df['stop_sequence'] = association_df.apply(
        lambda x: stops[stops.index == x['index']]['stop_sequence'].values[0], axis=1)

    print('Way to go 2. Since last observation we took ', time.time() - now)
    now = time.time()

    association_df['time'] = association_df.apply(lambda x: helper.calculate_real_time(stops.iloc[x['index']]['stop_lat'],
                                                            bus_position[bus_position['id'] == x['id']][
                                                                'previous_py'],
                                                            stops.iloc[x['index']]['stop_lon'],
                                                            bus_position[bus_position['id'] == x['id']][
                                                                'previous_px'],
                                                            bus_position[bus_position['id'] == x['id']]['py'],
                                                            bus_position[bus_position['id'] == x['id']]['px'],
                                                            ((time.mktime(
                                                                x['ta'].timetuple()) / 60) - (
                                                                         time.mktime(x[
                                                            'previous_ta'].timetuple()) / 60))), axis=1)

    association_df['time_between_stops'] = association_df.apply(
        lambda x: helper.get_time_between_stops(x['stop_sequence'], x['ta'], x['previous_ta'], x['time'], association_df),
                                                                                                                 axis=1)
    print('Way to go 3. Since last observation we took ', time.time() - now)
    now = time.time()

    association_df.dropna(subset=['time_between_stops'], inplace=True)

    association_df.set_index(['ta'], inplace=True)
    association_df = association_df[association_df['time_between_stops'] < 10]

    agg = association_df.groupby([association_df.index.hour, association_df.index.day_name()]).mean()

    days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    agg = agg.reindex(days, level=1)

    agg.index.names = ['hour', 'weekday']
    agg = agg.reset_index()

    agg['hour'] = agg['hour'].apply(lambda x: str(x).zfill(2) + ':' + '00')

    filtered = agg[agg['hour'] == hour]

    print('Now generating graph. Took ', time.time() - now)

    fig = px.bar(filtered, x='weekday', y='time_between_stops', title=f'Time it takes from '
                                                                      f'{first_stop} and {second_stop}')

    return fig
