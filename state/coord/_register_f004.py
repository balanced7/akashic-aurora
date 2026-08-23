import time
from core.coord.forecast_registry import ForecastRegistry

path = "state/coord/forecasts.jsonl"
reg = ForecastRegistry(path=path)

row = reg.register(
    id="F004",
    task_ref="T376",
    registered_by="deepseek",
    expectation={
        "statement": ("before the rolling-refresh drill measures it, the "
                      "wedged-vs-thinking discriminator spec (half_a section 2) "
                      "classifies the drill stager states without a single false "
                      "kill: a deliberately-WEDGED runner is relabeled wedged "
                      "(never thinking), and a deliberately-THINKING runner "
                      "blocked in a model call is relabeled thinking (never killed)"),
        "metric": "stager states correctly classified / false kills",
        "target": "0 false kills, 3/3 states correct",
    },
    horizon_ts=time.time() + 7 * 86400,
    mechanism=("the discriminator is a thread-stack question, not a timeout: "
               "py-spy dump separates 'MainThread blocked in write/flush/recv' "
               "(wedged) from 'MainThread above the model call or idle in a "
               "producer-consumer wait' (thinking); the tree already proves this "
               "on two live receipts (deepseek T019-pipe wedge vs kimi "
               "instrument-fault false-DEAD), and the spec fails toward thinking "
               "with the stack probe required before any kill"),
    dies_when=("the drill stager states do not actually exercise a "
               "wedged-vs-thinking distinction (only down vs up with no "
               "blocked-write vs blocked-model-call pair), or py-spy cannot "
               "reach the runner MainThread when it fires"),
)
print(f"[forecast] registered {row['id']} by {row['registered_by']} "
      f"(horizon {time.strftime('%Y-%m-%d', time.localtime(row['horizon_ts']))})")
