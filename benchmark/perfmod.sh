#!/bin/bash

# TODO Module loading or checking python version?

# Change these environment variables for your setup
# -----------------------------------------------------------------------------
export LS1_PATH=../ls1 # mardyn directory (will be copied and recompiled)
export PYTHONPATH=~/.local/lib/python2.7/site-packages/:$PYTHONPATH # pythonpath to jube installation
export PATH=~/.local/bin:$PATH # path to jube installation
export JUBE_INCLUDE_PATH=platforms/coolmuc # current platform
# -----------------------------------------------------------------------------

# Reset previous runs
python3 job_combine.py clear
rm -r scripts

# Perform benchmarks
jube run ls1.xml --hide-animation
python3 job_combine.py queue -t 48:0:0 -m 2:0:0 -p 40
echo "Run those jobs? (y/n)"
read dispatch
if [$dispatch != "y"]
then
    python3 job_combine.py queue -t 48:0:0 -m 2:0:0 -p 40 --dispatch
else
    echo "Benchmark aborted."
    exit 1
fi

echo "Waiting for completion..."
while [ "$(jube status bench_run)" != "FINISHED" ]
do
    sleep 5m
done
echo "Benchmarks completed!"

# Process results
jube analyse bench_run
jube result bench_run > ls1-bench.csv

# Create models
rm -r models
mkdir -p models
for traversal in c08 c04 # slice ori hs mp
do
    python3 csv2extrap.py ls1-bench.csv models/cutoff-${traversal}.extrap -m time_compute -v cutoff -f density=0.5 ljcenters=1 traversal=${traversal}
    python3 csv2extrap.py ls1-bench.csv models/density-${traversal}.extrap -m time_compute -v density -f cutoff=4 ljcenters=1 traversal=${traversal}
    python3 csv2extrap.py ls1-bench.csv models/ljcenters-${traversal}.extrap -m time_compute -v ljcenters -f density=0.5 cutoff=4 traversal=${traversal}
done


# TODO Call extrap with models
# TODO Plot results?

# TODO Two parameter models