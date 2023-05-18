# WDN-Simulation

This repository is built upon BattLeDIM Dataset Generator https://github.com/KIOS-Research/BattLeDIM
by
Stelios G. Vrachimis, Marios Kyriakou, Pavlos Pavlou, Demetrios G. Eliades
KIOS Center of Excellence, University of Cyprus, Cyprus

S. G. Vrachimis, D. G. Eliades, R. Taormina, Z. Kapelan, A. Ostfeld, S. Liu, M. Kyriakou, P. Pavlou, M. Qiu, and M. M. Polycarpou. Forthcoming. “Battle of the Leakage Detection and Isolation Methods,” Journal of Water Resources Planning and Management, 10.1061/(ASCE)WR.1943-5452.0001601

WDN-Simulation provides additional functionality for:
* simulating pump faults and outages
* simulating cyber-attacks (pump control change and signal masking)

## Installation

```
pip3 install -r requirements.txt
```

 
## Assets

* `networks` - water network structures of L-TOWN in .inp format

  The repository contains nominal network description L-TOWN.inp. To simulate real network you should download L-TOWN\_Real.inp from https://zenodo.org/record/4017659
  and put it in the `networks` directory (e.g. `curl https://zenodo.org/record/4017659/files/L-TOWN_Real.inp?download=1 -o networks/L-TOWN_Real.inp`).

* `measurements_for_masking` - this folder should contain data simulated without faults to use for masking. It can be downloaded from https://zenodo.org/record/7837165 (all 3 files are required).
    It is only used for masking measurements, other faults and leakages can be simulated without it.

* `configurations` - scenario configurations in .yaml format
    Exemplary configurations for all kinds of faults and attacks are provided.
    Put your own configuration here.

## Usage

Instructions:
1) Prepare the desired configuration of a scenario in .yaml format
2) Run `python dataset_generator.py -f configuration_file_name`

Sample usage:
```
python dataset_generator.py -f configurations/simple.yaml

# Requires L-TOWN_Real.inp file
python dataset_generator.py -f configurations/outage.yaml

# Requires L-TOWN_Real.inp file and measurements_for_masking files
python dataset_generator.py -f configurations/masking.yaml
```
