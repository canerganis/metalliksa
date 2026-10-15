"""R-LINK-1: difference paths resolve against the unchanged served kernels."""
import json
import subprocess
import sys
from pathlib import Path
from test_lpbf_research_harness import ResearchTestCase
import lpbf_research_codes as codes
import lpbf_research_manifest as manifest


class DifferenceLinks(ResearchTestCase):
    def test_research_paths_and_served_paths_resolve(self):
        paths=sorted({p for row in codes.SERVED_DIFFERENCES for p in row['servedPaths']})
        for row in codes.SERVED_DIFFERENCES:
            for path in row['researchPaths']:
                module,field=path.split('.')
                self.assertIn(field,manifest.FIELD_LIST[module])
        # Served calls are confined to this dedicated subprocess; the research evaluator stays guarded.
        script='''
import sys,json
sys.path.insert(0,sys.argv[1])
from lpbf_thermal_solver import calculate_meltpool_physics
paths=json.loads(sys.argv[2])
for material in ('ti6al4v','alsi10mg'):
 for kernel in ('rosenthal','goldak','eagar-tsai'):
  result=calculate_meltpool_physics(material,200,800,80,20,heat_source=kernel)
  for path in paths:
   value=result
   for key in path.split('.'):value=value[key]
print('6 served cases, all difference paths resolved')
'''
        proc=subprocess.run([sys.executable,'-B','-c',script,str(Path(__file__).parent),json.dumps(paths)],capture_output=True,text=True,timeout=120)
        self.assertEqual(proc.returncode,0,proc.stderr)
