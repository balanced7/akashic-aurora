#!/usr/bin/env python3
"""
Launch AI Stack — thin Tk launcher for BreakThrough stack_manager.

Double-click or run:  python launch_ai_stack.py

Frozen (PyInstaller): place ``Launch AI Stack.exe`` in ``E:\\AI-Setup`` or set
environment variable ``AI_SETUP_ROOT`` to your repo root. Uses ``python`` on PATH
for subprocess stack commands when frozen.
"""

from __future__ import annotations

import os
import queue
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import END, Button, Frame, Scrollbar, Text, Tk, messagebox, ttk

DEFAULT_CHAT_URL = os.environ.get("AI_STACK_CHAT_URL", "http://127.0.0.1:3000")
STACK_GUI_URL = os.environ.get("AI_STACK_GUI_URL", "http://127.0.0.1:8090")


def resolve_setup_root() -> Path:
    env = (os.environ.get("AI_SETUP_ROOT") or "").strip()
    if env:
        return Path(env).resolve()
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "stack_gui.py").exists() or (exe_dir / "stack_manager").is_dir():
            return exe_dir
    here = Path(__file__).resolve().parent
    if here.joinpath("stack_gui.py").exists():
        return here
    return Path(r"E:\AI-Setup")


def python_for_subprocess() -> str:
    if not getattr(sys, "frozen", False):
        return sys.executable
    for cand in (
        shutil.which("python"),
        shutil.which("py"),
    ):
        if cand:
            return cand
    return "python"


def _append_log(q: queue.Queue, widget: Text, line: str) -> None:
    q.put(line)


def _pump_queue(root: Tk, q: queue.Queue, widget: Text) -> None:
    try:
        while True:
            line = q.get_nowait()
            widget.insert(END, line + "\n")
            widget.see(END)
    except queue.Empty:
        pass
    root.after(200, lambda: _pump_queue(root, q, widget))


def run_cmd_stream(
    args: list[str],
    cwd: Path,
    q: queue.Queue,
    on_done,
) -> None:
    def _work():
        try:
            proc = subprocess.Popen(
                args,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            assert proc.stdout is not None
            for line in iter(proc.stdout.readline, ""):
                if line:
                    _append_log(q, None, line.rstrip())
            proc.wait(timeout=5)
            rc = proc.returncode
            _append_log(q, None, f"[exit {rc}]")
            on_done(rc)
        except Exception as e:
            _append_log(q, None, f"[error] {e}")
            on_done(-1)

    threading.Thread(target=_work, daemon=True).start()


class LaunchApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("Launch AI Stack")
        self.root.minsize(520, 420)
        self.setup_root = resolve_setup_root()
        self.q: queue.Queue = queue.Queue()
        self._busy = False

        top = Frame(self.root, padx=8, pady=8)
        top.pack(fill="x")

        ttk.Label(
            top,
            text=f"Repo: {self.setup_root}",
            wraplength=500,
        ).pack(anchor="w")

        btn_row = Frame(top)
        btn_row.pack(fill="x", pady=6)

        self.btn_start = Button(btn_row, text="Start full stack", command=self.on_start)
        self.btn_start.pack(side="left", padx=2)

        Button(btn_row, text="Status", command=self.on_status).pack(side="left", padx=2)
        Button(btn_row, text="Open Stack GUI", command=self.on_open_gui).pack(side="left", padx=2)
        Button(btn_row, text="Open Web Chat", command=self.on_open_chat).pack(side="left", padx=2)

        Button(btn_row, text="Stop stack", command=self.on_stop).pack(side="left", padx=12)

        log_frame = Frame(self.root)
        log_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        scroll = Scrollbar(log_frame)
        scroll.pack(side="right", fill="y")

        self.log = Text(log_frame, height=18, wrap="word", font=("Consolas", 9))
        self.log.pack(side="left", fill="both", expand=True)
        self.log.config(yscrollcommand=scroll.set)
        scroll.config(command=self.log.yview)

        self._log(f"Using Python for stack: {python_for_subprocess()}")
        self._log("Tip: set AI_SETUP_ROOT if this exe is not inside the AI-Setup folder.")

        _pump_queue(self.root, self.q, self.log)

    def _log(self, msg: str) -> None:
        self.q.put(msg)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.btn_start.config(state="disabled" if busy else "normal")

    def on_start(self) -> None:
        if self._busy:
            return
        if not (self.setup_root / "stack_manager").is_dir():
            messagebox.showerror(
                "Launch AI Stack",
                f"stack_manager package not found under:\n{self.setup_root}\n\n"
                "Place this exe in E:\\AI-Setup or set AI_SETUP_ROOT.",
            )
            return
        self._set_busy(True)
        self._log("--- Starting stack (python -m stack_manager.cli start) ---")
        py = python_for_subprocess()
        args = [py, "-m", "stack_manager.cli", "start"]

        def done(rc):
            self.root.after(0, lambda: self._set_busy(False))
            if rc == 0:
                self.root.after(0, lambda: messagebox.showinfo("Launch AI Stack", "Stack start finished (exit 0)."))
            else:
                self.root.after(
                    0,
                    lambda: messagebox.showwarning(
                        "Launch AI Stack",
                        f"Stack start exited with code {rc}. See log above.",
                    ),
                )

        run_cmd_stream(args, self.setup_root, self.q, done)

    def on_status(self) -> None:
        self._log("--- Status (python -m stack_manager.cli status) ---")
        py = python_for_subprocess()

        def done(_rc):
            pass

        run_cmd_stream([py, "-m", "stack_manager.cli", "status"], self.setup_root, self.q, done)

    def on_open_gui(self) -> None:
        webbrowser.open(STACK_GUI_URL)

    def on_open_chat(self) -> None:
        webbrowser.open(DEFAULT_CHAT_URL)

    def on_stop(self) -> None:
        if not messagebox.askyesno(
            "Stop stack",
            "This runs: python -m stack_manager.cli stop\n\n"
            "It stops registered services and terminates WSL (Ubuntu-Migrate).\n\n"
            "Continue?",
        ):
            return
        self._log("--- Stopping stack ---")
        py = python_for_subprocess()

        def done(_rc):
            self.root.after(0, lambda: messagebox.showinfo("Launch AI Stack", "Stop command finished."))

        run_cmd_stream([py, "-m", "stack_manager.cli", "stop"], self.setup_root, self.q, done)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    LaunchApp().run()


if __name__ == "__main__":
    main()
