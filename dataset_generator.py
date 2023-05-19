# -*- coding: utf-8 -*-
"""
Dataset Generator
Copyright: (C) 2019, KIOS Research Center of Excellence
"""
import pandas as pd
import numpy as np
import wntr
import os
import yaml
import shutil
import time
from math import sqrt
import argparse
import faults_and_attacks

argParser = argparse.ArgumentParser()
argParser.add_argument("-f", "--file", help="configuration file name", type=argparse.FileType('r'))
args = argParser.parse_args()
print("args=%s" % args)

with args.file as f:
    configuration = yaml.safe_load(f.read())
    print(configuration)


start_time = configuration['times']['StartTime']
end_time = configuration['times']['EndTime']
leakages = configuration['leakages']
leakages = leakages[1:]
number_of_leaks = len(leakages)
inp_file = configuration['Network']['filename']
print(f'Run input file: "{inp_file}"')
outages = configuration.get('outages')
pump_curves = configuration.get('pump_curves')
pump_control_low = configuration.get('pump_control_low')
pump_control_high = configuration.get('pump_control_high')
masking_pressure = configuration.get('masking_pressure')
masking_flowrate = configuration.get('masking_flowrate')
masking_demand = configuration.get('masking_demand')
results_folder = configuration.get('results_path', 'Results')

def get_sensors(leak_pipes, field):
    sensors = []
    [sensors.append(str(sens)) for sens in leak_pipes[field]]
    return sensors

pressure_sensors = get_sensors(configuration, 'pressure_sensors')
amrs = get_sensors(configuration, 'amrs')
flow_sensors = get_sensors(configuration, 'flow_sensors')
level_sensors = get_sensors(configuration, 'level_sensors')

# demand-driven (DD) or pressure dependent demand (PDD)
Mode_Simulation = 'PDD'


