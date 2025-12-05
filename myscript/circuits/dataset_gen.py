# TODO: use ngspice_wrapper to run ngspice to generate the specs from the list of parameters
# for the parameter range, use cktparam.yaml
# the generated data should be in json format which contains the following information:
# {
#   topology: topology_val, 
#   parameter: {
#       param1: param1_val,
#       param2: param2_val, 
#       ...
#   },
#   specification: {
#       ugbw: ugbw_val,
#       gain: gain_val,
#       phm: phm_val,
#       ibias: ibias_val,
#   }
# }
# generate sets under 281, 628, 921, 978, 1781 separately

# later on, when we collate the data, we will mix the order at random
# as we train the MLP classifier
from ngspice_wrapper import NgSpiceWrapper
import json
import yaml
import os
import random


def make_ds(yaml_path, num_workers):
    with open(yaml_path, 'r') as f:
        yaml_data = yaml.load(f, Loader=yaml.FullLoader)
    num_top = len(yaml_data['dsn_netlist'])

    dataset_files = []
    # generate dataset files individually under each topology folder
    for i in range(num_top):
        _, dsg_netlist_fname = os.path.split(yaml_data['dsn_netlist'][i])  # topology name w/ .cir
        base_design_name = os.path.splitext(dsg_netlist_fname)[0]  # topology name w/o extension
        ngspice_sim = NgSpiceWrapper(
            num_process = num_workers, 
            top_index = i,
            yaml_path = yaml_path,
            path = '/home/ubuntu/FALCON/myscript'
        )
        output_file = os.path.join(base_design_name, base_design_name+".jsonl")
        ngspice_sim.run(output_file)
        dataset_files.append(output_file)

    all_entries = []
    for file in dataset_files:
        if not os.path.exists(file):
            continue
        with open(file, 'r') as f:
            data = json.load(f)
            if isinstance(data, list):
                all_entries.extend(data)
            else:
                all_entries.append(data)
    random.shuffle(all_entries)

    collated_path = "circuits/dataset.jsonl"
    with open(collated_path, 'w') as f:
        json.dump(all_entries, f)
