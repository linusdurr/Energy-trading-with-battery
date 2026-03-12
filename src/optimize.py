import pandas as pd
import numpy as np
from amplpy import AMPL, modules
import datetime 

import datetime 
import pandas as pd
import numpy as np
from amplpy import AMPL, modules
import datetime 

def run_simulation(bat, df, start, end, forecasted=True, frame_size=14, update_period=1, forecasting_model=None, add_pv_and_load=False, time_horizon=24):
    """
    Run a simulation starting from the start-th day of the dataframe.
    For every day of the simulation, a schedule is generated (either based on true prices or prediction) and different 
    metrics are recorded.
    We return a dataframe containing the results of the simulation
    """
    
    try :
        end = datetime.datetime.strptime(end, '%Y-%m-%d %H:%M:%S') - datetime.timedelta(hours=1)
        start_index = df.index.get_loc(df.index[df.timestamp==start][0]) 
        end_index = df.index.get_loc(df.index[df.timestamp==end][0])
    except : raise ValueError("The dataframe does not contain all the data between the start and end dates")
    start_df = start_index - 24 * frame_size if forecasted else start_index
    if  start_df < 0 : raise ValueError("The dataframe does not contain enough data for the price prediction relying on the {} last days to be computed".format(frame_size))
    
    df = df.iloc[start_df: end_index+1, :]
    n_hours = (end_index-start_df) + 1
    
    if  n_hours% 24 != 0:
        raise Exception(
            "The dataframe should contain only full days (24 hours)")


    bat.reset()  # start with a new battery, and get the max SOC change when charging and discharging
    G_c, G_d = bat.max_SOC_change_charge, bat.min_SOC_change_discharge

    n_cycles_list = np.zeros(n_hours)
    eff_list = np.zeros(n_hours)
    NEC_list = np.zeros(n_hours)
    price_forecast_list = np.zeros(n_hours)
    if add_pv_and_load :
        schedule = pd.DataFrame(index=df.index, columns=["pv_to_grid", "pv_to_load", "pv_to_bess", "grid_to_load", "grid_to_bess", "bess_to_grid", "bess_to_load", "SOC"])
    else :
        schedule = np.zeros(n_hours)


    # optimization done for each day :
    for i, day in enumerate(range((frame_size if forecasted else 0), (n_hours - time_horizon + 24)//24)):

        day_indices = slice(day*24, (day+time_horizon//24)*24)

        # if using forecasted prices, get new forecast evert update_period iterations :
        if forecasted and (i % update_period == 0):
            if forecasting_model :
                prices = forecasting_model(df.iloc[(day-frame_size)*24:day*24, :][0])
            else : prices = df.iloc[(day-frame_size)*24:day*24, :].groupby(
                df.timestamp.dt.hour).price_euros_wh.mean().to_numpy()
            

        # Otherwise, use the true prices for the current day
        if not forecasted:
            prices = df.iloc[day_indices].price_euros_wh.to_numpy()

        # get the variable grid cost
        vgc = df.vgc.iloc[day_indices].to_numpy()

        # get the fixed grid cost
        fgc = df.fgc.iloc[day_indices].to_numpy()

        # store battery state
        n_cycles_list[day_indices] = bat.n_cycles
        eff_list[day_indices] = bat.eff
        NEC_list[day_indices] = bat.NEC
        price_forecast_list[day_indices] = prices

        # get optimized schedule
        if add_pv_and_load:
            if "pv_prod" not in df.columns or "load_demand" not in df.columns:
                raise ValueError("If add_pv_and_load is True, pv_prod, load_demand and deg_cost should be provided")
            pv_prod = df.pv_prod.iloc[day_indices].to_numpy()
            load_demand = df.load_demand.iloc[day_indices].to_numpy()
            deg_cost = bat.price / bat.max_cycles

            if day == (frame_size if forecasted else 0) :
                SOC_init = bat.min_SOC
            else :
                SOC_init = daily_schedule["SOC.val"].iloc[23]

            daily_schedule = get_daily_schedule(prices, vgc, fgc, bat, G_c, G_d, add_pv_and_load=add_pv_and_load, pv_prod=pv_prod, load_demand=load_demand, deg_cost=[deg_cost], SOC_init=SOC_init, time_horizon=time_horizon)
            if day == (n_hours - time_horizon + 24)//24 - 1:
                schedule.iloc[day_indices] = daily_schedule
            else:
                schedule.iloc[slice(day*24, (day+1)*24)] = daily_schedule.iloc[:24, :]

            

        else:
            schedule[day_indices] = get_daily_schedule(
                prices, vgc, fgc, bat, G_c, G_d, add_pv_and_load=add_pv_and_load)

    if add_pv_and_load :
        df = df.assign(n_cycles=n_cycles_list,
                        eff=eff_list,
                        NEC=NEC_list,
                        price_forecast=price_forecast_list,
                        pv_to_grid=schedule["pv_to_grid"],
                        pv_to_load=schedule["pv_to_load"],
                        pv_to_bess=schedule["pv_to_bess"],
                        grid_to_load=schedule["grid_to_load"],
                        grid_to_bess=schedule["grid_to_bess"],
                        bess_to_grid=schedule["bess_to_grid"],
                        bess_to_load=schedule["bess_to_load"],
                        SOC=schedule["SOC"],
                        capacity=schedule["SOC"]*NEC_list
        )
    else:
        ## store simulation results 
        df = df.assign(n_cycles=n_cycles_list,
                    eff=eff_list, 
                    NEC=NEC_list,
                    price_forecast=price_forecast_list,
                    schedule=schedule,
                    capacity=np.hstack(
                        (np.array([0]), np.cumsum(schedule)[:-1])),
                    SOC=lambda x: 100 * x.capacity/x.NEC,
                    charge_energy=lambda x: x.schedule.mask(x.schedule < 0, 0), ## energy delivered to the battery
                    discharge_energy=lambda x: -
                    x.schedule.mask(x.schedule > 0, 0) * x.eff, ## energy obtained from the battery (taking into account the discharge efficiency)
                    electricity_revenue=lambda x: x.price_euros_wh * ## net revenue from electricity trading (before grid costs)
                    (x.discharge_energy - x.charge_energy),
                    grid_cost=lambda x: x.vgc * ## grid costs
                    (x.discharge_energy + x.charge_energy) +
                    x.fgc * (abs(x.schedule) > 10**-5),
                        variable_grid_cost=lambda x: x.vgc * ## grid costs
                    (x.discharge_energy + x.charge_energy),
                    fixed_grid_cost = lambda x: x.fgc * (abs(x.schedule) > 10**-5),
                    hourly_profit=lambda x: x.electricity_revenue - x.grid_cost ## profits
                    )

    return df.iloc[(frame_size if forecasted else 0) * 24:]

def get_daily_schedule(prices, vgc, fgc, bat, G_c, G_d, add_pv_and_load=False, pv_prod=None, load_demand=None, deg_cost=None, SOC_init=0, time_horizon=24):
    """
    Obtain schedule given the battery model, prices, vgc and fgc.
    """

    ## the arrays have to contain the data for the 24 hours of the day
    # if not (len(prices) == 24 and len(vgc) == 24 and len(fgc) == 24) :
    #     raise Exception(
    #         "The arrays should contain the data for a full day (24 hours)")

    ## instantiate AMPL object and load the model
    modules.load()  # load all AMPL modules
    ampl = AMPL()
    if add_pv_and_load :
        if pv_prod is None or load_demand is None or deg_cost is None :
            raise ValueError("If add_pv_and_load is True, pv_prod, load_demand and deg_cost should be provided")

        ampl.read("ampl/energy_arbitrage.mod")

        ## set parameters 
        ampl.get_parameter("time_horizon").set_values([time_horizon])
        ampl.get_parameter("vgc").set_values(vgc)
        ampl.get_parameter("fgc").set_values(fgc)
        ampl.get_parameter("p").set_values(prices)
        ampl.get_parameter("eff").set_values([bat.eff])
        ampl.get_parameter("Nint").set_values([bat.Nint])
        ampl.get_parameter("G_c").set_values(np.array(G_c)*bat.NEC)
        ampl.get_parameter("G_d").set_values(np.array(G_d)*bat.NEC)
        ampl.get_parameter("BESS_Capacity").set_values([bat.NEC])
        ampl.get_parameter("pv_prod").set_values(pv_prod)
        ampl.get_parameter("load_demand").set_values(load_demand)
        ampl.get_parameter("deg_cost").set_values(deg_cost)
        ampl.get_parameter("SOC_init").set_values([SOC_init])
        ampl.get_parameter("max_SOC").set_values([bat.max_SOC]*time_horizon)
        ampl.get_parameter("min_SOC").set_values([bat.min_SOC]*time_horizon)

        ## solve and get optimization solution
        ampl.option["solver"] = "gurobi"
        ampl.solve()

        pv_to_grid = ampl.get_variable('pv_to_grid').get_values().to_pandas()
        pv_to_load = ampl.get_variable('pv_to_load').get_values().to_pandas()
        pv_to_bess = ampl.get_variable('pv_to_bess').get_values().to_pandas()
        grid_to_load = ampl.get_variable('grid_to_load').get_values().to_pandas()
        grid_to_bess = ampl.get_variable('grid_to_bess').get_values().to_pandas()
        bess_to_grid = ampl.get_variable('bess_to_grid').get_values().to_pandas()
        bess_to_load = ampl.get_variable('bess_to_load').get_values().to_pandas()
        SOC = ampl.get_variable('SOC').get_values().to_pandas()

        daily_schedule = pd.concat([pv_to_grid, pv_to_load, pv_to_bess, grid_to_load, grid_to_bess, bess_to_grid, bess_to_load, SOC], axis=1)

        ## update battery state
        bat.n_cycles += (bat.eff*daily_schedule["pv_to_bess.val"].sum() + bat.eff*daily_schedule["grid_to_bess.val"].sum() + daily_schedule["bess_to_grid.val"].sum() + daily_schedule["bess_to_load.val"].sum())/(2*bat.init_NEC)
    else :
        ampl.read("ampl/ampl.mod")  

        ## set parameters 
        ampl.get_parameter("vgc").set_values(vgc)
        ampl.get_parameter("fgc").set_values(fgc)
        ampl.get_parameter("p").set_values(prices)
        ampl.get_parameter("eff").set_values([bat.eff])
        ampl.get_parameter("Nint").set_values([bat.Nint])
        ampl.get_parameter("max_SOC").set_values([1]*23 + [0])
        ampl.get_parameter("G_c").set_values(np.array(G_c)*bat.NEC)
        ampl.get_parameter("G_d").set_values(np.array(G_d)*bat.NEC)
        ampl.get_parameter("NEC").set_values([bat.NEC])

        ## solve and get optimization solution
        ampl.option["solver"] = "gurobi"
        ampl.solve()
        daily_schedule = ampl.get_variable('x').get_values().to_pandas()[
            "x.val"].to_numpy()

        # print(ampl.get_variable('x').get_values().to_pandas()[
        #     "x.val"].to_numpy())
        
        # print(ampl.get_variable('is_charging_or_discharging').get_values().to_pandas()[
        # "is_charging_or_discharging.val"].to_numpy())
        # ampl.reset()

        ## update battery state
        bat.n_cycles += abs(daily_schedule).sum()/(2*bat.init_NEC)
        
    return daily_schedule
