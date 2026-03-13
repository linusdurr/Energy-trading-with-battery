# Power Flows in a Grid-connected PV, Battery and Load System

The entire simulation can be run using the notebook *simulations_household.ipynb*. This will create several plotly figures in the *./out/with_pv_and_load/* folder. They show a simulation of the entire year 2022 (for performance reasons when displaying the figures, we also have each month individually).

The output figures of the latest version of our model is already included in the above mentioned folder are also already visible in the Jupyter notebook.

## Code Structure

### AMPL
The optimization problem is solved using AMPL. We solve the problem once for each day of the dataset. The time horizon of each simulation can be set using the *time_horizon* parameter. For our paper we set this to 48h to make sure the system is capabale of keeping the battery charged over night in case electricity prices are expected to be higher the next day.

The relevant model file is *./ampl/energy_arbitrage.mod*. A single optimization can be performed directly in AMPL using dummy data with the available *.dat* and *.run* files. Typically, the AMPL code would be run using the AMPL python integration and the provided code...

### Python
The python part of the code keeps track of parameters between individual simulations. For example the battery state is stored in a *Battery* object where parameters are updated after every run of the simulation and these updated parameters are then passed to AMPL at the start of each simulation.

The file *.src/battery.py* defines the *Battery* class, the file *./src/optimize.py* contains the functions running the optimization and the file *./src/plot.py* contains the function that creates the plots of the results.

## Dependencies
Of course, AMPL needs to be installed on the machine. Furthermore, the following Python packages are necessary:
* *scipy*
* *matplotlib*
* *numpy*
* *pandas*
* *amplpy*
* *plotly*

## Authorship
This entire code base is heavily based on the code provided by Puech et al. on GitHub for their paper *Optimal battery charge scheduling for
revenue stacking under operational constraints via energy arbitrage* (For citation see report). We reuse their battery model and extend it with our additions. The code structure remains based on their work.
