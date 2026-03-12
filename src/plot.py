import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import csv
from os import read


def display_profit(df_optim, name =""):
    """
    Displays daily profits 
    """

    days = pd.to_datetime(df_optim["timestamp"].apply(
        lambda x: datetime.datetime(x.year, x.month, x.day)), utc=True).unique()
    daily_profit = []

    for i in range(len(days)):
        daily_profit.append(df_optim.hourly_profit.iloc[i*24:(i+1)*24].sum())

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(x=df_optim.timestamp, y=df_optim.price_euros_wh*10**6, name='Price (EUR/MWh)', line={"shape": "hv"}, showlegend=False),
                  secondary_y=False)

    fig.add_trace(go.Bar(x=days, y=daily_profit, name="Daily profit (EUR)", offset=2, showlegend=False, opacity=0.5),
                  secondary_y=True)

    fig.update_layout(
        title_text="Daily profit<br>Total: {} EUR<br>Mean: {} EUR".format(
            int(sum(daily_profit)), int(np.mean(daily_profit)))
    )

    fig.update_xaxes(title_text="Hour")
    fig.update_yaxes(title_text="Price (EUR/MWh)", secondary_y=False,title_font_color="blue")
    fig.update_yaxes(title_text="Daily profit (EUR)", secondary_y=True,title_font_color="red")

    fig.update_layout(bargap=0.)
    fig.write_html("out/profit_{}.html".format(name))
    fig.show()


