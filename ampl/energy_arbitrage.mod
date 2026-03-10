################### SETS ###################

# Time intervals of 15 minutes in a day
set T ordered := {0..23}; # 96 values 



######################### PARAMETERS & VARIABLES #########################
################### Battery constrains ###################
# BESS nominal energy capacity in Wh: Initial maximum capacity of the battery (which is reduced with degradation)
param BESS_Capacity >= 0, <= 60000 default 0;  
# initial energy capacity at time t
param SOC_init {t in T} >= 0, <= BESS_Capacity default 0;
# efficiency of the battery
param eff >0, <=1 default 0.92; #An average efficiency for a lithium-ion battery
# minimum SOC required, it is a 15% and 85% of the BESS_Capacity to avoid deep discharge and overcharge, which can damage the battery and reduce its lifespan
param min_SOC{T} >= 0, <= 1 default 0;
param max_SOC{T} >= 0, <= 1 default 1;
# State of charge at time t
# var SOC{t in T} >= min_SOC[t], <= max_SOC[t];

######################### PV #########################
var pv_to_load{t in T} >=0;
var pv_to_bess{t in T} >=0, <=BESS_Capacity;
var pv_to_grid{t in T} >=0;
param pv_prod{t in T} >=0;


######################### Load #########################
param load_demand{t in T} >=0;

######################### Grid #########################
var grid_to_load{t in T} >=0;
var grid_to_bess{t in T} >=0, <=BESS_Capacity;

######################### BESS #########################
var bess_to_grid{t in T} >=0, <=BESS_Capacity;
var bess_to_load{t in T} >=0, <=BESS_Capacity;



################### Price and costs ###################
# price of electricity per time period
param p{t in T};
# fixed grid cost per time period
param fgc{t in T} >= 0 default 0;
# variable grid cost per time period
param vgc{t in T} >= 0 default 0;

param deg_cost >= 0 default 0; # degradation cost per Wh of energy charged or discharged, it is a simplification to consider a linear degradation cost, but it allows us to capture the trade-off between profit and battery degradation in a simple way. In reality, the degradation of a battery is a complex process that depends on many factors, such as the depth of discharge, the charging and discharging rates, the temperature, and the age of the battery. A more accurate model would need to consider these factors and their interactions to capture the true degradation of the battery over time.


# ----------- constants -------------
# eps, epsilon param to be able to make strictly greater than...
param eps := 0.01;
# big M to compute is_charging and is_discharging
param M := BESS_Capacity;

# ----------- Decision variables --------------
# Energy charged or discharged at time t, positive for charging and negative for discharging
var BESS_state{t in T} >= -BESS_Capacity, <= BESS_Capacity;
var z{t in T} binary; # boolean indicating if we are charging or discharging (1), or holding (0)
var y{t in T} binary; # boolean indicating if we are charging (1), or discharging (0)


# ---------- charging/discharging or no action on the battery ---------
subject to is_charging_or_discharging_right {t in T} : 
    bess_to_grid[t] + grid_to_bess[t] + pv_to_bess[t] + bess_to_load[t] >= eps*z[t];

subject to is_charging_or_discharging_left {t in T} : 
    bess_to_grid[t] + grid_to_bess[t] + pv_to_bess[t] + bess_to_load[t] <= M * z[t];

#------------------- Auxiliary variables -------------------
# Convex combintation linearization variables

subject to BESS_state_asignation {t in T} :
    BESS_state[t] == - bess_to_grid[t] + grid_to_bess[t] - bess_to_load[t] + pv_to_bess[t];

subject to bess_exporting {t in T} :
    bess_to_grid[t] + bess_to_load[t] <= M * y[t];  

subject to bess_importing {t in T} :
    grid_to_bess[t] + pv_to_bess[t] <= M * (1-y[t]);

# ----------- SOC Charge/discharge curve discretization -------------
######### Convex combintation linearization ##########

# number of intervals
param Nint >= 1, <= 100 default 5;
# incremental - number of intervals
param inc := 1/Nint;
# interval indices 
set I ordered := {1..Nint};
# cut points indices 
set C ordered := {0..Nint};
# cut points
param S{i in C} := i*inc;
# max negative change in energy capacity (discharge)
param G_d{i in C} >= -BESS_Capacity, <= 0 default -BESS_Capacity/2;
# max positive change in energy capacity (charge)
param G_c{i in C} >=0, <= BESS_Capacity default BESS_Capacity/2;
# interval indicator
var in_interval{I,T} binary;
# convex combination weights
var interval_start_w{I,T} >=0, <= 1 default 1;
var interval_end_w{I,T} >= 0, <= 1 default 0;

#------------------- Availability constraints -------------------
# keep SOC within bounds 
subject to availability_constraint {t in T}:
    min_SOC[t] <= SOC_init[t]/BESS_Capacity + sum{t_passed in 0..t} BESS_state[t_passed]/BESS_Capacity <= max_SOC[t];

# ------------------- Find discretization parameters of SOC ------------
subject to find_weights_for_each_interval {t in T} : 
    sum{k in I} (interval_start_w[k,t]*S[k-1]+ interval_end_w[k,t]*S[k]) == SOC_init[t]/BESS_Capacity + sum{t_passed in 0..t-1} BESS_state[t_passed] / BESS_Capacity;

subject to find_weights_for_each_interval_0 : 
    sum{k in I} (interval_start_w[k,0]*S[k-1]+ interval_end_w[k,0]*S[k]) == SOC_init[0]/BESS_Capacity;

subject to comvex_combination_constraint {k in I, t in T} : 
    interval_start_w[k,t] + interval_end_w[k,t] == in_interval[k,t];

subject to select_one_interval {t in T} : 
    sum{k in I} in_interval[k,t] == 1;

#-------------------Charge/ Discharge rate constraints ----------------
# energy increment should be below maximum increment 
subject to energy_increment {t in T}:
    sum{k in 1..Nint} (interval_start_w[k,t] * G_c[k-1] + interval_end_w[k,t] * G_c[k]) >= BESS_state[t];

# energy increment should be above minimum increment 
subject to energy_decrease {t in T}:
    sum{k in 1..Nint} (interval_start_w[k,t] * G_d[k-1] + interval_end_w[k,t] * G_d[k]) <= BESS_state[t];



################### Power flow constrains ###################

#................... Energy balance PV ............... 
subject to energy_balance_pv {t in T} :
    pv_prod[t] == pv_to_grid[t] + pv_to_load[t] + pv_to_bess[t];

#................... Energy balance Load ............... 
subject to energy_balance_load {t in T} :
    load_demand[t] == grid_to_load[t] + pv_to_load[t] + bess_to_load[t];

#................... Energy balance BESS ...............
# subject to energy_balance_bess {t in T} :
#     SOC[t] == bess_to_grid[t] - grid_to_bess[t] - pv_to_bess[t] + bess_to_load[t] + SOC_init[t];



############################# OBJECTIVE FUNCTION #############################
# -x_n[i]*eff) * p[i] is the term thht makes us money, the rest of the variables are costs with negative prices considered
# The efficiecny is only cosidered for the discahrging because we dont sell all the energy that we discharge, but when charging we assume the cost of the energy lost
#
maximize profit :
    sum{t in T} (
        (bess_to_grid[t]+pv_to_grid[t]-grid_to_bess[t]*eff-grid_to_load[t]) * p[t] 
        - (bess_to_grid[t]+pv_to_grid[t]+grid_to_bess[t]*eff+grid_to_load[t]) * vgc[t] 
        - z[t] * fgc[t] - deg_cost*BESS_state[t]
        );