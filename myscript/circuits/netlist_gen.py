# NOTE: This only makes a draft .cir file. For precise simulatable .cir file, I used GPT and then curated them by hand

import yaml
import os

# Load topology file
def parse_topology(filepath):
    components = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            name = parts[0]
            nodes = parts[1:-1]
            nodes = [n.strip("()") for n in nodes]
            ctype = parts[-1]
            components.append((name, nodes, ctype))
    return components


# Load YAML parameter file
def load_params(yaml_path):
    with open(yaml_path, 'r') as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    return data['params']

# Generate netlist
def generate_netlist(components, params, output_path):
    netlist = []
    netlist.append("* Generated Netlist")
    netlist.append('.include "../45nm_bulk.txt"\n')

    # Parameter definitions from YAML
    for name, value in params.items():
        netlist.append(f".param {name}={value[0]}")

    netlist.append(".param ibias=30u")
    netlist.append(".param cload=10p")
    netlist.append(".param vcm=0.6\n")
    netlist.append("* Components")

     # Component instantiations
    for name, nodes, ctype in components:
        node_str = ' '.join(nodes)
        if 'nmos' in ctype:
            netlist.append(f"{name} {node_str} nmos w=w l=ll m=mn")
        elif 'pmos' in ctype:
            netlist.append(f"{name} {node_str} pmos w=w l=ll m=mp")
        elif ctype == "resistor":
            netlist.append(f"{name} {node_str} R")
        elif ctype == "capacitor":
            netlist.append(f"{name} {node_str} C")
        else:
            print(f"Unknown component type: {ctype}")
    
    netlist.append('')

    # Stimulus and control (generic part from two_stage_opamp.cir)
    netlist += [
        "* Inputs",
        "vin in 0 dc=0 ac=1.0",
        "ein1 net1 cm in 0 0.5",
        "ein2 net2 cm in 0 -0.5",
        "vcm cm 0 dc=vcm",
        "\n* Supplies",
        "vdd VDD 0 dc=1.2",
        "vss 0 VSS dc=0",
        "\n* Load",
        "CL VOUT1 0 cload",
        "\n* Tail current source correctly attached",
        "ibias VDD net7 ibias",
        "",
        "* output pin: VOUT1",
        "\n* Simple bias sources (choose values!)",
        "vvb1 VB1 0 0.8",
        "vvb2 VB2 0 0.9",
        "vvb3 VB3 0 0.6",
        "\n* --- AC Analysis (Logarithmic Sweep from 1Hz to 10GHz) ---",
        "* --- for ugbw_min, phm_min, ibias_max ---",
        ".ac dec 10 1 10G",
        ".meas ac gain_min FIND v(VOUT1) AT=1",
        ".meas ac ugbw_min WHEN vm(VOUT1)=1 CROSS=1",
        ".meas ac phase_ugbw FIND vp(VOUT1) WHEN vm(VOUT1)=1 CROSS=1",
        "*phm_min = 180+phase_ugbw",    
        "\n* --- Printing Results ---",
        ".control", 
        "*    set ngdebug",
        "    set wr_vecnames",
        "    set units=degrees",
        "    .option numdgt=7",
        "    run",
        "    wrdata output/ac.csv v(VOUT1)",
        "    op",
        "    wrdata output/dc.csv i(vdd)",
        ".endc",
        ".end",
    ]

    with open(output_path, 'w') as f:
        f.write('\n'.join(netlist))

# Example usage
if __name__ == "__main__":
    cir_list = [281]  # NOTE: each netlist requires different fix to work
    for cir in cir_list:
        topology_file = f"{cir}/{cir}.cir"
        yaml_file = "cktparam.yaml"
        output_netlist = f"{cir}/{cir}_gen_netlist.cir"
        
        # make output directory (for ac.csv and dc.csv)
        os.makedirs(f"{cir}/output", exist_ok=True)

        components = parse_topology(topology_file)
        params = load_params(yaml_file)
        generate_netlist(components, params, output_netlist)
