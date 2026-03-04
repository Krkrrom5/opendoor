"""
InputOutput — Windows + Linux/Mac compatible. No readline import at top level.
"""
import sys
import os
import time

from opendoor.ui.terminal import (
    WaitingSpinner, print_markdown, rule, c,
    ACCENT, ERROR, WARNING, MUTED, INFO, BCYAN
)


def _try_setup_readline(files_ref: list):
    """Try to setup readline/pyreadline3. Returns rl module or None."""
    rl = None
    try:
        import readline as rl
    except ImportError:
        try:
            import pyreadline3 as rl
        except ImportError:
            return None

    history = os.path.expanduser("~/.opendoor_history")
    try:
        rl.set_history_length(1000)
        try:
            rl.read_history_file(history)
        except FileNotFoundError:
            pass
        import atexit
        atexit.register(lambda: _save_history(rl, history))
    except Exception:
        pass

    def completer(text, state):
        options = [f for f in files_ref if f.startswith(text)]
        return options[state] if state < len(options) else None

    try:
        rl.set_completer(completer)
        rl.parse_and_bind("tab: complete")
    except Exception:
        pass

    return rl


def _save_history(rl, path):
    try:
        rl.write_history_file(path)
    except Exception:
        pass


class InputOutput:
    def __init__(self, stream=True):
        self.stream = stream
        self._files = []
        self._rl = _try_setup_readline(self._files)

    def set_files(self, files: list):
        self._files.clear()
        self._files.extend(files)
        if self._rl:
            def completer(text, state):
                options = [f for f in self._files if f.startswith(text)]
                return options[state] if state < len(options) else None
            try:
                self._rl.set_completer(completer)
            except Exception:
                pass

    def get_input(self, prompt_text="> ") -> str:
        try:
            return input(c(prompt_text, ACCENT, bold=True))
        except EOFError:
            raise
        except KeyboardInterrupt:
            raise

    def rule(self):
        rule()

    def tool_output(self, *msgs, bold=False):
        if not msgs:
            print()
            return
        text = " ".join(str(m) for m in msgs)
        print(c(f"  {text}", INFO, bold=bold))

    def tool_error(self, msg=""):
        if msg:
            print(c(f"  ✗ {msg}", ERROR), file=sys.stderr)

    def tool_warning(self, msg=""):
        if msg:
            print(c(f"  ⚠ {msg}", WARNING))

    def user_input(self, text: str):
        print(c(f"\n  You › ", ACCENT, bold=True) + text)

    def assistant_output(self, text: str, stream=None):
        print()
        print_markdown(text)
        print()

    def get_assistant_stream(self):
        return StreamingOutput()

    def confirm_ask(self, question: str, default="y") -> bool:
        opts = c("(Y/n)", MUTED) if default.lower() == "y" else c("(y/N)", MUTED)
        try:
            ans = input(c(f"  {question} ", ACCENT) + opts + " ").strip().lower()
            return (ans or default[0]).startswith("y")
        except (EOFError, KeyboardInterrupt):
            return False

    def prompt_ask(self, question: str, default="") -> str:
        try:
            return input(c(f"  {question}: ", ACCENT)) or default
        except (EOFError, KeyboardInterrupt):
            return default

    def ai_output_log(self, text: str):
        pass

    def llm_started(self):
        pass


class StreamingOutput:
    def __init__(self):
        self._buf = ""
        self._started = False
        self._word_count = 0
        self._start_time = 0
        self._frame_idx = 0
        self._last_ui_update = 0
        self._last_was_space = True
        self._frames = [
            "░█        ", " ░█       ", "  ░█      ", "   ░█     ",
            "    ░█    ", "     ░█   ", "      ░█  ", "       ░█ ",
            "        ░█", "       ░█ ", "      ░█  ", "     ░█   ",
            "    ░█    ", "   ░█     ", "  ░█      ", " ░█       "
        ]

    def update(self, chunk: str):
        self._buf += chunk
        
        # Incremental word count (Low CPU)
        for char in chunk:
            is_space = char.isspace()
            if self._last_was_space and not is_space:
                self._word_count += 1
            self._last_was_space = is_space

        if not self._started:
            self._started = True
            self._start_time = time.time()
            print()
            
        now = time.time()
        # Throttle UI updates to ~15Hz (approx every 0.066s)
        if now - self._last_ui_update < 0.066:
            return
            
        self._last_ui_update = now
        elapsed = now - self._start_time
        frame = self._frames[self._frame_idx]
        self._frame_idx = (self._frame_idx + 1) % len(self._frames)
        
        status = f"\r  {c(frame, BCYAN)} {c('Thinking...', MUTED)} [{self._word_count} words | {elapsed:.1f}s]  "
        sys.stdout.write(status)
        sys.stdout.flush()

    def finish(self):
        if self._started:
            # Clear the live status line
            sys.stdout.write("\r" + " " * 60 + "\r")
            sys.stdout.flush()
            print_markdown(self._buf)
            print()
        self._buf = ""
        self._started = False
        self._word_count = 0
        self._frame_idx = 0
