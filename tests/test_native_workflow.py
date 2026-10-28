"""Integration checks for native build paths, separate experiments, and outputs."""
import csv
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]


class NativeWorkflowTests(unittest.TestCase):
    def test_build_and_run_with_spaces_without_make(self):
        with tempfile.TemporaryDirectory(prefix='lab3 native build ') as temp:
            project=Path(temp)
            (project/'lab').mkdir()
            for name in ['simlib.c','simlib.h','trace.h']:
                shutil.copy2(PROJECT/name,project/name)
            for name in ['runtime.py','simulator.c']:
                shutil.copy2(PROJECT/'lab'/name,project/'lab'/name)
            subprocess.run([sys.executable,str(project/'lab/runtime.py')],check=True,capture_output=True,text=True)
            executable=project/'build'/('simulator.exe' if os.name=='nt' else 'simulator')
            result=subprocess.run([str(executable),'--mode','fixed','--stations','1','--rate','.2',
                                   '--time','10000','--warmup','1000','--seed','400452897'],
                                  check=True,capture_output=True,text=True,cwd=project.parent)
            row=next(csv.DictReader(result.stdout.splitlines()[:2]))
            self.assertEqual(float(row['collisions']),0)
            self.assertGreater(int(row['successes']),1000)

    def test_individual_experiment_exports_only_requested_part(self):
        with tempfile.TemporaryDirectory(prefix='lab3 experiment results ') as temp:
            subprocess.run([sys.executable,str(PROJECT/'lab/run_experiments.py'),
                            '--experiment','3','--time','1000','--seeds','400452897',
                            '--workers','2','--output',temp],check=True,capture_output=True,text=True)
            folder=Path(temp)/'exp3'
            with (folder/'runs.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),46)
            self.assertEqual({r['mode'] for r in rows},{'beb'})
            self.assertTrue(all(int(r['persistent'])==-1 for r in rows))
            self.assertEqual(len((folder/'exp3_results.txt').read_text(encoding='utf-8').splitlines()),46)
            self.assertFalse((Path(temp)/'results/runs.csv').exists())
            self.assertFalse((Path(temp)/'exp4').exists())

    def test_nonbinary_minislot_configuration_roundtrips_and_replays(self):
        sys.path.insert(0,str(PROJECT/'lab'))
        from runtime import build
        executable=build()
        duration=str(1/.75)
        command=[str(executable),'--mode','reservation','--stations','10','--rate','2',
                 '--xr',duration,'--seed','400452897','--time','50000','--warmup','5000']
        first=subprocess.check_output(command,text=True).splitlines()
        row=next(csv.DictReader(first[:2]))
        self.assertEqual(float(row['xr']),float(duration))
        replay=[str(executable),'--mode',row['mode'],'--stations',row['stations'],
                '--rate',row['rate'],'--xr',row['xr'],'--seed',row['seed'],
                '--time',row['horizon'],'--warmup',row['warmup']]
        second=subprocess.check_output(replay,text=True).splitlines()
        self.assertEqual(first,second)

    def test_missing_compiler_reports_native_install_action(self):
        env=dict(os.environ,CC='lab3-compiler-that-does-not-exist')
        result=subprocess.run([sys.executable,str(PROJECT/'lab/runtime.py'),'--force'],env=env,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Install native GCC',result.stderr)
        self.assertIn('WSL and Make are not required',result.stderr)


if __name__=='__main__':unittest.main()
