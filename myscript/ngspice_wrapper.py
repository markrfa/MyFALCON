# adapted from Autockt/autockt/eval_engines/ngspice_wrapper.py

import re
import copy
from multiprocessing.dummy import Pool as ThreadPool
import os
import subprocess
import yaml
import json
import itertools
import math
from compute_performance import TwoStageClass
from tqdm import tqdm
debug = False


class NgSpiceWrapper(object):

    BASE_TMP_DIR = os.path.abspath("/home/ubuntu/FALCON/myscript/circuits")

    def __init__(self, num_process, top_index, yaml_path, path, root_dir=None):
        if root_dir == None:
            self.root_dir = NgSpiceWrapper.BASE_TMP_DIR
        else:
            self.root_dir = root_dir

        with open(yaml_path, 'r') as f:
            self.yaml_data = yaml.load(f, Loader=yaml.FullLoader)
        self.fpath = self.yaml_data['dsn_netlist'][top_index]
        self.fpath = os.path.join(path, self.fpath)
        # print("topology index:", top_index)
        # print("self.fpath:", self.fpath)
        
        
        _, dsg_netlist_fname = os.path.split(self.fpath)  # filename w/ extension
        self.base_design_name = os.path.splitext(dsg_netlist_fname)[0]  # filename w/o extension
        self.num_process = num_process
        self.gen_dir = os.path.join(self.root_dir, self.base_design_name)

        os.makedirs(self.root_dir, exist_ok=True)
        os.makedirs(self.gen_dir, exist_ok=True)

        with open(self.fpath, 'r') as raw_file:
            self.tmp_lines = raw_file.readlines()
        
        self.translator = TwoStageClass()


    def get_design_name(self, state):
        fname = self.base_design_name
        for value in state.values():
            fname += "_" + str(value)
        return fname


    # TODO: modify the file from circuits/circut_num
    # so that it takes the parameter variations from the yaml file
    # and apply them to create designs individually
    def create_design(self, state):
        lines = copy.deepcopy(self.tmp_lines)
        for line_num, line in enumerate(lines):
            if '.param' in line:
                for key, value in state.items():
                    regex = re.compile("%s=(\S+)" % (key))
                    found = regex.search(line)
                    if found:
                        new_replacement = "%s=%s" % (key, str(value))
                        lines[line_num] = lines[line_num].replace(found.group(0), new_replacement)

        with open(self.fpath, 'w') as f:
            f.write(''.join(lines))


    def simulate(self, fpath):
        # print("simulation started on file", fpath)
        info = 0 # this means no error occurred
        process = subprocess.run(
            f"ngspice -b {fpath} >/dev/null 2>&1",
            shell=True,
            capture_output=True, 
            text=True
        )
        exit_code = process.returncode
        if debug:
            print(process)
            print(fpath)
        if (exit_code % 256):
            # raise RuntimeError('program {} failed!'.format(command))
            info = 1 # this means an error has occurred
        # print(f"simulation complete, exit code: {info}")
        return info


    # Creates a temporary design folder
    # in which new design.cir is made, simulated, and then the results are recorded in 
    # json file directly under the folder
    # after that, the temporary folder and their contents are deleted
    # this prevents memory overflow
    def create_design_and_simulate(self, state, dsn_name=None, verbose=False):
        if debug:
            print('state', state)
            print('verbose', verbose)
        if dsn_name == None:
            dsn_name = self.get_design_name(state)
        else:
            dsn_name = str(dsn_name)
        if verbose:
            print(dsn_name)
        self.create_design(state)
        topology = self.base_design_name
        info = self.simulate(self.fpath)
        specs = self.translate_result(self.gen_dir, info)
        return topology, state, specs, info


    def translate_result(self, output_path, info):
        """
        This method needs to be overwritten according to cicuit needs,
        parsing output, playing with the results to get a cost function, etc.
        The designer should look at his/her netlist and accordingly write this function.

        :param output_path:
        :return:
        """
        if info != 0:
            return []
        result = self.translator.translate_result(output_path)
        return result


    # make states from cktparam.yaml
    # list of all possible combinations of parameters as specified in the yaml
    def make_states(self):
        params = self.yaml_data["params"]
        param_ranges = params.values()
        param_names = list(params.keys())

        value_lists = []
        for bounds in param_ranges:
            start, stop, step = bounds
            values = []
            cur = start
            # generate inclusive sequence, guard against floating point drift
            while cur <= stop + 1e-15:
                values.append(cur)
                cur += step
            value_lists.append(values)
        
        return param_names, value_lists

        # itertools.product() return the Cartesian product (all possible combinations) of the input list
        # states = [dict(zip(param_names, combo)) for combo in itertools.product(*value_lists)]
    

    # lazy evaluation to save memory
    def all_states(self, param_names, value_lists):
        for combo in itertools.product(*value_lists):
            yield dict(zip(param_names, combo))
    

    def run(self, output_file, batch_size=10_000, verbose=False):
        """
        :param batch_size:  Size of the buffer before it is flushed to the file
        :param verbose: If True it will print the design name that was created
        :return:
            results = [(state: dict(param_kwds, param_value), specs: dict(spec_kwds, spec_value), info: int)]
        """
        if not os.path.exists(output_file):
            os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
            open(output_file, 'w').close()

        param_names, value_lists = self.make_states()

        total_iterations = math.prod(len(l) for l in value_lists)
        
        pbar = tqdm(total=total_iterations, desc="Generating simulations...", unit="file")
        batch = []
        for i, state in enumerate(self.all_states(param_names, value_lists)):
            batch.append(self.create_design_and_simulate(state, self.base_design_name, verbose))
            pbar.update(1)  # increment progress

            # flush the batch every 10,000 entries
            if i % batch_size == 0:
                with open(output_file, 'w') as json_f:
                    json.dump(batch, json_f)
                    batch.clear()
        pbar.close()
