from itertools import product

import colorlover as cl
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
    samples = samples.reshape(-1)
    x, y = zip(*product(x[0], x[1]))
    options_m = dict(
        x=x,
        y=y,
        z=samples,
        name='model',
        showscale=False,
        opacity=0.9,
    )
    options_d = dict(
        x=filtered_df[sel_var1],
        y=filtered_df[sel_var2],
        z=filtered_df[sel_metric],
        mode='markers',
        name='data',
    )

    return [go.Mesh3d(options_m), go.Scatter3d(options_d)]


def two_d_graph_multi(models, bounds, filtered_df, sel_var1, sel_var2, sel_metric, sel_compare):
    data_list = []
    split_dfs = [frame for frame in filtered_df.groupby(sel_compare)]

    num_colors = len(models) + len(split_dfs)
    for i, (region, frame) in enumerate(split_dfs):
        name = str(region)
        model = next(m for m in models if str(m.name) == name)
        x, samples = model.sample(*bounds)
        samples = samples.reshape(-1)
        x, y = zip(*product(x[0], x[1]))
        options_m = dict(
            x=x,
            y=y,
            z=samples,
            name='%s: %s (model)' % (sel_compare, name),
            legendgroup=region,
            opacity=1,
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
            options_m['color'] = colors[2 * i]
            options_d['marker'] = dict(color=colors[2 * i + 1])
        elif num_colors < 25:
            colors = cl.scales[str(num_colors)]['qual']['Set1']
            options_m['color'] = colors[i]
            options_d['marker'] = dict(color=colors[i])

        data_list += [go.Mesh3d(options_m), go.Scatter3d(options_d)]

    return data_list
