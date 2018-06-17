#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pickle

import base64
import dash
import dash_html_components as html
import os
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from flask_caching import Cache
from functools import partial

from md_perfmod.models import comparison
from md_perfmod.visualizer import graphs
from md_perfmod.visualizer import model_creation
from md_perfmod.visualizer.layout import layout

csv_file_path = os.path.relpath('../../ls1-bench4.csv')
df = pd.read_csv(csv_file_path)

app = dash.Dash()
cache = Cache(app.server, config={'CACHE_TYPE': 'simple'})

selectable_columns = []
selectable_columns_values = []
metric_columns = []

for c in df.columns:
    unique_val = df[c].unique()
    if 1 < len(unique_val) < len(df) / 2:
        selectable_columns.append(c)
        selectable_columns_values.append(unique_val)
    elif 1 < len(unique_val):
        metric_columns.append(c)

slider_names = [('slider%i' % i) for i in range(len(selectable_columns))]

app.layout = layout(2, selectable_columns, selectable_columns_values, metric_columns)


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


@app.callback(Output('model-table', 'children'), [Input('models', 'children')])
def update_model_table(models_json):
    models = decode(models_json)

    if len(models) == 0:
        raise ValueError("No models to create table")

    data = list(map(lambda m: (m.name, m.model_str, m.adj_r2), models))
    table = pd.DataFrame(data, columns=['Label', 'Model', 'Adjusted R^2'])
    return generate_table(table)


def get_bounds(variable):
    ix = selectable_columns.index(variable)
    return min(selectable_columns_values[ix]), max(selectable_columns_values[ix])


@app.callback(Output('combined_model-table', 'children'),
              [Input('models', 'children'), Input('combined_models', 'children')])
def update_combined_model_table(models_json, combined_models_json):
    models = decode(models_json)
    combined_models = decode(combined_models_json)

    if len(models) == 0:
        raise ValueError("No models to create table")

    if len(combined_models) == 0:
        return generate_table(pd.DataFrame())

    def create_table_data(model, model_combined):
        name = model.name
        model_str = model_combined.model_str

        bounds = list(map(get_bounds, model_combined.variables))

        a = model.integrate(*bounds)
        b = model_combined.integrate(*bounds)
        error = abs(a - b)
        return name, model_str, error

    data = list(map(lambda m: create_table_data(m[0], m[1]), zip(models, combined_models)))
    table = pd.DataFrame(data, columns=['Label', 'Model', 'Error to 2D model'])
    return generate_table(table)


@app.callback(Output('classification-table', 'children'),
              [Input('models', 'children'), Input('combined_models', 'children')])
def update_classification_table(models_json, combined_models_json):
    models = decode(models_json)
    combined_models = decode(combined_models_json)

    if len(models) <= 1 or len(combined_models) <= 1:
        return generate_table(pd.DataFrame())

    bounds = list(map(get_bounds, models[0].variables))

    n_samples = 53
    error, classified_corr, min_err, max_err = comparison.calculate_error(models, combined_models, *bounds,
                                                                          n_samples=n_samples, rel=True)

    data = [(100 * (1 - classified_corr), error, min_err, max_err)]
    table = pd.DataFrame(data,
                         columns=['Wrongly classified samples (percent)', 'Avg. difference to real classification',
                                  'Min error', 'Max error'])
    return generate_table(table)


def generate_slider_updates():
    def update_slider(slider_column, *args):
        return any(map(lambda x: x == slider_column, args))

    for slider_id, slider_col in zip(slider_names, selectable_columns):
        app.callback(
            Output(slider_id, 'disabled'),
            [Input('sel_var1', 'value'), Input('sel_var2', 'value'), Input('sel_compare', 'value'),
             Input('sel_repeat', 'value')]
        )(partial(update_slider, slider_col))


generate_slider_updates()


@app.callback(Output('model-graph', 'figure'),
              [Input('sel_var1', 'value'), Input('sel_var2', 'value'), Input('sel_metric', 'value'),
               Input('sel_compare', 'value'), Input('sel_repeat', 'value'), Input('models', 'children')]
              + [Input(sid, 'value') for sid in slider_names])
