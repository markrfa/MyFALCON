# adapted from Autockt/autockt/eval_engines/ngspice_wrapper.py

import re
import copy
from multiprocessing.dummy import Pool as ThreadPool
import os
import subprocess
import yaml
import json
import itertools
from compute_performance import TwoStageClass
import tempfile
debug = False


class NgSpiceWrapper(object):

    BASE_TMP_DIR = os.path.abspath("/home/ubuntu/FALCON/myscript/designs")

    def __init__(self, num_process, top_index, yaml_path, path, root_dir=None):
        if root_dir == None:
            self.root_dir = NgSpiceWrapper.BASE_TMP_DIR
        else:
            self.root_dir = root_dir

        with open(yaml_path, 'r') as f:
            self.yaml_data = yaml.load(f, Loader=yaml.FullLoader)
        design_netlist = self.yaml_data['dsn_netlist'][top_index]
        design_netlist = path+'/'+design_netlist
        
        _, dsg_netlist_fname = os.path.split(design_netlist)  # filename w/ extension
        self.base_design_name = os.path.splitext(dsg_netlist_fname)[0]  # filename w/o extension
        self.num_process = num_process
        self.gen_dir = os.path.join(self.root_dir, "designs_" + self.base_design_name)

        os.makedirs(self.root_dir, exist_ok=True)
        os.makedirs(self.gen_dir, exist_ok=True)

        with open(design_netlist, 'r') as raw_file:
            self.tmp_lines = raw_file.readlines()
        
        self.translator = TwoStageClass()


    def get_design_name(self, state):
        fname = self.base_design_name
        for value in state.values():
            fname += "_" + str(value)
        return fname


    # TODO: modify the file 
    # so that it takes the parameter variations from the yaml file
    # and apply them to create designs individually
    def create_design(self, state, new_fname):
        design_folder = tempfile.TemporaryDirectory(prefix=new_fname, dir=self.gen_dir)

        fpath = os.path.join(design_folder, new_fname + '.cir')

        lines = copy.deepcopy(self.tmp_lines)
        for line_num, line in enumerate(lines):
            if '.param' in line:
                for key, value in state.items():
                    regex = re.compile("%s=(\S+)" % (key))
                    found = regex.search(line)
                    if found:
                        new_replacement = "%s=%s" % (key, str(value))
                        lines[line_num] = lines[line_num].replace(found.group(0), new_replacement)

        with open(fpath, 'w') as f:
            f.writelines(lines)
        return design_folder, fpath


    def simulate(self, fpath):
        info = 0 # this means no error occurred
        process = subprocess.run(
            ['ngspice', '-b', fpath, '>/dev/null', '2>&1'], 
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
        design_folder, fpath = self.create_design(state, dsn_name)
        topology = self.base_design_name
        info = self.simulate(fpath)
        specs = self.translate_result(design_folder)
        design_folder.cleanup()  # remove design folder
        return topology, state, specs, info


    def translate_result(self, output_path):
        """
        This method needs to be overwritten according to cicuit needs,
        parsing output, playing with the results to get a cost function, etc.
        The designer should look at his/her netlist and accordingly write this function.

        :param output_path:
        :return:
        """
        result = self.translate_result(output_path)
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

        # itertools.product() return the Cartesian product (all possible combinations) of the input list
        states = [dict(zip(param_names, combo)) for combo in itertools.product(*value_lists)]

        return states
    

    def run(self, output_file, design_names=None, verbose=False):
        """
        :param states:
        :param design_names: if None default design name will be used, otherwise the given design name will be used
        :param verbose: If True it will print the design name that was created
        :return:
            results = [(state: dict(param_kwds, param_value), specs: dict(spec_kwds, spec_value), info: int)]
        """
        states = self.make_states()
        pool = ThreadPool(processes=self.num_process)
        if design_names is None:
            design_names = [self.base_design_name] * len(states)
        arg_list = [(state, dsn_name, verbose) for (state, dsn_name)in zip(states, design_names)]
        specs = pool.starmap(self.create_design_and_simulate, arg_list)
        pool.close()

        with open(output_file, 'w') as json_f:
            json.dump(specs, json_f)

        return specs
