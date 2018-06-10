# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output
from functools import partial

df = pd.read_csv('../ls1-bench1.csv')

app = dash.Dash()

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
                value=selectable_columns[1]
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


@app.callback(Output('1d-graph', 'figure'),
              [Input('sel_var1', 'value'), Input('sel_metric', 'value'),
               Input('sel_compare', 'value'), Input('sel_repeat', 'value')]
              + [Input(sid, 'value') for sid in slider_names])
def update_figure(sel_var1, sel_metric, sel_compare, sel_repeat, *args):
    # sliders[selectable_columns.index(sel_var1)].disabled = True

    # filtering
    filtered_df = df
    for col, val in zip(selectable_columns, args):
        if col in [sel_var1, sel_metric, sel_compare, sel_repeat]:
            continue

        print(col, val)
        filtered_df = filtered_df[df[col] == val]

    print(filtered_df)

    if sel_var1 is None:
        sel_var1=selectable_columns[0]
    if sel_metric is None:
        sel_metric=metric_columns[1]

    data_list = []
    mode = 'lines+markers' if sel_repeat is None else 'markers'

    if sel_compare is not None:
        split_dfs = [frame for frame in filtered_df.groupby(sel_compare)]


        for region, frame in split_dfs:
            d = go.Scatter(
                x=frame[sel_var1],
                y=frame[sel_metric],
                mode=mode,
                name=region,
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
