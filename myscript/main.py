from pathlib import Path
import json
from train.train import train
from circuits.dataset_gen import make_ds


# TODO: construct dataset by simulating different specs using ngspice 
# (refer to circuits/dataset_gen.py and cktparam.yaml)
# and then, collate the dataset in one place (.jsonl) under circuits
# and then, read the json file and structure as a dataset
# and pass it to the trainer 

def main(
        yaml_path='circuits/cktparam.yaml',
        num_workers=1
    ):
    ds_path = Path("circuits/dataset.jsonl")
    if not ds_path.exists():
        make_ds(yaml_path, num_workers)
    
    with open('circuits/dataset.jsonl', 'r', encoding='utf-8') as file:
        dataset = json.load(file)

    train(dataset)

if __name__ == "__main__":
    main()