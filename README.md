# Performance Modelling for Auto-Tuning of Molecular Dynamics Simulations 
[![Build Status](https://travis-ci.org/ssauermann/md-perfmod.svg?branch=master)](https://travis-ci.org/ssauermann/md-perfmod) [![Codacy Badge](https://api.codacy.com/project/badge/Grade/27a3a33743e74e25adcca2ac1be497ee)](https://www.codacy.com/app/ssauermann/md-perfmod?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=ssauermann/md-perfmod&amp;utm_campaign=Badge_Grade)

## 1. Setup
### 1.1 Dependencies
* `pandas`

If your system does provide all dependencies you can try running the converter just by executing `python csv2extrap.py -h`.
 Proceed with the following section to run it in a virtual python environment with the tested versions of the dependencies.

### 1.2 Setup with pipenv
#### 1.2.1 General setup
1. Install python 3.5 and pip
2. Install pipenv via pip ```[sudo] pip install pipenv```
3. Clone the repository and cd into the folder
4. Create virtual environment and install dependencies: ```pipenv install```

#### 1.2.2 Setup example for the CooLMUC cluster
1. Load python3 module: ```module load python/3.5_intel```
2. Export the python lib path ```export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(dirname $(dirname $(which python3)))/lib```
3. Install pipenv via pip: ```python -m pip install --user pipenv```
4. Clone the repository and cd into the folder
5. Create virtual environment and install dependencies: ```python -m pipenv install```

#### 1.2.3 Running the converter
Either prefix every python call with ```[python -m] pipenv run``` or enter the shell for
 this virtual environment once with ```[python -m] pipenv shell``` and execute python like normal.

* ```python -m pipenv run python csv2extrap.py -h``` or
* ```python -m pipenv shell``` and ```python csv2extrap.py -h```

#### 1.2.4 Running other python versions than 3.5?
For other python versions it might be necessary to ignore the specific versions of the dependencies stored in the
 lock file. Use `pipenv install --skip-lock` for python &ge; 3.6.