def update_model_graph(sel_var1, sel_var2, sel_metric, sel_compare, sel_repeat, model_json, *args):
    if sel_var1 is None or sel_metric is None:
        raise ValueError("Nothing selected")

    models = decode(model_json)

    # filtering
    filtered_df = df
    for col, val in zip(selectable_columns, args):
        if col in [sel_var1, sel_var2, sel_metric, sel_compare, sel_repeat]:
            continue
        if val < 0:
            val = df[col].unique()[val + len(df[col].unique())]
        filtered_df = filtered_df[filtered_df[col] == val]

    bounds = [(df[sel_var1].min(), df[sel_var1].max())]
    if sel_var2 is not None:
        bounds.append((df[sel_var2].min(), df[sel_var2].max()))
        if sel_compare is not None:
            data_list = graphs.two_d_graph_multi(models, bounds, filtered_df, sel_var1, sel_var2, sel_metric,
                                                 sel_compare)
        else:
            data_list = graphs.two_d_graph(models, bounds, filtered_df, sel_var1, sel_var2, sel_metric)
    else:
        if sel_compare is not None:
            data_list = graphs.one_d_graph_multi(models, bounds, filtered_df, sel_var1, sel_metric, sel_compare)
        else:
            data_list = graphs.one_d_graph(models, bounds, filtered_df, sel_var1, sel_metric)

    # TODO Plot combined models
    return {
        'data': data_list,
        'layout': go.Layout(
            xaxis={'title': sel_var1},
            yaxis={'title': sel_metric},
            margin={'l': 40, 'b': 40, 't': 10, 'r': 0},
            hovermode='closest'
        )
    }


def encode(obj):
    return base64.encodebytes(pickle.dumps(obj)).decode('ascii')


def decode(json):
    return pickle.loads(base64.decodebytes(json.encode('ascii')))


@app.callback(Output('models', 'children'),
              [Input('sel_var1', 'value'), Input('sel_var2', 'value'), Input('sel_metric', 'value'),
               Input('sel_compare', 'value'), Input('sel_repeat', 'value')]
              + [Input(sid, 'value') for sid in slider_names])
def update_model_wrap(sel_var1, sel_var2, sel_metric, sel_compare, sel_repeat, *slider_vals):
    return update_model(sel_var1, sel_var2, sel_metric, sel_compare, sel_repeat, *slider_vals)


@cache.memoize()
def update_model(sel_var1, sel_var2, sel_metric, sel_compare, sel_repeat, *slider_vals):
    # variable and metric must be selected
    if sel_var1 is None or sel_metric is None:
        return encode(list())

    if sel_compare is None:
        comp_values = None
    else:
        comp_values = df[sel_compare].unique()

    fixed = dict(
        filter(lambda s: s[0] not in [sel_var1, sel_var2, sel_metric, sel_compare],
               zip(selectable_columns, slider_vals)))

    for k, v in fixed.items():
        if v < 0:
            col = df[k].unique()
            fixed[k] = col[v + len(col)]

    variables = [sel_var1]
    if sel_var2 is not None:
        variables.append(sel_var2)

    models = model_creation.create(csv_file_path, variables, sel_metric, sel_repeat, sel_compare, comp_values, fixed)

    return encode(models)


@app.callback(Output('combined_models', 'children'),
              [Input('sel_var1', 'value'), Input('sel_var2', 'value'), Input('sel_metric', 'value'),
               Input('sel_compare', 'value'), Input('sel_repeat', 'value')]
              + [Input(sid, 'value') for sid in slider_names])
@cache.memoize()
def update_combined_model(sel_var1, sel_var2, sel_metric, sel_compare, sel_repeat, *slider_vals):
    if sel_var1 is None or sel_var2 is None or sel_metric is None:
        return encode(list())

    def mid_val(ll):  # similar to median, when even number of values takes the larger 'middle' value
        sl = sorted(ll)
        item = None
        while len(sl) >= 2:
            item = sl.pop()
            sl.pop(0)
        if len(sl) == 1:
            return sl[0]
        else:
            return item

    # one d models for single var with other vars fixed
    def one_d_model(variable, others):
        fixed = list(slider_vals)
        for other in others:
            col_ix = selectable_columns.index(other)
            fixed[col_ix] = mid_val(selectable_columns_values[col_ix])
        models = update_model(variable, None, sel_metric, sel_compare, sel_repeat, *fixed)
        return decode(models)

    variables = [sel_var1, sel_var2]
    single_models = list(map(lambda v: one_d_model(v, [x for x in variables if x != v]), variables))
    combined_models = list(map(lambda m: comparison.combine(*m, combined_name=m[0].name), zip(*single_models)))
    return encode(combined_models)


if __name__ == '__main__':
    app.run_server(debug=True)
