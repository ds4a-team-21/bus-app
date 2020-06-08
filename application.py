# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html

from utils import queries
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import time
import datetime

# Starting dash!
app = dash.Dash(__name__)
application = app.server
app.title = 'São Paulo Bus System Analysis'

# Getting data frame of all São Paulo bus routes
routes = queries.get_routes()

# Transforming data frame into list with dictionaries.
routes_data = routes[['route_id', 'route_long_name']].apply(lambda x: {'label': x['route_long_name'],
                                                                       'value': x['route_id']}, axis=1).to_list()
# App layout
app.layout = html.Div(children=[ # Master div
    html.Div([ # Dropdown container
        dcc.Dropdown( # Bus route dropdown
            id='dropdown-route',
            options=routes_data,
            placeholder='Select a bus route',
            value='',
            className='dropdown'
        ),
        html.Br(),
        dcc.Dropdown( # First stop dropdown
            id='dropdown-stop-first',
            options=[],
            placeholder='Select the first stop',
            className='dropdown'
        ),
        html.Br(),
        dcc.Dropdown( # Second stop dropdown
            id='dropdown-stop-second',
            options=[],
            placeholder='Select the second stop',
            className='dropdown'
        ),
        dcc.Dropdown( # Hour of the day
            id='dropdown-hour',
            options=[{'label': datetime.time(i).strftime('%I %p'), 'value': str(i).zfill(2) + ':' + '00'}
                     for i in range(24)],
            placeholder='Select hour',
            className='dropdown'
        )
    ], className='dropdown-container'),
    html.Div([ # Graphs and maps container
        html.Div([ # Map
            dcc.Graph(
                id='map-graph'
            )
        ], className='map'),
        html.Div([ # Passengers graph
            dcc.Graph(
                id='passengers-graph'
            )
        ], className='passengers'),
        html.Div([ # Time graph
            dcc.Graph(
                id='time-graph'
            )
        ], className='time')
    ], className='analysis'),
    html.Div(className='clearfix'),

    html.P(id='time'),

    html.Div(children=[ # Footer
            html.Div(children=[
                html.P(children='Team 21 - São Paulo Bus Transit Times', className='footer-text'),

                html.P(children='''
                    Project by João Pedro Barreto, Rafael Alves de Souza, and Henrique Novak
                ''', className='footer-text')], className='footer')], className='footer-container')
])


# Function input is the chosen route from the dropdown button
@app.callback(
    Output('map-graph', 'figure'),
    [Input('dropdown-route', 'value')]
)
def update_map(route):
    """Updates São Paulo's map when a route is chosen."""

    now = time.time()

    # If there is no route chosen, display empty map centered in São Paulo
    if not route:
        bus_stops = {'stop_lat': [-23.5507], 'stop_lon': [-46.6334], 'stop_name': []}

    # If a route is chosen, do the following:
    else:
        # Get all stops from that route
        stops = queries.get_stops(route)

        # Check if we have the stops for that route
        if not stops.empty:
            bus_stops = stops

        # If we don't have, display empty map
        else:
            bus_stops = {'stop_lat': [-23.5507], 'stop_lon': [-46.6334], 'stop_name': []}

    # Generates plotly map. If a route is chosen, will create markers for the stops
    fig = go.Figure(go.Scattermapbox(
            lat=bus_stops['stop_lat'],
            lon=bus_stops['stop_lon'],
            text=bus_stops['stop_name'],
            mode='markers',
            marker=go.scattermapbox.Marker(size=7, opacity=0.7),
            name='Stops'
        )
    )

    # If a route is chosen
    if route and route is not None:

        # Get the shape of the route
        shape = queries.get_shape(route)

        # Check if we have the shape for that route
        if not shape.empty:
            color = '#' + shape['color'].iloc[0]

            # Create line shape
            fig.add_trace(go.Scattermapbox(
                lat=shape['shape_pt_lat'].to_list(),
                lon=shape['shape_pt_lon'].to_list(),
                mode='lines',
                marker=go.scattermapbox.Marker(
                    color=color,
                    opacity=0.7
                ),
                text=shape['route_id'].iloc[0],
                hoverinfo='text',
                name='Route'
            ))

    # Extra detailing of the map
    fig.update_layout(
        title='Interactive Map of São Paulo',
        mapbox=go.layout.Mapbox(
            style='open-street-map',
            bearing=0,
            center=go.layout.mapbox.Center(
                lat=list(bus_stops['stop_lat'])[0],
                lon=list(bus_stops['stop_lon'])[0]
            ),
            pitch=0,
            zoom=12
        )
    )

    print('Time of execution: ', time.time() - now)

    return fig


# Function input is the chosen route from the dropdown button
@app.callback(
    Output('passengers-graph', 'figure'),
    [Input('dropdown-route', 'value')]
)
def update_passengers(route):

    # If there is a route chosen
    if route:

        # Get the figure for weekly passengers
        fig = queries.weekly_passengers(route)

    else:
        # Display empty figure
        fig = go.Figure()

    fig.update_layout(xaxis_title='Weekday', yaxis_title='Number of Passengers', title=dict(x=0.5))
    
    return fig


# Function input is the first-stop dropdown
@app.callback(
    Output('dropdown-stop-first', 'options'),
    [Input('dropdown-route', 'value')]
)
def update_first_stop(route):
    if route is None or not route:
        return []

    stops = queries.get_stops(route)
    stop_data = []

    for i in range(len(stops)):
        row = stops.iloc[i]
        stop_data.append({'label': row['stop_name'], 'value': row['stop_id']})
    return stop_data


# Function input is the second-stop dropdown
@app.callback(
    Output('dropdown-stop-second', 'options'),
    [Input('dropdown-route', 'value')]
)
def update_second_stop(route):
    if route is None or not route:
        return []

    stops = queries.get_stops(route)
    stop_data = []

    for i in range(len(stops)):
        row = stops.iloc[i]
        stop_data.append({'label': row['stop_name'], 'value': row['stop_id']})
    return stop_data


# Function input is the first-stop, second-stop dropdown, and route
@app.callback(
    Output('time-graph', 'figure'),
    [Input('dropdown-route', 'value'), Input('dropdown-stop-first', 'value'), Input('dropdown-stop-second', 'value'),
     Input('dropdown-hour', 'value')]
)
def calc_time(route, first_stop, second_stop, hour):

    if route is not None and first_stop is not None and second_stop is not None and hour is not None:
        fig = queries.historial_timedelta(route, first_stop, second_stop, hour)
        print('Uhul! Got the graph!')

    else:

        fig = go.Figure()

    fig.update_layout(xaxis_title='Weekday', yaxis_title=f'Time between stops', title=dict(x=0.5, font={'size': 15}))

    print('Sending graph!')
    return fig


if __name__ == '__main__':
    application.run(port=8080)
