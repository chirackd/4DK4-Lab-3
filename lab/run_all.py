#!/usr/bin/env python3
"""One native entry point: build, test, all six experiments, sensitivity, plots."""
import argparse
from pathlib import Path
import subprocess
import sys
from runtime import ROOT, build


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--quick', action='store_true', help='Smoke run only: one seed, shortened horizons')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--output', type=Path, default=ROOT.parent/'output')
    p.add_argument('--skip-analysis', action='store_true', help='Run C experiments without third-party Python packages')
    a=p.parse_args()
    if a.workers<1:p.error('--workers must be positive')
    output=a.output.resolve()
    build()
    def call(script,*args):
        subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],check=True)
    call('test_simulator.py')
    common=['--output',output,'--workers',a.workers]
    quick_main=['--time',10000,'--seeds',400452897] if a.quick else []
    quick_sens=['--times',10000,30000,50000,'--seeds',400452897] if a.quick else []
    call('run_experiments.py',*common,*quick_main)
    call('run_sensitivity.py',*common,*quick_sens)
    if not a.skip_analysis:
        call('analyze.py','--results-dir',output/'results','--figures-dir',output/'figures')
        if not a.quick:call('validate_trends.py','--results-dir',output/'results')
        call('build_report.py','--results-dir',output/'results','--figures-dir',output/'figures','--output-dir',output)
    print(f'Complete: {output}')
    if a.quick:print('QUICK SMOKE RUN: these shortened results are not submission-quality experiments.')
    print("Plots and report use this run's own measurements; checked-in lab/ artifacts remain separate until explicitly refreshed.")

if __name__=='__main__': main()
