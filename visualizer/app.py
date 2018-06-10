# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output

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


# def update_slider(Output(''))

@app.callback(Output('1d-graph', 'figure'),
              [Input('sel_var1', 'value'), Input('sel_metric', 'value'), Input('sel_compare', 'value')]
              + [Input(sid, 'value') for sid in slider_names])
def update_figure(sel_var1, sel_metric, sel_compare, *args):
    # sliders[selectable_columns.index(sel_var1)].disabled = True

    # filtering
    selected = [c for c in selectable_columns if c != 2]
    selected_cutoff = args[1]
    filtered_df = df[df.cutoff == selected_cutoff]

    print(filtered_df)
    return {
        'data': [go.Scatter(
            x=filtered_df['density'],
            y=filtered_df['time'],
            mode='markers',
        )],
        'layout': go.Layout(
            xaxis={'title': 'Density'},
            yaxis={'title': 'Time'},
            margin={'l': 40, 'b': 40, 't': 10, 'r': 0},
            hovermode='closest'
        )
    }


if __name__ == '__main__':
    app.run_server(debug=True)
