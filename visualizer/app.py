# -*- coding: utf-8 -*-
import json
import subprocess

import colorlover as cl
import dash
import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import os
import pandas as pd
import plotly.graph_objs as go
import re
import tempfile
from dash.dependencies import Input, Output
from flask_caching import Cache
from functools import partial
from pathos.multiprocessing import ProcessingPool as Pool
from py_expression_eval import Parser

csv_file_path = os.path.relpath('../ls1-bench4.csv')
df = pd.read_csv(csv_file_path)

app = dash.Dash()
cache = Cache(app.server, config={'CACHE_TYPE': 'simple'})

sliders = []
slider_names = []


def create_marks(l):
    result = dict()
    for i, e in enumerate(l):
        if isinstance(e, str):
            result[-len(l) + i] = e
        elif e % 1 == 0:
            result[int(e)] = str(e)
        else:
            result[e] = str(e)
    return result


def add_slider(column):
    sid = 'slider%i' % len(sliders)
    col = df[column].unique()
    minv = -len(col) if isinstance(col[0], str) else col.min()
    maxv = -1 if isinstance(col[0], str) else col.max()
    sliders.append(dcc.Slider(
        id=sid,
        min=minv,
        max=maxv,
        value=minv,
        step=None,
        updatemode='drag',
        marks=create_marks(col),
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
        html.Table(id='model-table'),
    ], style={'width': '48%', 'float': 'right', 'display': 'inline-block'}),

    html.Div([], style={'margin-top': '4em'}),
    html.Div(id='models', style={'display': 'none'}),
])


def generate_table(dataframe, max_rows=None):
    if max_rows is None:
        max_rows = len(dataframe)
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in dataframe.columns])] +

        # Body
        [html.Tr([
            html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
        ]) for i in range(min(len(dataframe), max_rows))]
    )


@app.callback(Output('model-table', 'children'), [Input('sel_compare', 'value'), Input('models', 'children')])
def update_model_table(compare, models_json):
    models = json.loads(models_json)

    if compare is not None:
        data = list(zip(df[compare].unique(), models))
    else:
        data = [('model', models[0])]
    table = pd.DataFrame(data, columns=['Label', 'Model'])
    return generate_table(table)


def generate_slider_updates():
    def update_slider(slider_column, *args):
        return any(map(lambda x: x == slider_column, args))

    for slider_id, slider_col in zip(slider_names, selectable_columns):
        app.callback(
            Output(slider_id, 'disabled'),
            [Input('sel_var1', 'value'), Input('sel_compare', 'value'), Input('sel_repeat', 'value')]
        )(partial(update_slider, slider_col))


generate_slider_updates()


@app.callback(Output('model-graph', 'figure'),
              [Input('sel_var1', 'value'), Input('sel_metric', 'value'),
               Input('sel_compare', 'value'), Input('sel_repeat', 'value'), Input('models', 'children')]
              + [Input(sid, 'value') for sid in slider_names])
def update_model_graph(sel_var1, sel_metric, sel_compare, sel_repeat, model_json, *args):
    parser = Parser()
    models = json.loads(model_json)

    data_list = []
    x_vals = np.linspace(df[sel_var1].min(), df[sel_var1].max(), 50)

    def sample_points(model_):
        m = parser.parse(model_)
        points = []
        for x in x_vals:
            points.append(m.evaluate({sel_var1: x}))
        return points

    # filtering
    filtered_df = df
    for col, val in zip(selectable_columns, args):
        if col in [sel_var1, sel_metric, sel_compare, sel_repeat]:
            continue
        if val < 0:
            val = df[col].unique()[val + len(df[col].unique())]
        filtered_df = filtered_df[df[col] == val]

    if sel_var1 is None:
        sel_var1 = selectable_columns[0]
    if sel_metric is None:
        sel_metric = metric_columns[1]

    if sel_compare is not None:

        split_dfs = [frame for frame in filtered_df.groupby(sel_compare)]

        num_colors = len(models) + len(split_dfs)

        for i, ((region, frame), model) in enumerate(zip(split_dfs, models)):
            options_m = dict(
                x=x_vals,
                y=sample_points(model),
                name='%s: %s (model)' % (sel_compare, str(region)),
                legendgroup=region,
            )

            options_d = dict(
                x=frame[sel_var1],
                y=frame[sel_metric],
                mode='markers',
                name='%s: %s (data)' % (sel_compare, str(region)),
                legendgroup=region,
            )

            if 3 < num_colors < 13:
                colors = cl.scales[str(num_colors)]['qual']['Paired']
                options_m['line'] = dict(color=colors[2 * i])
                options_d['marker'] = dict(color=colors[2 * i + 1])
            elif num_colors < 25:
                colors = cl.scales[str(num_colors)]['qual']['Set1']
                options_m['line'] = dict(color=colors[i])
                options_d['marker'] = dict(color=colors[i])

            m = go.Scatter(options_m)
            d = go.Scatter(options_d)
            data_list += [m, d]
    else:
        data_list += [go.Scatter(
            x=x_vals,
            y=sample_points(models[0]),
            name='model',
            legendgroup='1',
        )]
        data_list += [
            go.Scatter(
                x=filtered_df[sel_var1],
                y=filtered_df[sel_metric],
                mode='markers',
                name='data',
                legendgroup='1',
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


@app.callback(Output('models', 'children'),
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

    models = []
    if sel_compare is None:
        model = create_model_wrap(path, sel_var1, sel_metric, sel_repeat, sel_compare, args)()
        if model is not None:
            # TODO Edit parsing library instead of replacing here
            model = model.replace('log2^1', 'log2')
            models.append(model)
    else:
        filters = list(map(lambda x: ['%s=%s' % (sel_compare, x)], df[sel_compare].unique()))

        with Pool(len(filters)) as p:
            models = p.map(create_model_wrap(path, sel_var1, sel_metric, sel_repeat, sel_compare, args), filters)
            print("Foo")

        models = list(map(lambda x: x.replace('log2^1', 'log2') if x is not None else None, models))

    return json.dumps(models)


def create_model_wrap(path, sel_var1, sel_metric, sel_repeat, sel_compare, args):
    def create_model(additional_filters=list()):
        try:
            _, tmp_file_in = tempfile.mkstemp()
            call_params = ['python3', path, csv_file_path, tmp_file_in, '-v', sel_var1, '-m', sel_metric]

            # handle fixed columns
            filters = []
            for col, val in zip(selectable_columns, args):
                if val < 0:
                    val = df[col].unique()[val + len(df[col].unique())]
                if col not in [sel_var1, sel_repeat, sel_compare]:
                    filters.append("%s=%s" % (col, val))

            call_params += ['-f'] + filters + additional_filters

            # handle repeat column
            if sel_repeat is None:
                call_params.append('--single-measurement')
            else:
                call_params += ['-r', sel_repeat]

            subprocess.check_call(call_params)

            _, tmp_file_out = tempfile.mkstemp()
            subprocess.check_call(['/opt/extrap/bin/extrap-modeler', 'input', tmp_file_in, '-o', tmp_file_out],
                                  timeout=8)
            model_summary = subprocess.check_output(['/opt/extrap/bin/extrap-print', tmp_file_out]).decode("utf-8")

            return re.search(r'model: (.+)\n', model_summary).group(1)
        except subprocess.CalledProcessError:
            return None

    return create_model


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
        if val < 0:
            val = df[col].unique()[val + len(df[col].unique())]
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
