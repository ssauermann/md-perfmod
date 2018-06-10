# -*- coding: utf-8 -*-
import subprocess

import dash
import dash_core_components as dcc
import dash_html_components as html
import os
import pandas as pd
import plotly.graph_objs as go
import tempfile
from dash.dependencies import Input, Output
from functools import partial
import re
from flask_caching import Cache

csv_file_path = os.path.relpath('../ls1-bench1.csv')
df = pd.read_csv(csv_file_path)

app = dash.Dash()
cache = Cache(app.server, config={'CACHE_TYPE': 'simple'})

sliders = []
slider_names = []


def add_slider(column):
    sid = 'slider%i' % len(sliders)
    sliders.append(dcc.Slider(
        id=sid,
        min=df[column].min(),
        max=df[column].max(),
        value=df[column].min(),
        step=None,
        updatemode='drag',
        marks={int(i) if i % 1 == 0 else i: '{}'.format(i) for i in df[column].unique()},
    ))
    slider_names.append(sid)


selectable_columns = []
metric_columns = []

for c in df.columns:
    if 1 < len(df[c].unique()) < len(df) / 2:
        selectable_columns.append(c)
        add_slider(c)
    elif 1 < len(df[c].unique()):
        metric_columns.append(c)

app.layout = html.Div(children=[
    html.H1('Benchmark visualization'),

    html.Div([
        html.Div([
            html.H3('Variable'),
            dcc.Dropdown(
                id='sel_var1',
                options=list(map(lambda c: {'label': c, 'value': c}, selectable_columns)),
                value=selectable_columns[0]
            )
        ], style={'width': '25%', 'float': 'left', 'display': 'inline-block'}),
        html.Div([
            html.H3('Metric'),
            dcc.Dropdown(
                id='sel_metric',
                options=list(map(lambda c: {'label': c, 'value': c}, metric_columns)),
                value=metric_columns[0]
            )
        ], style={'width': '25%', 'float': 'left', 'display': 'inline-block'}),
        html.Div([
            html.H3('Repeat'),
            dcc.Dropdown(
                id='sel_repeat',
                options=list(map(lambda c: {'label': c, 'value': c}, selectable_columns)),
                value=selectable_columns[len(selectable_columns) - 1]
            )
        ], style={'width': '25%', 'float': 'left', 'display': 'inline-block'}),
        html.Div([
            html.H3('Comparison'),
            dcc.Dropdown(
                id='sel_compare',
                options=list(map(lambda c: {'label': c, 'value': c}, selectable_columns)),
            )
        ], style={'width': '25%', 'float': 'left', 'display': 'inline-block'}),
    ]),

    html.Div([
        html.H3('Plot'),
        dcc.Graph(id='1d-graph'),
        html.Div(list(map(lambda t: html.Div(
            [html.H4(t[0]), t[1]]), zip(sliders, selectable_columns))))
    ], style={'width': '48%', 'display': 'inline-block'}),

    html.Div([
        html.H3('Model'),
        dcc.Graph(id='model-graph'),
        html.P(id='model'),
    ], style={'width': '48%', 'float': 'right', 'display': 'inline-block'}),

    html.Div([], style={'margin-top': '4em'})
])


def generate_slider_updates():
    def update_slider(slider_column, *args):
        return any(map(lambda x: x == slider_column, args))

    for slider_id, slider_col in zip(slider_names, selectable_columns):
        app.callback(
            Output(slider_id, 'disabled'),
            [Input('sel_var1', 'value'), Input('sel_compare', 'value'), Input('sel_repeat', 'value')]
        )(partial(update_slider, slider_col))


generate_slider_updates()


#@app.callback(Output('model-graph', 'figure'),
#              [Input('sel_var1', 'value'), Input('sel_metric', 'value'),
#               Input('sel_compare', 'value'), Input('sel_repeat', 'value'), Input('model', 'children')]
#              + [Input(sid, 'value') for sid in slider_names])
#def update_model_graph(sel_var1, sel_metric, sel_compare, sel_repeat, model, *args):
    #pass

@app.callback(Output('model', 'children'),
              [Input('sel_var1', 'value'), Input('sel_metric', 'value'),
               Input('sel_compare', 'value'), Input('sel_repeat', 'value')]
              + [Input(sid, 'value') for sid in slider_names])
@cache.memoize()
def update_model(sel_var1, sel_metric, sel_compare, sel_repeat, *args):
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../csv2extrap.py')

    # prevent variable and metric to be null
    if sel_var1 is None:
        sel_var1 = selectable_columns[0]
    if sel_metric is None:
        sel_metric = metric_columns[0]

    def create_model(additional_filters=list()):
        try:
            _, tmp_file_in = tempfile.mkstemp()
            call_params = ['python3', path, csv_file_path, tmp_file_in, '-v', sel_var1, '-m', sel_metric]

            # handle fixed columns
            filters = []
            for col, val in zip(selectable_columns, args):
                if col not in [sel_var1, sel_repeat, sel_compare]:
                    filters.append("%s=%s" % (col, val))

            call_params += ['-f', " ".join(filters + additional_filters)]

            # handle repeat column
            if sel_repeat is None:
                call_params.append('--single-measurement')
            else:
                call_params += ['-r', sel_repeat]

            subprocess.check_call(call_params)

            _, tmp_file_out = tempfile.mkstemp()
            subprocess.check_call(['/opt/extrap/bin/extrap-modeler', 'input', tmp_file_in, '-o', tmp_file_out])
            model_summary = subprocess.check_output(['/opt/extrap/bin/extrap-print', tmp_file_out]).decode("utf-8")

            print(model_summary)

            return re.search(r'model: (.+)\n', model_summary).group(1)
        except subprocess.CalledProcessError:
            return None

    models = []
    if sel_compare is None:
        models.append(create_model())
    else:
        for cmp_val in df[sel_compare].unique():
            models.append(create_model(['%s=%s' % (sel_compare, cmp_val)]))

    return '; '.join(models)


@app.callback(Output('1d-graph', 'figure'),
              [Input('sel_var1', 'value'), Input('sel_metric', 'value'),
               Input('sel_compare', 'value'), Input('sel_repeat', 'value')]
              + [Input(sid, 'value') for sid in slider_names])
def update_figure(sel_var1, sel_metric, sel_compare, sel_repeat, *args):
    # filtering
    filtered_df = df
    for col, val in zip(selectable_columns, args):
        if col in [sel_var1, sel_metric, sel_compare, sel_repeat]:
            continue
        filtered_df = filtered_df[df[col] == val]

    if sel_var1 is None:
        sel_var1 = selectable_columns[0]
    if sel_metric is None:
        sel_metric = metric_columns[1]

    data_list = []
    mode = 'lines+markers' if sel_repeat is None else 'markers'  # TODO Median line if showing multiple repeats?

    if sel_compare is not None:
        split_dfs = [frame for frame in filtered_df.groupby(sel_compare)]

        for region, frame in split_dfs:
            d = go.Scatter(
                x=frame[sel_var1],
                y=frame[sel_metric],
                mode=mode,
                name=sel_compare + ': ' + str(region),
            )
            data_list.append(d)
    else:
        data_list = [
            go.Scatter(
                x=filtered_df[sel_var1],
                y=filtered_df[sel_metric],
                mode=mode,
            )]

    return {
        'data': data_list,
        'layout': go.Layout(
            xaxis={'title': sel_var1},
            yaxis={'title': sel_metric},
            margin={'l': 40, 'b': 40, 't': 10, 'r': 0},
            hovermode='closest'
        )
    }


if __name__ == '__main__':
    app.run_server(debug=True)
