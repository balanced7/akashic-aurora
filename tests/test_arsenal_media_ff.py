"""arsenal.media.ff + the verb table: finding ffmpeg, its caps, filter-path escaping, the CLI's refusals."""
from __future__ import annotations

import os
import subprocess

import pytest

from arsenal.media import __main__ as media_main
from arsenal.media import ff


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv(ff.STATE_ENV, str(tmp_path / "state"))
    ff._located.clear()
    yield tmp_path / "state"
    ff._located.clear()


def _house_ffmpeg():
    """The real ffmpeg this machine uses, found with the default state (skip when there is none)."""
    try:
        return ff.locate(refresh=True)
    except ff.MediaError:
        pytest.skip("no ffmpeg on this machine")


def test_env_accepts_a_folder_and_finds_ffprobe_beside_it(state, tmp_path, monkeypatch):
    folder = tmp_path / "bin"
    folder.mkdir()
    exe = ".exe" if os.name == "nt" else ""
    (folder / f"ffmpeg{exe}").write_bytes(b"")
    (folder / f"ffprobe{exe}").write_bytes(b"")
    monkeypatch.setenv(ff.FFMPEG_ENV, str(folder))
    loc = ff.locate(refresh=True)
    assert loc["source"] == "env"
    assert loc["ffmpeg"] == str(folder / f"ffmpeg{exe}")
    assert loc["ffprobe"] == str(folder / f"ffprobe{exe}")


def test_env_pointing_nowhere_refuses_loudly(state, tmp_path, monkeypatch):
    monkeypatch.setenv(ff.FFMPEG_ENV, str(tmp_path / "missing.exe"))
    with pytest.raises(ff.MediaError, match=ff.FFMPEG_ENV):
        ff.locate(refresh=True)


def test_saved_config_beats_path(state, tmp_path, monkeypatch):
    exe = ".exe" if os.name == "nt" else ""
    saved = tmp_path / "saved" / f"ffmpeg{exe}"
    saved.parent.mkdir()
    saved.write_bytes(b"")
    ff._write_json(ff.config_path(), {"ffmpeg": str(saved)})
    monkeypatch.delenv(ff.FFMPEG_ENV, raising=False)
    monkeypatch.setattr(ff.shutil, "which", lambda name: f"C:/on/path/{name}{exe}")
    loc = ff.locate(refresh=True)
    assert (loc["source"], loc["ffmpeg"], loc["ffprobe"]) == ("config", str(saved), None)
    with pytest.raises(ff.MediaError, match="no ffprobe"):
        ff.ffprobe()


def test_house_caps_report_what_the_primitives_need():
    loc = _house_ffmpeg()
    if loc["source"] != "config":
        pytest.skip("the house build is not saved here (run `py -m arsenal.media doctor --save`)")
    c = ff.caps()
    for name in ("hevc_amf", "h264_amf", "libx264"):
        assert c["encoders"][name], name
    for name in ("scdet", "ebur128", "ass", "loudnorm", "silencedetect"):
        assert c["filters"][name], name
    assert "d3d11va" in c["hwaccels"]


def test_has_filter_answers_for_any_name_the_build_has():
    _house_ffmpeg()
    assert ff.has_filter("scdet") and ff.has_filter("movie")      # movie is not watched, but the build has it
    assert not ff.has_filter("no_such_filter_anywhere")
    assert ff.has_encoder("aac") and not ff.has_encoder("no_such_encoder")


def test_quick_id_sees_the_middle_of_a_file(tmp_path):
    from arsenal.media.receipt import quick_id
    mib = 1 << 20
    a, b = tmp_path / "a.bin", tmp_path / "b.bin"
    a.write_bytes(b"H" * mib + b"x" * (3 * mib) + b"T" * mib)
    b.write_bytes(b"H" * mib + b"y" * (3 * mib) + b"T" * mib)   # same size, head and tail; different middle
    assert quick_id(a) != quick_id(b)
    assert quick_id(a) == quick_id(a)


def _burn(tmp_path, sub_arg):
    out = tmp_path / "burn.png"
    return ff.run(["-f", "lavfi", "-i", "color=c=black:s=320x240:d=1", "-vf", sub_arg, "-frames:v", "1", "-y",
                   str(out)], check=False), out


def test_filter_path_survives_a_drive_colon_and_a_space(tmp_path):
    _house_ffmpeg()
    if not ff.has_filter("subtitles"):
        pytest.skip("this ffmpeg has no libass")
    folder = tmp_path / "a b"
    folder.mkdir()
    ass = folder / "x.srt"
    ass.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
    good, out = _burn(tmp_path, f"subtitles=filename={ff.filter_path(ass)}")
    assert good.returncode == 0, good.stderr[-400:]
    assert out.stat().st_size > 0
    bad, _ = _burn(tmp_path, f"subtitles={str(ass)}")
    assert bad.returncode != 0


def test_filter_path_refuses_an_apostrophe(tmp_path):
    with pytest.raises(ff.MediaError, match="apostrophe"):
        ff.filter_path(tmp_path / "Daniel's clip.ass")


def test_run_raises_with_argv_and_stderr_tail():
    _house_ffmpeg()
    with pytest.raises(ff.MediaError) as exc:
        ff.run(["-i", "definitely-not-a-file.mp4", "-f", "null", "-"])
    assert exc.value.argv and "definitely-not-a-file.mp4" in exc.value.argv
    assert "definitely-not-a-file" in str(exc.value)


def test_popen_streams_stdout_and_keeps_stderr_off_the_pipe():
    _house_ffmpeg()
    proc = ff.popen(["-f", "lavfi", "-i", "color=c=red:s=16x16:d=0.2:r=10", "-f", "rawvideo", "-pix_fmt", "rgb24",
                     "-"])
    data = proc.stdout.read()
    assert ff.finish(proc) == 0
    assert len(data) == 16 * 16 * 3 * 2


def test_cli_lists_verbs_and_refuses_unknown_ones(capsys):
    assert media_main.main([]) == 0
    assert "contact sheet" in capsys.readouterr().out
    assert media_main.main(["no-such-verb"]) == 2


def test_cli_reports_a_verb_whose_module_is_not_built(monkeypatch, capsys):
    monkeypatch.setitem(media_main.VERBS, "ghost", ("ghost_module_never_written", "x"))
    assert media_main.main(["ghost"]) == 3
    assert "not built yet" in capsys.readouterr().err


def test_doctor_runs_as_a_subprocess(state):
    _house_ffmpeg()
    env = dict(os.environ, PYTHONUTF8="1")
    out = subprocess.run(["py" if os.name == "nt" else "python3", "-m", "arsenal.media", "doctor"],
                         capture_output=True, text=True, env=env, cwd=str(ff._REPO_ROOT), timeout=120)
    assert out.returncode == 0, out.stderr
    assert "ffmpeg" in out.stdout
