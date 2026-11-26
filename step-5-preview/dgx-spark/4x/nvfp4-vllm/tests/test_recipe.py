#!/usr/bin/env python3
"""CPU-only tests. External deployment commands are never executed."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO=Path(__file__).resolve().parents[1]

def shell(name,*args,env=None):
    return subprocess.run(['bash',str(REPO/'scripts'/name),*map(str,args)],env=env,capture_output=True,text=True)

class RecipeTests(unittest.TestCase):
    def test_lists(self):
        groups=[(REPO/f'lists/files-holder{i}.txt').read_text().splitlines() for i in range(3)]
        small=(REPO/'lists/files-small.txt').read_text().splitlines()
        self.assertEqual([len(g) for g in groups],[21,17,57])
        all_files=sum(groups,[])+small
        self.assertEqual(len(all_files),107);self.assertEqual(len(set(all_files)),107)
        for name in all_files:
            self.assertEqual(Path(name).name,name)
    def test_links_all_ranks(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            for rank in range(4):
                storage=base/f'rank{rank}'
                for holder in range(3):
                    source=storage/'weights' if rank==holder else storage/f'nfs/holder{holder}'
                    source.mkdir(parents=True,exist_ok=True)
                    files=(REPO/f'lists/files-holder{holder}.txt').read_text().splitlines()
                    if holder==0:files+=(REPO/'lists/files-small.txt').read_text().splitlines()
                    for name in files:(source/name).write_text('fixture')
                env={**os.environ,'STEP5_ROOT':str(storage),'STEP5_CONFIG':''}
                p=shell('mklinks.sh',rank,env=env);self.assertEqual(p.returncode,0,p.stderr)
                links=list((storage/'model').iterdir());self.assertEqual(len(links),107)
                self.assertTrue(all(x.is_symlink() and x.is_file() for x in links))
                p=shell('mklinks.sh',rank,env=env);self.assertEqual(p.returncode,0,p.stderr)
    def test_entrypoint_profiles_and_ranks(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d); storage=base/'storage';(storage/'model').mkdir(parents=True)
            for f in ('config.json','model.safetensors.index.json'):(storage/'model'/f).write_text('{}')
            mock=base/'mock-vllm'
            mock.write_text('#!/usr/bin/env python3\nimport json,os,sys\nkeys=["STEP5_FP8KV","PYTHONPATH","VLLM_HOST_IP","VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS"]\nwith open(os.environ["MOCK_LOG"],"a") as f:f.write(json.dumps({"argv":sys.argv[1:],"env":{k:os.environ.get(k) for k in keys}})+"\\n")\n')
            mock.chmod(0o755)
            base_env={**os.environ,'STEP5_ROOT':str(storage),'FP8KV_BUNDLE':str(REPO/'fp8-kv'),'VLLM_BIN':str(mock),'MOCK_LOG':str(base/'calls')}
            for key in ('PROFILE','NODE_RANK','VLLM_HOST_IP','STEP5_FP8KV','KV_DTYPE','MAXLEN','FP8KV_BLOCKS','GMU','VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS','PYTHONPATH','API_PORT','SPEC_TOKENS','STEP5_DENSE','LMONLY'):
                base_env.pop(key,None)
            # Default b5-fp8 across all four ranks
            for rank in range(4):
                p=shell('entrypoint.sh',env={**base_env,'NODE_RANK':str(rank)});self.assertEqual(p.returncode,0,p.stderr)
            recs=[json.loads(x) for x in (base/'calls').read_text().splitlines()]
            self.assertEqual(len(recs),4)
            for rank,rec in enumerate(recs):
                call,renv=rec['argv'],rec['env']
                for flag,value in [('--port','8100'),('--max-model-len','589824'),('--kv-cache-dtype','fp8_e4m3'),('--gpu-memory-utilization','0.86'),('--max-num-batched-tokens','4096'),('--max-num-seqs','8'),('--tensor-parallel-size','4'),('--nnodes','4'),('--node-rank',str(rank)),('--block-size','16'),('--num-gpu-blocks-override','40000')]:
                    self.assertEqual(call[call.index(flag)+1],value)
                self.assertEqual('--headless' in call,rank!=0)
                self.assertEqual(renv['STEP5_FP8KV'],'1')
                self.assertEqual(renv['VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS'],'0')
                self.assertEqual(renv['VLLM_HOST_IP'],f'192.168.50.{11+rank}')
                self.assertIn(str(REPO/'fp8-kv/overlay'),renv['PYTHONPATH'] or '')
                self.assertEqual(call[call.index('--spec-method')+1],'mtp')
                self.assertEqual(call[call.index('--spec-tokens')+1],'3')
                self.assertEqual(json.loads(call[call.index('--hf-overrides')+1]),{'text_config':{'sparse_config':{'enabled':False}}})
                self.assertIn('--language-model-only',call)
            # Safer FP8 profile (b4-fp8)
            p=shell('entrypoint.sh',env={**base_env,'PROFILE':'b4-fp8','NODE_RANK':'0'});self.assertEqual(p.returncode,0,p.stderr)
            rec=json.loads((base/'calls').read_text().splitlines()[-1])
            self.assertEqual(rec['argv'][rec['argv'].index('--max-model-len')+1],'442368')
            self.assertEqual(rec['argv'][rec['argv'].index('--num-gpu-blocks-override')+1],'30000')
            self.assertEqual(rec['argv'][rec['argv'].index('--gpu-memory-utilization')+1],'0.85')
            self.assertEqual(rec['env']['VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS'],'1')
            self.assertEqual(rec['env']['STEP5_FP8KV'],'1')
            # BF16 safe profiles (192K and 256K): no overlay, no block override
            for prof,maxlen,gmu in [('b4-bf16-192k','196608','0.85'),('b4-bf16-256k','262144','0.86')]:
                p=shell('entrypoint.sh',env={**base_env,'PROFILE':prof,'NODE_RANK':'0'});self.assertEqual(p.returncode,0,p.stderr)
                rec=json.loads((base/'calls').read_text().splitlines()[-1])
                self.assertEqual(rec['argv'][rec['argv'].index('--max-model-len')+1],maxlen)
                self.assertEqual(rec['argv'][rec['argv'].index('--kv-cache-dtype')+1],'auto')
                self.assertEqual(rec['argv'][rec['argv'].index('--gpu-memory-utilization')+1],gmu)
                self.assertEqual(rec['env']['STEP5_FP8KV'],'0')
                self.assertEqual(rec['env']['VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS'],'1')
                self.assertNotIn('--num-gpu-blocks-override',rec['argv'])
                self.assertIsNone(rec['env']['PYTHONPATH'])
            # Reject invalid rank, unknown profile, and incomplete custom FP8 profile
            self.assertNotEqual(shell('entrypoint.sh',env={**base_env,'NODE_RANK':'4'}).returncode,0)
            self.assertNotEqual(shell('entrypoint.sh',env={**base_env,'PROFILE':'bogus'}).returncode,0)
            self.assertNotEqual(shell('entrypoint.sh',env={**base_env,'PROFILE':'custom','STEP5_FP8KV':'1','KV_DTYPE':'fp8_e4m3','MAXLEN':'442368','GMU':'0.85'}).returncode,0)
    def test_default_profile_from_example(self):
        keys=['PROFILE','NODE_RANK','API_PORT','SPEC_TOKENS','BATCH_TOKENS','MAXSEQ','STEP5_DENSE','LMONLY','RDMA_HCA','NCCL_CROSS_NIC','NCCL_MIN_NCHANNELS','NCCL_MAX_NCHANNELS']
        p=subprocess.run(['bash','-c','set -a; source "$1"; python3 -c "$2"','bash',
            str(REPO/'.env.example'),
            'import os,json; print(json.dumps([os.environ[k] for k in '+repr(keys)+']))'],
            capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(p.stdout),['b5-fp8','0','8100','3','4096','8','1','1','mlx5_0,mlx5_1','1','2','2'])
        compose=(REPO/'compose.yaml').read_text()
        self.assertIn('vllm/vllm-openai:step-5-preview@sha256:8bc189bb3f57183bcaf4f01405b29d4d92d782a182b384aac79b4b2885fb1fda',compose)
        self.assertIn('./fp8-kv:/opt/step5-fp8kv-bundle:ro',compose)
    def test_page_cache_loop_dry_run(self):
        p=shell('drop-page-cache.sh','--dry-run')
        self.assertEqual(p.returncode,0,p.stderr)
        lines=p.stdout.splitlines();self.assertEqual(len(lines),90)
        self.assertTrue(lines[0].startswith('t=0s:'))
        self.assertTrue(lines[-1].startswith('t=890s:'))
        self.assertTrue(all('echo 1 > /proc/sys/vm/drop_caches' in line for line in lines))
    def test_checksums(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);w=base/'weights';w.mkdir()
            names=(REPO/'lists/files-holder0.txt').read_text().splitlines()
            for name in names:(w/name).write_bytes(b'fixture')
            checksum=hashlib.sha256(b'fixture').hexdigest()
            (w/'SHA256SUMS').write_text(''.join(f'{checksum}  {name}\n' for name in names))
            env={**os.environ,'STEP5_CONFIG':'','STEP5_ROOT':str(base)}
            p=shell('verify-shards.sh',0,env=env);self.assertEqual(p.returncode,0,p.stderr)
            (w/names[0]).write_text('changed')
            p=shell('verify-shards.sh',0,env=env);self.assertNotEqual(p.returncode,0)
    def test_privacy_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);(base/'scripts').mkdir()
            shutil.copyfile(REPO/'scripts/privacy_scan.sh',base/'scripts/privacy_scan.sh')
            def scan():return subprocess.run(['bash',str(base/'scripts/privacy_scan.sh')],capture_output=True,text=True)
            self.assertEqual(scan().returncode,0)
            bad=['100'+'.64.1.1','10'+'.98.0.2','d'+'gx1','spa'+'rk-abcd','/ho'+'me/example','/ro'+'ot/private',
                 'reg'+'gie','pu'+'lse','As'+'tra','Fa'+'ble','O'+'pus','S'+'ol','Ar'+'gon','hf_'+'A'*25]
            for value in bad:
                (base/'example.txt').write_text(value+'\n')
                p=scan();self.assertEqual(p.returncode,1,(value,p.stdout,p.stderr))
            (base/'example.txt').unlink()
            self.assertEqual(scan().returncode,0)
    def test_bench_configuration(self):
        spec=importlib.util.spec_from_file_location('public_bench',REPO/'scripts/bench.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(len(module.NODES),4)
        self.assertEqual(list(module.NODES),['rank0','rank1','rank2','rank3'])
        snapshot={name:{'verified':True,'cap_state':'inactive'} for name in module.NODES}
        self.assertEqual(module.clock_label(snapshot,snapshot),'fullclk')
        self.assertIsNone(module.mtp_delta({'values':{}},{'values':{}})['acceptance_fraction'])

if __name__=='__main__':unittest.main(verbosity=2)
