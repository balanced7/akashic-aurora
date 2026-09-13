"""Tests for the parsing helpers in arsenal/lanes/gst_d3d12_soak.py (Lane B.1 soak).

The sample lines were captured from gst-launch-1.0 1.28.7 on this machine (2026-09-13), running
the same pipeline shape the soak uses; lines marked "constructed" follow the same format but
were edited by hand. GStreamer is not needed to run these tests.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_LANE_FILE = Path(__file__).resolve().parent.parent / "arsenal" / "lanes" / "gst_d3d12_soak.py"


def _load_lane():
    try:
        from arsenal.lanes import gst_d3d12_soak  # type: ignore
        return gst_d3d12_soak
    except ImportError:
        spec = importlib.util.spec_from_file_location("arsenal_gst_d3d12_soak", _LANE_FILE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        return module


soak = _load_lane()

CAPS_D3D12 = (
    "video/x-raw(memory:D3D12Memory), format=(string)NV12, width=(int)1920, height=(int)1080, "
    "interlace-mode=(string)progressive, multiview-mode=(string)mono, "
    "multiview-flags=(GstVideoMultiviewFlagsSet)0:ffffffff:/right-view-first/left-flipped/"
    "left-flopped/right-flipped/right-flopped/half-aspect/mixed-mono, "
    "pixel-aspect-ratio=(fraction)1/1, colorimetry=(string)bt709, framerate=(fraction)60/1"
)
SINK_ELEMENT = "/GstPipeline:pipeline0/GstFPSDisplaySink:fps/GstFakeVideoSink:sink/GstFakeSink:sink"

FPS_LINE = ("/GstPipeline:pipeline0/GstFPSDisplaySink:fps: last-message = "
            "rendered: 62, dropped: 0, current: 61.89, average: 61.89")
FPS_DROP_LINE = ("/GstPipeline:pipeline0/GstFPSDisplaySink:fps: last-message = "
                 "rendered: 4, dropped: 4, fps: 2.25, drop rate: 2.25")
# h265parse src caps, codec_data trimmed.
PARSE_SRC_LINE = ("/GstPipeline:pipeline0/GstH265Parse:parse.GstPad:src: caps = video/x-h265, "
                  "stream-format=(string)hvc1, alignment=(string)au, width=(int)1920, "
                  "height=(int)1080, framerate=(fraction)60/1")
DEC_SRC_LINE = f"/GstPipeline:pipeline0/GstD3D12H265Dec:dec.GstPad:src: caps = {CAPS_D3D12}"
CAPSFILTER_LINE = f"/GstPipeline:pipeline0/GstCapsFilter:capsfilter0.GstPad:src: caps = {CAPS_D3D12}"
SINK_CHAIN_LINES = [
    "/GstPipeline:pipeline0/GstFPSDisplaySink:fps.GstGhostPad:sink.GstProxyPad:proxypad1: "
    f"caps = {CAPS_D3D12}",
    f"{SINK_ELEMENT}.GstPad:sink: caps = {CAPS_D3D12}",
    f"/GstPipeline:pipeline0/GstFPSDisplaySink:fps/GstFakeVideoSink:sink.GstGhostPad:sink: caps = {CAPS_D3D12}",
    f"/GstPipeline:pipeline0/GstFPSDisplaySink:fps.GstGhostPad:sink: caps = {CAPS_D3D12}",
]
QOS_LINE = (
    'Got message #117 from element "dec" (qos): GstMessageQOS, live=(boolean)false, '
    "running-time=(guint64)50000000, stream-time=(guint64)50000000, timestamp=(guint64)50000000, "
    "duration=(guint64)18446744073709551615, jitter=(gint64)24503533, "
    "proportion=(double)1.152715171108607, quality=(int)1000000, format=(GstFormat)buffers, "
    "processed=(guint64)4, dropped=(guint64)1;"
)
CONTEXT_LINE = r"""Got context from element 'dec': gst.d3d12.device.handle=context, device=(GstD3D12Device)"\(GstD3D12Device\)\ d3d12device0-1", adapter-index=(uint)0, adapter-luid=(gint64)129573, device-id=(uint)30032, vendor-id=(uint)4098, description=(string)"AMD\ Radeon\ RX\ 9070\ XT";"""


# --- fpsdisplaysink last-message ---------------------------------------------------------------

def test_fps_message_current_average_format():
    assert soak.parse_fps_message(FPS_LINE) == {
        "element": "/GstPipeline:pipeline0/GstFPSDisplaySink:fps",
        "rendered": 62, "dropped": 0, "current_fps": 61.89, "average_fps": 61.89,
        "drop_rate": None,
    }


def test_fps_message_drop_interval_format():
    record = soak.parse_fps_message(FPS_DROP_LINE)
    assert (record["rendered"], record["dropped"]) == (4, 4)
    assert record["current_fps"] == 2.25
    assert record["drop_rate"] == 2.25
    assert record["average_fps"] is None


def test_fps_message_smoke_run_line_and_comma_decimal_locale():
    line = ("/GstPipeline:pipeline0/GstFPSDisplaySink:fpsdisplaysink0: last-message = "
            "rendered: 786, dropped: 0, current: 1569.64, average: 1569.64")
    assert soak.parse_fps_message(line)["current_fps"] == pytest.approx(1569.64)
    comma = line.replace("1569.64", "1569,64")  # constructed: comma decimal separator
    assert soak.parse_fps_message(comma)["average_fps"] == pytest.approx(1569.64)


@pytest.mark.parametrize("line", [
    "/GstPipeline:pipeline0/GstFPSDisplaySink:fps: last-message = Max-fps: 61.89, Min-fps: 59.49",
    f"{SINK_ELEMENT}: last-message = chain   ******* (sink:sink) (0 bytes, dts: none, "
    "pts: 0:00:01.000000000)",
    DEC_SRC_LINE,
    f"{SINK_ELEMENT}: sync = true",
    "Setting pipeline to PLAYING ...",
])
def test_fps_message_ignores_other_lines(line):
    assert soak.parse_fps_message(line) is None


# --- caps extraction ---------------------------------------------------------------------------

def test_caps_line_decoder_src():
    event = soak.parse_caps_line(DEC_SRC_LINE)
    assert event["element_name"] == "dec"
    assert event["pad_name"] == "src"
    assert event["ghost"] is False
    assert event["caps"] == CAPS_D3D12


def test_caps_line_ghost_proxy_chain():
    event = soak.parse_caps_line(SINK_CHAIN_LINES[0])
    assert event["element_path"] == "/GstPipeline:pipeline0/GstFPSDisplaySink:fps"
    assert event["pad_name"] == "proxypad1"
    assert event["ghost"] is True


@pytest.mark.parametrize("line", [f"{SINK_ELEMENT}: sync = true", FPS_LINE, QOS_LINE])
def test_caps_line_ignores_other_lines(line):
    assert soak.parse_caps_line(line) is None


def test_decoder_and_innermost_sink_caps_from_captured_run():
    lines = [PARSE_SRC_LINE, DEC_SRC_LINE, CAPSFILTER_LINE, *SINK_CHAIN_LINES]
    events = [soak.parse_caps_line(line) for line in lines]
    assert all(events)
    assert soak.decoder_src_caps(events) == [CAPS_D3D12]
    sink = soak.final_sink_caps(events)
    assert sink == {"element_path": SINK_ELEMENT, "caps": [CAPS_D3D12]}
    assert soak.all_d3d12(sink["caps"]) is True


def test_download_before_the_sink_is_caught():
    system_caps = CAPS_D3D12.replace("video/x-raw(memory:D3D12Memory)", "video/x-raw")
    lines = [DEC_SRC_LINE, f"{SINK_ELEMENT}.GstPad:sink: caps = {system_caps}"]  # constructed
    events = [soak.parse_caps_line(line) for line in lines]
    assert soak.all_d3d12(soak.decoder_src_caps(events)) is True
    assert soak.all_d3d12(soak.final_sink_caps(events)["caps"]) is False


def test_renegotiation_away_from_d3d12_fails_the_sink_check():
    system_caps = CAPS_D3D12.replace("(memory:D3D12Memory)", "")
    lines = [f"{SINK_ELEMENT}.GstPad:sink: caps = {CAPS_D3D12}",
             f"{SINK_ELEMENT}.GstPad:sink: caps = {system_caps}"]  # constructed
    sink = soak.final_sink_caps([soak.parse_caps_line(line) for line in lines])
    assert len(sink["caps"]) == 2
    assert soak.all_d3d12(sink["caps"]) is False


def test_no_sink_caps_is_not_d3d12():
    assert soak.final_sink_caps([]) == {"element_path": None, "caps": []}
    assert soak.all_d3d12([]) is False


# --- other output lines ------------------------------------------------------------------------

def test_qos_message():
    assert soak.parse_qos_message(QOS_LINE) == {"element": "dec", "processed": 4, "dropped": 1}
    assert soak.parse_qos_message(
        'Got message #62 from element "parse" (latency): no message details') is None


@pytest.mark.parametrize("line, expected", [
    ("0:00:00.349719200      58892      66084 WARN                 qtdemux "
     "qtdemux.c:11589:qtdemux_parse_segments:<demux> Segment 0  extends to 0:00:15.354000000 "
     "past the end of the declared movie duration 0:00:15.350000000 movie segment will be "
     "extended", True),
    ("WARNING: from element /GstPipeline:pipeline0/GstFPSDisplaySink:fps/GstFakeVideoSink:sink/"
     "GstFakeSink:sink: A lot of buffers are being dropped.", True),
    ("ERROR: from element /GstPipeline:pipeline0/GstFileSrc:filesrc0: Resource not found.",
     True),  # constructed
    ("0:00:00.100000000      58892      66084 INFO             GST_INIT gst.c:100:init_pre: "
     "Initializing GStreamer Core Library version 1.28.7", False),  # constructed
    (QOS_LINE, False),
    ("Setting pipeline to PAUSED ...", False),
])
def test_error_or_warning_detection(line, expected):
    assert soak.is_error_or_warning(line) is expected


def test_d3d12_device_context_and_counter_luid():
    device = soak.parse_d3d12_device_context(CONTEXT_LINE)
    assert device == {"adapter_index": 0, "adapter_luid": 129573, "device_id": 30032,
                      "vendor_id": 4098, "description": "AMD Radeon RX 9070 XT"}
    assert soak.luid_instance_key(device["adapter_luid"]) == "0x00000000_0x0001fa25"
    assert soak.parse_d3d12_device_context(QOS_LINE) is None


def test_clock_times_and_framerate():
    assert soak.parse_execution_time("Execution ended after 0:00:04.985051400") == pytest.approx(4.9850514)
    assert soak.parse_execution_time("Setting pipeline to NULL ...") is None
    assert soak.parse_clock_time("Duration: 0:02:52.250000000") == pytest.approx(172.25)
    assert soak.parse_framerate(CAPS_D3D12) == 60.0
    assert soak.parse_framerate(None) is None


def test_percentile_and_slope():
    assert soak.percentile([], 50) is None
    assert soak.percentile([60.0, 59.0, 61.0, 58.0], 50) == pytest.approx(59.5)
    assert soak.percentile([float(v) for v in range(101)], 5) == pytest.approx(5.0)
    assert soak.linear_slope([0, 1, 2, 3], [10, 12, 14, 16]) == pytest.approx(2.0)
    assert soak.linear_slope([1], [5]) is None


def test_pipeline_string_quotes_spaced_values():
    tokens = soak.build_pipeline(Path(r"E:\Video Output E\clip one.mp4"), sync=True, eos_after=-1)
    text = soak.pipeline_string(tokens)
    assert 'location="E:/Video Output E/clip one.mp4"' in text
    assert 'video-sink="fakevideosink name=sink"' in text
    assert "sync=true" in text and "eos-after=-1" in text
    assert "d3d12videosink" not in text and "autovideosink" not in text


# --- verdict (synthetic passes; pins that unmeasured criteria fail) ----------------------------

MB = 1024 * 1024
CALIBRATED = {"gated_count_detected_drops": True, "drops_observed": 294, "completed": True,
              "stall": None, "pass": {"drops": {"gated": {"dropped": 294}}}}


def _pass(index, kind, *, rendered=10_000, gated=0, ws_start=140.0, ws_end=140.5, exit_code=0,
          at_sink=True):
    samples = [{"t_s": 2.0 + i,
                "working_set_bytes": int((ws_start + (ws_end - ws_start) * i / 9) * MB),
                "private_bytes": int(130 * MB), "gpu_dedicated_by_luid": {"0x0_0x1": int(117 * MB)}}
               for i in range(10)]
    return {
        "index": index, "kind": kind, "soak_offset_s": 20.0 * index, "exit_code": exit_code,
        "timed_out": False, "wall_s": 12.0, "execution_ended_after_s": 11.5,
        "d3d12_memory_at_sink": at_sink,
        "frames": {"expected": rendered, "rendered_at_last_fps_report": rendered,
                   "average_fps_at_last_report": 60.0},
        "drops": {"counts": [{"source": "qos_bus_messages", "element": "dec", "dropped": gated}],
                  "gated": {"dropped": gated}, "sink_conditions": {"sync": kind == "synced"}},
        "fpsdisplaysink_series": [{"current_fps": 60.0}, {"current_fps": 59.9}],
        "errors_warnings": [], "errors_warnings_total": 0,
        "memory": soak.summarize_pass_memory(samples, 1.5, 30.0, None),
    }


def _verdict(passes, calibration=CALIBRATED):
    summary = soak.summarize(passes, 480.0)
    return soak.build_verdict(passes, summary, calibration, interrupted=False), summary


def test_verdict_passes_for_a_clean_soak():
    passes = [_pass(1, "throughput"), _pass(2, "synced"), _pass(3, "synced"), _pass(4, "synced")]
    verdict, summary = _verdict(passes)
    assert verdict["pass"] is True, verdict["reasons"]
    assert all(reason.startswith("ok: ") for reason in verdict["reasons"])
    assert summary["drops"]["total_dropped"] == 0
    assert summary["memory"]["post_warmup"]["passes"] == [3, 4]


def test_calibration_stall_is_reported_beside_the_soak_result():
    passes = [_pass(1, "throughput"), _pass(2, "synced"), _pass(3, "synced")]
    stalled = {"gated_count_detected_drops": True, "drops_observed": 295, "completed": False,
               "stall": {"summary": "registered 295 gated drops but did not reach EOS"},
               "pass": {"drops": {"gated": {"dropped": 295}}}}
    verdict, _ = _verdict(passes, calibration=stalled)
    assert verdict["pass"] is True and verdict["soak_verdict"] == "pass"
    assert verdict["calibration"]["drops_observed"] == 295
    assert verdict["calibration"]["gated_count_detected_drops"] is True
    assert verdict["calibration"]["completed"] is False
    assert verdict["status"] == "soak PASS; calibration saw drops but stalled before EOS (open finding)"
    assert not any("did not register" in reason for reason in verdict["reasons"])

    blind = {"gated_count_detected_drops": False, "drops_observed": 0, "completed": True,
             "stall": None, "pass": {"drops": {"gated": {"dropped": 0}}}}
    verdict, _ = _verdict(passes, calibration=blind)
    assert "calibration saw no drops" in verdict["status"]


def test_verdict_drop_rate_limit():
    under = [_pass(1, "throughput"), _pass(2, "synced", gated=1), _pass(3, "synced")]
    over = [_pass(1, "throughput"), _pass(2, "synced", gated=25), _pass(3, "synced")]
    assert _verdict(under)[0]["pass"] is True      # 1 of ~20k frames
    assert _verdict(over)[0]["pass"] is False      # 25 of ~20k frames > 0.1 %


def test_verdict_fails_on_growth_after_warmup_and_when_growth_is_unmeasured():
    leaking = [_pass(1, "throughput"), _pass(2, "synced"), _pass(3, "synced", ws_end=220.0)]
    verdict, summary = _verdict(leaking)
    assert verdict["pass"] is False
    assert summary["memory"]["post_warmup"]["working_set_growth_mb"] > 64
    single = [_pass(1, "throughput"), _pass(2, "synced")]
    verdict, summary = _verdict(single)
    assert verdict["pass"] is False and summary["memory"]["post_warmup"] is None


def test_verdict_fails_on_exit_code_or_download_before_sink():
    passes = [_pass(1, "throughput"), _pass(2, "synced", exit_code=1), _pass(3, "synced")]
    assert _verdict(passes)[0]["pass"] is False
    passes = [_pass(1, "throughput", at_sink=False), _pass(2, "synced"), _pass(3, "synced")]
    assert _verdict(passes)[0]["pass"] is False


def test_inspect_property_default():
    text = ("  max-lateness        : Maximum number of nanoseconds that a buffer can be late\n"
            "                        flags: readable, writable\n"
            "                        Integer64. Range: -1 - 9223372036854775807 Default: 5000000 \n"
            "  qos                 : Generate Quality-of-Service events upstream\n"
            "                        flags: readable, writable\n"
            "                        Boolean. Default: true\n")
    assert soak.inspect_property_default(text, "max-lateness") == "5000000"
    assert soak.inspect_property_default(text, "qos") == "true"
    assert soak.inspect_property_default(text, "sync") is None
