import wntr
import pandas as pd

def add_outages(outages, wn, time_stamp, time_step):
    for outage in outages:
        start_time, end_time = outage['StartTime'], outage['EndTime']
        start_time = time_stamp.get_loc(start_time)
        end_time = time_stamp.get_loc(end_time)
        pump = wn.get_link('PUMP_1')
        pump.add_outage(wn, start_time * time_step, end_time * time_step, priority=6)


def change_pump_curve(curves, wn, time_stamp, time_step):
    for i, curve in enumerate(curves):
        start_time, end_time = curve['StartTime'], curve['EndTime']
        start_time = time_stamp.get_loc(start_time)
        end_time = time_stamp.get_loc(end_time)
        c = curve['curve']
        pump = wn.get_link('PUMP_1')
        curve_name = 'faulty' + str(i)
        wn.add_curve(curve_name, 'HEAD', c)

        act = wntr.network.controls.ControlAction(pump, 'pump_curve_name', curve_name)
        cond = wntr.network.controls.SimTimeCondition(wn, 'after', start_time * time_step)
        ctrl = wntr.network.controls.Control(cond, act)
        wn.add_control('pump_fault' + str(i), ctrl)

        # return to normal
        act = wntr.network.controls.ControlAction(pump, 'pump_curve_name', '1')
        cond = wntr.network.controls.SimTimeCondition(wn, 'after', end_time * time_step)
        ctrl = wntr.network.controls.Control(cond, act)
        wn.add_control('pump_fault_end' + str(i), ctrl)


def change_pump_control_low(pump_control_low, wn, time_stamp, time_step):
    pump = wn.get_link('PUMP_1')
    tank = wn.get_node('T1')
    start_time, end_time = pump_control_low['StartTime'], pump_control_low['EndTime']
    start_time = time_stamp.get_loc(start_time)
    end_time = time_stamp.get_loc(end_time)

    wn.remove_control('control 2')
    act = wntr.network.controls.ControlAction(pump, 'status', 1)
    cond_time_start = wntr.network.controls.SimTimeCondition(wn, 'before', start_time * time_step)
    cond_time_end = wntr.network.controls.SimTimeCondition(wn, 'after', end_time * time_step)
    cond_level = wntr.network.controls.ValueCondition(tank, 'level', '<', 2.4)
    cond_or = wntr.network.controls.OrCondition(cond_time_start, cond_time_end)
    cond_and = wntr.network.controls.AndCondition(cond_or, cond_level)
    ctrl = wntr.network.controls.Control(cond_and, act)
    wn.add_control('control 2 time gap', ctrl)

    cond_time_start = wntr.network.controls.SimTimeCondition(wn, 'after', start_time * time_step)
    cond_time_end = wntr.network.controls.SimTimeCondition(wn, 'before', end_time * time_step)
    cond_level = wntr.network.controls.ValueCondition(tank, 'level', '<', pump_control_low['value'])
    cond_and = wntr.network.controls.AndCondition(cond_time_start, cond_time_end)
    cond_and = wntr.network.controls.AndCondition(cond_and, cond_level)
    ctrl = wntr.network.controls.Control(cond_and, act, priority=6)
    wn.add_control('pump_attack low', ctrl)


def change_pump_control_high(pump_control_high, wn, time_stamp, time_step):
    pump = wn.get_link('PUMP_1')
    tank = wn.get_node('T1')
    start_time, end_time = pump_control_high['StartTime'], pump_control_high['EndTime']
    start_time = time_stamp.get_loc(start_time)
    end_time = time_stamp.get_loc(end_time)

    wn.remove_control('control 1')
    act = wntr.network.controls.ControlAction(pump, 'status', 0)
    cond_time_start = wntr.network.controls.SimTimeCondition(wn, 'before', start_time * time_step)
    cond_time_end = wntr.network.controls.SimTimeCondition(wn, 'after', end_time * time_step)
    cond_level = wntr.network.controls.ValueCondition(tank, 'level', '>', 3.9)
    cond_or = wntr.network.controls.OrCondition(cond_time_start, cond_time_end)
    cond_and = wntr.network.controls.AndCondition(cond_or, cond_level)
    ctrl = wntr.network.controls.Control(cond_and, act)
    wn.add_control('control 1 time gap', ctrl)

    cond_time_start = wntr.network.controls.SimTimeCondition(wn, 'after', start_time * time_step)
    cond_time_end = wntr.network.controls.SimTimeCondition(wn, 'before', end_time * time_step)
    cond_level = wntr.network.controls.ValueCondition(tank, 'level', '>', pump_control_high['value'])
    cond_and = wntr.network.controls.AndCondition(cond_time_start, cond_time_end)
    cond_and = wntr.network.controls.AndCondition(cond_and, cond_level)
    ctrl = wntr.network.controls.Control(cond_and, act, priority=6)
    wn.add_control('pump_attack high', ctrl)


def masking(masking, dfs, filename):
    masking_data = pd.read_csv('../../results/' + filename, sep=';', index_col=0)
    masking_data['Timestamp'] = masking_data['Timestamp'].astype('datetime64')
    for m in masking:
        start_time, end_time = m['StartTime'], m['EndTime']
        node = m['node']
        masked = masking_data[node][(masking_data['Timestamp'] >= start_time) & (masking_data['Timestamp'] <= end_time)].values
        for df in dfs:
            if node in df.columns:
                df.loc[(df['Timestamp'] >= start_time) & (df['Timestamp'] <= end_time), node] = masked