class LeakDatasetCreator:
    def __init__(self):

        # Create Results folder
        self.create_folder(results_folder)

        self.scenario_num = 1
        self.unc_range = np.arange(0, 0.25, 0.05)

        # Load EPANET network file
        self.wn = wntr.network.WaterNetworkModel(os.path.join('networks', inp_file))

        for name, node in self.wn.junctions():
            node.required_pressure = 25

        self.inp = os.path.basename(self.wn.name)[0:-4]

        # Get time step
        self.time_step = round(self.wn.options.time.hydraulic_timestep)
        # Create time_stamp
        self.time_stamp = pd.date_range(start_time, end_time, freq=str(self.time_step / 60) + "min")

        # Simulation duration in steps
        self.wn.options.time.duration = (len(self.time_stamp) - 1) * 300  # 5min step
        self.TIMESTEPS = int(self.wn.options.time.duration / self.wn.options.time.hydraulic_timestep)

    def create_csv_file(self, values, time_stamp, columnname, pathname):

        file = pd.DataFrame(values)
        file['time_stamp'] = time_stamp
        file = file.set_index(['time_stamp'])
        file.columns.values[0] = columnname
        file.to_csv(pathname)
        del file, time_stamp, values

    def create_folder(self, _path_):
        if os.path.exists(_path_):
            shutil.rmtree(_path_)
        os.makedirs(_path_)

    def dataset_generator(self):
        # Path of EPANET Input File
        print("Dataset Generator run...")

        # Initialize parameters for the leak
        leak_node = {}
        leak_diameter = {}
        leak_area = {}
        leak_type = {}
        leak_starts = {}
        leak_ends = {}
        leak_peak_time = {}
        leak_param = {}

        for leak_i in range(0, number_of_leaks):
            # Split pipe and add a leak node
            # leakages: pipeID, startTime, endTime, leakDiameter, leakType (abrupt, incipient)
            leakage_line = leakages[leak_i].split(',')

            # Start time of leak
            ST = self.time_stamp.get_loc(leakage_line[1])

            # End Time of leak
            ET = self.time_stamp.get_loc(leakage_line[2])

            # Get leak type
            leak_type[leak_i] = leakage_line[4]

            # Split pipe to add a leak
            pipe_id = self.wn.get_link(leakage_line[0])
            node_leak = f'{pipe_id}_leaknode'
            self.wn = wntr.morph.split_pipe(self.wn, pipe_id, f'{pipe_id}_Bleak', node_leak)
            leak_node[leak_i] = self.wn.get_node(self.wn.node_name_list[self.wn.node_name_list.index(node_leak)])

            if 'incipient' in leak_type[leak_i]:
                # END TIME
                ET = ET + 1
                PT = self.time_stamp.get_loc(leakage_line[5])+1

                # Leak diameter as max magnitude for incipient
                nominal_pres = 100
                leak_diameter[leak_i] = float(leakage_line[3])
                leak_area[leak_i] = 3.14159 * (leak_diameter[leak_i] / 2) ** 2

                # incipient
                leak_param[leak_i] = 'demand'
                increment_leak_diameter = leak_diameter[leak_i] / (PT - ST)
                increment_leak_diameter = np.arange(increment_leak_diameter, leak_diameter[leak_i], increment_leak_diameter)
                increment_leak_area = 0.75 * sqrt(2 / 1000) * 990.27 * 3.14159 * (increment_leak_diameter/2)**2
                leak_magnitude = 0.75 * sqrt(2 / 1000) * 990.27 * leak_area[leak_i]
                pattern_array = [0] * (ST) + increment_leak_area.tolist() + [leak_magnitude] * (ET - PT + 1) + [0] * (self.TIMESTEPS - ET)

                # basedemand
                leak_node[leak_i].demand_timeseries_list[0]._base = 1
                pattern_name = f'{str(leak_node[leak_i])}'
                self.wn.add_pattern(pattern_name, pattern_array)
                leak_node[leak_i].demand_timeseries_list[0].pattern_name = pattern_name
                leak_node[leak_i].required_pressure = nominal_pres
                leak_node[leak_i].minimum_pressure = 0

                # save times of leak
                leak_starts[leak_i] = self.time_stamp[ST]
                leak_starts[leak_i] = leak_starts[leak_i]._date_repr + ' ' + leak_starts[leak_i]._time_repr
                leak_ends[leak_i] = self.time_stamp[ET - 1]
                leak_ends[leak_i] = leak_ends[leak_i]._date_repr + ' ' + leak_ends[leak_i]._time_repr
                leak_peak_time[leak_i] = self.time_stamp[PT - 1]._date_repr + ' ' + self.time_stamp[PT - 1]._time_repr

            else:
                leak_param[leak_i] = 'leak_demand'
                PT = ST
                leak_diameter[leak_i] = float(leakage_line[3])
                leak_area[leak_i] = 3.14159 * (leak_diameter[leak_i] / 2) ** 2

                leak_node[leak_i]._leak_end_control_name = str(leak_i) + 'end'
                leak_node[leak_i]._leak_start_control_name = str(leak_i) + 'start'

                leak_node[leak_i].add_leak(self.wn, discharge_coeff=0.75,
                                           area=leak_area[leak_i],
                                           start_time=ST * self.time_step,
                                           end_time=(ET+1) * self.time_step)

                leak_starts[leak_i] = self.time_stamp[ST]
                leak_starts[leak_i] = leak_starts[leak_i]._date_repr + ' ' + leak_starts[leak_i]._time_repr
                leak_ends[leak_i] = self.time_stamp[ET]
                leak_ends[leak_i] = leak_ends[leak_i]._date_repr + ' ' + leak_ends[leak_i]._time_repr
                leak_peak_time[leak_i] = self.time_stamp[PT]._date_repr + ' ' + self.time_stamp[PT]._time_repr

        # Save/Write input file with new settings
        leakages_folder = os.path.join(results_folder, 'Leakages')
        self.create_folder(leakages_folder)

        # Other faults and attacks
        if pump_control_low:
            faults_and_attacks.change_pump_control_low(pump_control_low, self.wn, self.time_stamp, self.time_step)
        if pump_control_high:
            faults_and_attacks.change_pump_control_high(pump_control_high, self.wn, self.time_stamp, self.time_step)
        if outages:
            self.wn.convert_controls_to_rules(priority=3)  # avoid flickering controls
            faults_and_attacks.add_outages(outages, self.wn, self.time_stamp, self.time_step)
        if pump_curves:
            faults_and_attacks.change_pump_curve(pump_curves, self.wn, self.time_stamp, self.time_step)

        # Run wntr simulator
        sim = wntr.sim.WNTRSimulator(self.wn)
        self.wn.options.hydraulic.demand_model = Mode_Simulation
        results = sim.run_sim()
        if results.node["pressure"].empty:
            print("Negative pressures.")
            return -1

        if results:
            # Create CSV files
            for leak_i in range(0, number_of_leaks):
                if 'leaknode' in str(leak_node[leak_i]):
                    NODEID = str(leak_node[leak_i]).split('_')[0]
                totals_info = {'Description': ['Leak Pipe', 'Leak Area', 'Leak Diameter', 'Leak Type', 'Leak Start',
                                               'Leak End', 'Peak Time'],
                               'Value': [NODEID, str(leak_area[leak_i]), str(leak_diameter[leak_i]),
                                         leak_type[leak_i],
                                         str(leak_starts[leak_i]), str(leak_ends[leak_i]), str(leak_peak_time[leak_i])]}

                # Create leak XLS files
                decimal_size = 2

                leaks = results.node[leak_param[leak_i]][str(leak_node[leak_i])].values
                # Convert m^3/s (wntr default units) to m^3/h
                # https://wntr.readthedocs.io/en/latest/units.html#epanet-unit-conventions
                leaks = [elem * 3600 for elem in leaks]
                leaks = [round(elem, decimal_size) for elem in leaks]
                leaks = leaks[:len(self.time_stamp)]

                total_Leaks = {'Timestamp': self.time_stamp}
                total_Leaks[NODEID] = leaks
                df1 = pd.DataFrame(totals_info)
                df2 = pd.DataFrame(total_Leaks)
                writer = pd.ExcelWriter(os.path.join(leakages_folder, f'Leak_{NODEID}.xlsx'), engine='xlsxwriter')
                df1.to_excel(writer, sheet_name='Info', index=False)
                df2.to_excel(writer, sheet_name='Demand (m3_h)', index=False)
                writer.close()


            # Create xlsx file with Measurements
            total_pressures = {'Timestamp': self.time_stamp}
            total_demands = {'Timestamp': self.time_stamp}
            total_flows = {'Timestamp': self.time_stamp}
            total_levels = {'Timestamp': self.time_stamp}
            for j in range(0, self.wn.num_nodes):
                node_id = self.wn.node_name_list[j]
                if node_id in pressure_sensors:
                    pres = results.node['pressure'][node_id]
                    pres = pres[:len(self.time_stamp)]
                    pres = [round(elem, decimal_size) for elem in pres]
                    total_pressures[node_id] = pres

                if node_id in amrs:
                    dem = results.node['demand'][node_id]
                    dem = dem[:len(self.time_stamp)]
                    dem = [elem * 3600 * 1000 for elem in dem]  # CMH / L/s
                    dem = [round(elem, decimal_size) for elem in dem]  # CMH / L/s
                    total_demands[node_id] = dem

                if node_id in level_sensors:
                    level_pres = results.node['pressure'][node_id]
                    level_pres = level_pres[:len(self.time_stamp)]
                    level_pres = [round(elem, decimal_size) for elem in level_pres]
                    total_levels[node_id] = level_pres

            for j in range(0, self.wn.num_links):
                link_id = self.wn.link_name_list[j]

                if link_id not in flow_sensors:
                    continue
                flows = results.link['flowrate'][link_id]
                flows = [elem * 3600 for elem in flows]
                flows = [round(elem, decimal_size) for elem in flows]
                flows = flows[:len(self.time_stamp)]
                total_flows[link_id] = flows

            # Create a Pandas dataframe from the data.
            df1 = pd.DataFrame(total_pressures)
            df2 = pd.DataFrame(total_demands)
            df3 = pd.DataFrame(total_flows)
            df4 = pd.DataFrame(total_levels)

            if masking_pressure:
                faults_and_attacks.masking(masking_pressure, [df1, df4], 'pressures_normal.csv')
            if masking_demand:
                faults_and_attacks.masking(masking_demand, [df2], 'demands_normal.csv')
            if masking_flowrate:
                faults_and_attacks.masking(masking_flowrate, [df3], 'flows_normal.csv')

            # Create a Pandas Excel writer using XlsxWriter as the engine.
            writer = pd.ExcelWriter(os.path.join(results_folder, 'Measurements.xlsx'), engine='xlsxwriter')

            # Convert the dataframe to an XlsxWriter Excel object.
            # Pressures (m), Demands (m^3/h), Flows (m^3/h), Levels (m)
            df1.to_excel(writer, sheet_name='Pressures (m)', index=False)
            df2.to_excel(writer, sheet_name='Demands (L_h)', index=False)
            df3.to_excel(writer, sheet_name='Flows (m3_h)', index=False)
            df4.to_excel(writer, sheet_name='Levels (m)', index=False)

            # Close the Pandas Excel writer and output the Excel file.
            writer.close()
        else:
            print('Results empty.')
            return -1


if __name__ == '__main__':
    t = time.time()
    L = LeakDatasetCreator()
    L.dataset_generator()

    print(f'Total Elapsed time is {str(time.time() - t)} seconds.')
