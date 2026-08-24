"""M4 measurement for t385 half_b (disposable): can a cheap extractor see the REAL
file set of a wrapper command?"""
import re
import time

CMD = ("py - << PYEOF\n"
       "import re\n"
       "for f in ['scripts/bifrost_daemon.py', 'core/recall/at_action.py']:\n"
       "    pass\n"
       "PYEOF")
t0 = time.perf_counter()
hits = re.findall(r"(?<![A-Za-z0-9])([A-Za-z0-9_./-]+\.(?:py|md|json|yml|yaml|js))", CMD)
dt = time.perf_counter() - t0
print("M4 extracted:", hits)
print(f"M4 cost: {dt*1000:.3f}ms")
