"""PASTE-TEST INSTRUMENT for the affordance-layer fence (Navi / half_b, V3-V6).

Temporary probe, RETAINED so the fence citation resolves and the method is reproducible.
Each emitted affordance string is executed VERBATIM (as a reader would paste it) through
cmd, and the return code + first/last output line are captured.

WARNING -- READ BEFORE RUNNING (this is V6): several "pasteable" affordances are NOT
idempotent reads. Running this probe verbatim caused two real house mutations:
  * graduate ... --enforced-by ...   -> graduated a real lesson (reversed with --undo)
  * reply "test message"             -> sent a real bus message (id 1791262686850-0)
Both were reversed/retracted during the fence. Do NOT re-run this casually; it is a
measurement record, not a safe demo.
"""
import subprocess, os
os.chdir(r'E:\AI-Setup')

# (census_line, plane, census_cost_claim, exact_emitted_string)
SAMPLE = [
    (277, 'hooks', 'ZERO', 'py agent_cli.py bifrost-sync claude'),
    (471, 'hooks', 'ZERO', 'py agent_cli.py bifrost-sync claude'),
    (48,  'boot',  'ZERO', 'py agent_cli.py recall --full learn:experiment:check_whether_the_ask_is_already_built_before_building_it --json'),
    (53,  'boot',  'ZERO', 'py agent_cli.py note claude --get save:claude:bench-corrects-its-author-2026-10-02'),
    (274, 'know',  'ZERO', 'py agent_cli.py graduate claude --experiment a_bare_except_around_an_undefined_name_is_a_silent_organ --enforced-by "tests/test_x.py"'),
    (217, 'know',  'ZERO', 'py agent_cli.py tag-anti-pattern claude --experiment some_experiment_slug'),
    (203, 'know', 'MISSING-PREFIX', 'recall-at --limit 21'),
    (199, 'know', 'MISSING-ARG', 'py agent_cli.py wish'),
    (56,  'boot', 'PLACEHOLDER', 'py agent_cli.py mailbox claude --state <sha> | --open <sha>'),
    (790, 'bus',  'MISSING-ARG', 'py agent_cli.py bifrost-sync --consume'),
    (241, 'know', 'PLACEHOLDER', 'py agent_cli.py events --get <ref>'),
    (26,  'boot', 'PLACEHOLDER', 'py agent_cli.py note <you> --get <title>'),
    (236, 'know', 'MISSING-PREFIX', 'recall --full learn:experiment:a_bare_except_around_an_undefined_name_is_a_silent_organ'),
    (490, 'hooks','PLACEHOLDER', 'py agent_cli.py focus --set T227'),
    (315, 'bg',   'PLACEHOLDER', 'py agent_cli.py ask --get <handle>'),
    (772, 'bus',  'MISSING-VERB', 'py agent_cli.py reply "test message"'),
]

def paste(cmd):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    except subprocess.TimeoutExpired:
        return -99, 'TIMEOUT'
    except Exception as e:
        return -98, f'{type(e).__name__}: {e}'

if __name__ == '__main__':
    for line, plane, claim, cmd in SAMPLE:
        rc, out = paste(cmd)
        o = out.strip().replace('\r', '')
        first = o.splitlines()[0] if o else ''
        tail = o.splitlines()[-1] if o else ''
        err = ('error' in o.lower() or 'not found' in o.lower() or 'not recognized' in o.lower()
               or 'Traceback' in o or rc != 0)
        print(f'[{plane:5}] L{line} claim={claim} rc={rc} err={err}')
        print(f'   PASTED: {cmd}')
        print(f'   first: {first[:160]}')
        if tail and tail != first:
            print(f'   last : {tail[:160]}')