def display_schedule(df_to_show, name = "", start=None, end=None, add_pv_and_load=False):
    """
    Displays charge schedule between start datetime and end datetime 
    """

    mask = None

    if start : 
        df_to_show = df_to_show[(df_to_show.timestamp >= start)]
  
    if end : 
        df_to_show = df_to_show[(df_to_show.timestamp < end)]

    
    if add_pv_and_load:
        variables_to_show = ["pv_to_grid", "pv_to_load", "pv_to_bess", "grid_to_load", "grid_to_bess", "bess_to_load", "bess_to_grid"]

        pv_colors = {"pv_to_grid":"#2ca02c","pv_to_load":"#98df8a","pv_to_bess":"#66c2a5"}
        load_colors = {"pv_to_load":pv_colors["pv_to_load"],"grid_to_load":"#ffd269","bess_to_load":"#fef576"}
        grid_colors = {"grid_to_bess":"#ff9328","bess_to_grid":"#62d0d8","grid_to_load":"#ffd269","pv_to_grid":"#2ca02c"}
        
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pv = make_subplots(specs=[[{"secondary_y": True}]])
        fig_load = make_subplots(specs=[[{"secondary_y": True}]])
        fig_grid = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig1.update_yaxes(title_text="SOC (%)", secondary_y=True)
        fig2.update_yaxes(title_text="Power Flow (kW)", secondary_y=True)
        fig_pv.update_yaxes(title_text="Power Flow (kW)", secondary_y=True)
        fig_load.update_yaxes(title_text="Power Flow (kW)", secondary_y=True)
        fig_grid.update_yaxes(title_text="Power Flow (kW)", secondary_y=True)        
        
        fig1.update_layout(
            title_text="<b>Charge Schedule</b><br>Please use the buttons below to set the data range."
        )
        fig2.update_layout(
            title_text="<b>Power Flows Between Devices</b><br>Please use the buttons below to set the data range."
        )
        fig_pv.update_layout(
            title_text="<b>Photovoltaic Production</b><br>Please use the buttons below to set the data range."
        )
        fig_load.update_layout(
            title_text="<b>Load Consumption</b><br>Please use the buttons below to set the data range."
        )
        fig_grid.update_layout(
            title_text="<b>Grid Power Flow</b><br>Please use the buttons below to set the data range."
        )

        

        fig1.add_trace(go.Scatter(x=df_to_show.timestamp, y=df_to_show.price_euros_wh*10**6, name='Price (EUR/MWh)', line={"shape": "hv"}, showlegend=True),
                    secondary_y=False)
        fig1.add_trace(
            go.Scatter(x=df_to_show.timestamp, y=df_to_show["SOC"] * 100, name="SOC (%)", showlegend=True), secondary_y=True)

        fig2.add_trace(go.Scatter(x=df_to_show.timestamp, y=df_to_show.price_euros_wh*10**6, name='Price (EUR/MWh)', line={"shape": "hv"}, showlegend=True),
                        secondary_y=False)

        fig_pv.add_trace(go.Scatter(x=df_to_show.timestamp, y=df_to_show.price_euros_wh*10**6, name='Price (EUR/MWh)', line={"shape": "hv"}, showlegend=True),
                        secondary_y=False)
        fig_pv.add_trace(go.Scatter(x=df_to_show.timestamp, y=df_to_show.pv_prod / 1000, name='PV Production (kWh)', showlegend=True),
                        secondary_y=True)
        
        fig_load.add_trace(go.Scatter(x=df_to_show.timestamp, y=df_to_show.price_euros_wh*10**6, name='Price (EUR/MWh)', line={"shape": "hv"}, showlegend=True),
                        secondary_y=False)
        fig_load.add_trace(go.Scatter(x=df_to_show.timestamp, y=df_to_show.load_demand / 1000, name='Load Consumption (kWh)', showlegend=True),
                        secondary_y=True)
        
        fig_grid.add_trace(go.Scatter(x=df_to_show.timestamp, y=df_to_show.price_euros_wh*10**6, name='Electricity Price (EUR / MWh)', line={"shape": "hv"}, showlegend=True),
                        secondary_y=False)
        fig_grid.add_trace(go.Scatter(x=df_to_show.timestamp, y=df_to_show.pv_prod / 1000, name='PV Production (kWh)', showlegend=True),
                        secondary_y=True)
        fig_grid.add_trace(go.Scatter(x=df_to_show.timestamp, y=df_to_show.load_demand / 1000, name='Load Consumption (kWh)', showlegend=True),
                        secondary_y=True)
        
        
        for variable in variables_to_show:
            if variable.startswith("pv_"):
                c = pv_colors.get(variable, "#2ca02c")
                fig_pv.add_trace(
                    go.Bar(x=df_to_show.timestamp, y=df_to_show[variable] / 1000, name=variable,
                           marker_color=c, offsetgroup="pv", legendgroup="pv"),
                    secondary_y=True)
            if variable.endswith("_load"):
                c = load_colors.get(variable, "#ff7f0e")
                fig_load.add_trace(
                    go.Bar(x=df_to_show.timestamp, y=df_to_show[variable] / 1000, name=variable,
                           marker_color=c, offsetgroup="load", legendgroup="load"),
                    secondary_y=True)
            if variable.startswith("grid_"):
                c = grid_colors.get(variable, "#7f7f7f")
                fig_grid.add_trace(
                    go.Bar(x=df_to_show.timestamp, y=df_to_show[variable] / 1000, name=variable,
                           marker_color=c, offsetgroup="grid", legendgroup="grid"),
                    secondary_y=True)
            if variable.endswith("_grid"):
                c = grid_colors.get(variable, "#7f7f7f")
                fig_grid.add_trace(
                    go.Bar(x=df_to_show.timestamp, y=-df_to_show[variable] / 1000, name=variable,
                           marker_color=c, offsetgroup="grid", legendgroup="grid"),
                    secondary_y=True)
            
            fig2.add_trace(
                go.Scatter(x=df_to_show.timestamp, y=df_to_show[variable] / 1000, name=variable, showlegend=True, marker_color=c), secondary_y=True)

            # ensure stacking behavior by offsetgroup
            fig_pv.update_layout(barmode="stack")
            fig_load.update_layout(barmode="stack")
            fig_grid.update_layout(barmode="stack")
            

            # for h in df_to_show.index[np.sign(df_to_show.schedule).diff() != 0]:

            #     if (df_to_show.schedule[h] == 0 and not color) or (df_to_show.schedule[h] > 0 and color == "green") or (df_to_show.schedule[h] < 0 and color == "red"):
            #         continue

            #     elif df_to_show.schedule[h] == 0 and color:
            #         shapes.append(dict(type="rect", x0=df_to_show.timestamp[start], y0=1, x1=df_to_show.timestamp[h],
            #                     y1=100,  yref="y2", fillcolor=color, opacity=0.25, line_width=0))
            #         color = None

            #     elif df_to_show.schedule[h] > 0 and color == "red":
            #         shapes.append(dict(type="rect", x0=df_to_show.timestamp[start], y0=1,
            #                     x1=df_to_show.timestamp[h], y1=100, yref="y2", fillcolor=color, opacity=0.25, line_width=0))
            #         start = h
            #         color = "green"

            #     elif df_to_show.schedule[h] > 0 and not color:
            #         start = h
            #         color = "green"

            #     elif df_to_show.schedule[h] < 0 and color == "green":
            #         shapes.append(dict(type="rect", x0=df_to_show.timestamp[start], y0=1,
            #                     x1=df_to_show.timestamp[h], y1=100, yref="y2", fillcolor=color, opacity=0.25, line_width=0))
            #         start = h
            #         color = "red"

            #     elif df_to_show.schedule[h] < 0 and not color:
            #         start = h
            #         color = "red"

            # Add range slider
        for fig in [fig1, fig2, fig_pv, fig_load, fig_grid]:
            fig.update_layout(
                xaxis=dict(
                    rangeselector=dict(
                        buttons=list([
                            dict(step="all"),
                            dict(count=1,
                                label="1m",
                                step="month",
                                stepmode="backward"),
                            dict(count=2*7,
                                label="2w",
                                step="day",
                                stepmode="backward"),
                            dict(count=1*7,
                                label="1w",
                                step="day",
                                stepmode="backward"),
                            dict(count=2,
                                label="2d",
                                step="day",
                                stepmode="backward"),
                            dict(count=1,
                                label="1d",
                                step="day",
                                stepmode="backward"),

                        ])
                    ),
                    rangeslider=dict(
                        visible=True
                    ),
                    type="date"
                )
            )

            fig.update_xaxes(title_text="Date")
            fig.update_yaxes(title_text="Price (EUR/MWh)", secondary_y=False)

            fig.show()
            fig_name = fig.layout.title.text.split("<b>")[1].split("</b>")[0].lower().replace(" ", "_")
            fig.write_html(f"out/with_pv_and_load/{fig_name}_{name}.html")
    
    else:
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(go.Scatter(x=df_to_show.timestamp, y=df_to_show.price_euros_wh*10**6, name='Price (EUR/MWh)', line={"shape": "hv"}, showlegend=True),
                    secondary_y=False)
        
        fig.add_trace(
            go.Scatter(x=df_to_show.timestamp, y=df_to_show.SOC, name="SOC (%)", showlegend=True), secondary_y=True)

        color = None
        shapes = []
        

        for h in df_to_show.index[np.sign(df_to_show.schedule).diff() != 0]:

            if (df_to_show.schedule[h] == 0 and not color) or (df_to_show.schedule[h] > 0 and color == "green") or (df_to_show.schedule[h] < 0 and color == "red"):
                continue

            elif df_to_show.schedule[h] == 0 and color:
                shapes.append(dict(type="rect", x0=df_to_show.timestamp[start], y0=1, x1=df_to_show.timestamp[h],
                            y1=100,  yref="y2", fillcolor=color, opacity=0.25, line_width=0))
                color = None

            elif df_to_show.schedule[h] > 0 and color == "red":
                shapes.append(dict(type="rect", x0=df_to_show.timestamp[start], y0=1,
                            x1=df_to_show.timestamp[h], y1=100, yref="y2", fillcolor=color, opacity=0.25, line_width=0))
                start = h
                color = "green"

            elif df_to_show.schedule[h] > 0 and not color:
                start = h
                color = "green"

            elif df_to_show.schedule[h] < 0 and color == "green":
                shapes.append(dict(type="rect", x0=df_to_show.timestamp[start], y0=1,
                            x1=df_to_show.timestamp[h], y1=100, yref="y2", fillcolor=color, opacity=0.25, line_width=0))
                start = h
                color = "red"

            elif df_to_show.schedule[h] < 0 and not color:
                start = h
                color = "red"

        # Add range slider
        fig.update_layout(
            xaxis=dict(
                rangeselector=dict(
                    buttons=list([
                        dict(step="all"),
                        dict(count=1,
                            label="1m",
                            step="month",
                            stepmode="backward"),
                        dict(count=2*7,
                            label="2w",
                            step="day",
                            stepmode="backward"),
                        dict(count=1*7,
                            label="1w",
                            step="day",
                            stepmode="backward"),
                        dict(count=2,
                            label="2d",
                            step="day",
                            stepmode="backward"),
                        dict(count=1,
                            label="1d",
                            step="day",
                            stepmode="backward"),

                    ])
                ),
                rangeslider=dict(
                    visible=True
                ),
                type="date"
            )
        )

        fig.update_layout(
            shapes=shapes)

        fig.update_layout(
            title_text="Charge schedule.    Please use the buttons below to set the data range.<br>"
        )

        fig.update_xaxes(title_text="Date")
        fig.update_yaxes(title_text="Price (EUR/MWh)", secondary_y=False)
        fig.update_yaxes(title_text="SOC (%)", secondary_y=True)

        fig.show()
        fig.write_html("out/schedule_{}.html".format(name))




def get_stats(df_pred, df_optim, name='') :
    stats = {'prediction_mae':10**6 * abs(df_pred.price_euros_wh-df_pred.price_forecast).mean(),
                 'relative_diff_profits':-100*(df_optim.hourly_profit.sum() - df_pred.hourly_profit.sum())/df_optim.hourly_profit.sum(),
                 'daily_profit_avg_pred':24*df_pred.hourly_profit.sum()/len(df_pred),
                 'avg_daily_profit_optim': 24*df_optim.hourly_profit.sum()/len(df_optim),
                 'n_cycles_pred':df_pred.n_cycles.iloc[-1],
                 "n_cycles_optim":df_optim.n_cycles.iloc[-1]}
    
    with open("out/stats_{}.csv".format(name),"w") as file:
        for value,item in stats.items():
            file.write(str(value)+","+str(item)+"\n")
            print(value,item)
