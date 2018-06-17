import dash_core_components as dcc
import dash_html_components as html


def combo_opts(cols):
    return list(map(lambda c: {'label': c, 'value': c}, cols))


def combo_box(name, hid, cols, num_boxes):
    return [html.Div([
        html.Label(name, htmlFor=hid),
        dcc.Dropdown(
            id=hid,
            options=combo_opts(cols),
        )
    ],
        style={'width': '%d%%' % (93 / num_boxes), 'float': 'left', 'margin': '0 1em'})
    ]


def slider_marks(l):
    result = dict()
    for i, e in enumerate(l):
        if isinstance(e, str):
            result[-len(l) + i] = e
        elif e % 1 == 0:
            result[int(e)] = str(e)
        else:
            result[e] = str(e)
    return result


def slider(name, hid, values):
    min_v = -len(values) if isinstance(values[0], str) else values.min()
    max_v = -1 if isinstance(values[0], str) else values.max()

    return html.Div([
        html.Label(name, htmlFor=hid),
        html.Div([
            dcc.Slider(
                id=hid,
                min=min_v,
                max=max_v,
                value=min_v,
                step=None,
                updatemode='drag',
                marks=slider_marks(values),
            )], style={'margin': '0 0 1.6em 0'}),
    ])


def layout(num_variables, selectable_columns, selectable_columns_values, metric_columns):
    cmb_boxes = []
    for i in range(1, num_variables + 1):
        cmb_boxes += combo_box('Variable %i' % i, 'sel_var%i' % i, selectable_columns, num_variables + 3)

    cmb_boxes += combo_box('Metric', 'sel_metric', metric_columns, num_variables + 3)
    cmb_boxes += combo_box('Compare', 'sel_compare', selectable_columns, num_variables + 3)
    cmb_boxes += combo_box('Repeat', 'sel_repeat', selectable_columns, num_variables + 3)

    sliders = []
    for i, col in enumerate(zip(selectable_columns, selectable_columns_values)):
        sliders.append(slider(col[0], 'slider%i' % i, col[1]))

    return html.Div(children=[
        html.H1('Benchmark visualization'),

        html.Div(cmb_boxes),

        html.Div([
            html.H3('Graph'),
            dcc.Graph(id='model-graph'),
            html.H5('Models'),
            html.Table(id='model-table'),
        ], style={'width': '49%', 'float': 'left', 'display': 'inline-block'}),
        html.Div([
            html.H3('Fixed values'),
            html.Div(
                sliders
            ),
            html.H5('Combined models'),
            html.Table(id='combined_model-table'),
            html.H5('Classification'),
            html.Table(id='classification-table'),
        ], style={'width': '48%', 'float': 'left', 'display': 'inline-block'}),

        html.Div([], style={'margin-top': '4em'}),
        html.Div(id='models', style={'display': 'none'}),
        html.Div(id='combined_models', style={'display': 'none'}),
    ])
