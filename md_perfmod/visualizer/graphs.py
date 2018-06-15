import colorlover as cl
import numpy as np
import plotly.graph_objs as go


def one_d_graph(models, bounds, filtered_df, sel_var1, sel_metric):
    x, samples = models[0].sample(*bounds)
    options_m = dict(
        x=x[0],
        y=samples,
        name='model',
        legendgroup='1',
    )
    options_d = dict(
        x=filtered_df[sel_var1],
        y=filtered_df[sel_metric],
        mode='markers',
        name='data',
        legendgroup='1',
    )

    return [go.Scatter(options_m), go.Scatter(options_d)]


def one_d_graph_multi(models, bounds, filtered_df, sel_var1, sel_metric, sel_compare):
    data_list = []
    split_dfs = [frame for frame in filtered_df.groupby(sel_compare)]

    num_colors = len(models) + len(split_dfs)
    for i, (region, frame) in enumerate(split_dfs):
        name = str(region)
        model = next(m for m in models if str(m.name) == name)
        x, samples = model.sample(*bounds)
        options_m = dict(
            x=x[0],
            y=samples,
            name='%s: %s (model)' % (sel_compare, name),
            legendgroup=region,
        )

        options_d = dict(
            x=frame[sel_var1],
            y=frame[sel_metric],
            mode='markers',
            name='%s: %s (data)' % (sel_compare, name),
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

        data_list += [go.Scatter(options_m), go.Scatter(options_d)]

    return data_list


def two_d_graph(models, bounds, filtered_df, sel_var1, sel_var2, sel_metric):
    x, samples = models[0].sample(*bounds)
    options_m = dict(
        name='model',
        showlegend=True,
        mode='lines',
        line=dict(color='#1f77b4', width=3),
    )
    options_d = dict(
        x=filtered_df[sel_var1],
        y=filtered_df[sel_var2],
        z=filtered_df[sel_metric],
        mode='markers',
        marker=dict(color='#ff7f0e'),
        name='data',
    )

    return create_mesh(x, samples, options_m) + [go.Scatter3d(options_d)]


def create_mesh(x, samples, options_m):
    data_list = []
    x_grid, y_grid = np.meshgrid(x[0], x[1])
    for a, b, c in zip(x_grid, y_grid, samples):
        options_m['x'] = a
        options_m['y'] = b
        options_m['z'] = c
        data_list.append(go.Scatter3d(options_m))
        options_m['showlegend'] = False

    y_grid, x_grid = np.meshgrid(x[1], x[0])
    for a, b, c in zip(x_grid, y_grid, samples.T):
        options_m['x'] = a
        options_m['y'] = b
        options_m['z'] = c
        data_list.append(go.Scatter3d(options_m))

    return data_list


def two_d_graph_multi(models, bounds, filtered_df, sel_var1, sel_var2, sel_metric, sel_compare):
    data_list = []
    split_dfs = [frame for frame in filtered_df.groupby(sel_compare)]

    num_colors = len(models) + len(split_dfs)
    for i, (region, frame) in enumerate(split_dfs):
        name = str(region)
        model = next(m for m in models if str(m.name) == name)
        x, samples = model.sample(*bounds)
        options_m = dict(
            name='%s: %s (model)' % (sel_compare, name),
            mode='lines',
            line=dict(width=2),
            legendgroup=region,
        )

        options_d = dict(
            x=frame[sel_var1],
            y=frame[sel_var2],
            z=frame[sel_metric],
            mode='markers',
            name='%s: %s (data)' % (sel_compare, name),
            legendgroup=region,
        )

        if 3 < num_colors < 13:
            colors = cl.scales[str(num_colors)]['qual']['Paired']
            options_m['line'] = dict(color=colors[2 * i], width=3)
            options_d['marker'] = dict(color=colors[2 * i + 1])
        elif num_colors < 25:
            colors = cl.scales[str(num_colors)]['qual']['Set1']
            options_m['line'] = dict(color=colors[i], width=3)
            options_d['marker'] = dict(color=colors[i])

        data_list += [go.Scatter3d(options_d)] + create_mesh(x, samples, options_m)

    return data_list
