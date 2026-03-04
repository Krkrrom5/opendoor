"""
Terminal utilities — ANSI colors, spinner, markdown printing.
Zero external dependencies — stdlib + pygments only.
Windows + Linux/Mac compatible.
"""
import os
import re
import sys
import threading
import time

from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
from pygments.formatters import Terminal256Formatter
from pygments.util import ClassNotFound

# ── Windows ANSI enable ─────────────────────────────────────────────────────
def _enable_windows_ansi():
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

_enable_windows_ansi()

# ── ANSI codes ──────────────────────────────────────────────────────────────
RESET    = "\033[0m"
BOLD     = "\033[1m"
DIM      = "\033[2m"
RED      = "\033[31m"
GREEN    = "\033[32m"
YELLOW   = "\033[33m"
CYAN     = "\033[36m"
BBLACK   = "\033[90m"
BRED     = "\033[91m"
BGREEN   = "\033[92m"
BYELLOW  = "\033[93m"
BCYAN    = "\033[96m"
BWHITE   = "\033[97m"

ACCENT   = BCYAN
SUCCESS  = BGREEN
WARNING  = BYELLOW
ERROR    = BRED
MUTED    = BBLACK
INFO     = BWHITE


_IS_TTY_CACHE = None
def _is_tty() -> bool:
    global _IS_TTY_CACHE
    if _IS_TTY_CACHE is None:
        _IS_TTY_CACHE = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    return _IS_TTY_CACHE

_WIDTH_CACHE = (80, 0.0)
def _term_width() -> int:
    global _WIDTH_CACHE
    now = time.time()
    if now - _WIDTH_CACHE[1] < 1.0:
        return _WIDTH_CACHE[0]
    try:
        w = os.get_terminal_size().columns
        _WIDTH_CACHE = (w, now)
        return w
    except Exception:
        return 80


def c(text: str, color: str, bold: bool = False) -> str:
    if not _is_tty():
        return text
    prefix = (BOLD if bold else "") + color
    return f"{prefix}{text}{RESET}"


def rule(color: str = MUTED):
    w = _term_width()
    print(c("─" * w, color))


def print_success(text: str): print(c(f"  ✓ {text}", SUCCESS))
def print_error(text: str):   print(c(f"  ✗ {text}", ERROR), file=sys.stderr)
def print_warning(text: str): print(c(f"  ⚠ {text}", WARNING))
def print_info(text: str):    print(c(f"  {text}", INFO))
def print_dim(text: str):     print(c(f"  {text}", MUTED))


def highlight_code(code: str, lang: str = "") -> str:
    try:
        lexer = get_lexer_by_name(lang) if lang else guess_lexer(code)
    except ClassNotFound:
        lexer = TextLexer()
    try:
        return highlight(code, lexer, Terminal256Formatter(style="monokai")).rstrip()
    except Exception:
        return code


def print_markdown(text: str):
    """Print Markdown with ANSI formatting + syntax-highlighted code blocks."""
    lines = text.split("\n")
    in_code = False
    code_lang = ""
    code_buf = []
    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("```"):
            if not in_code:
                in_code = True
                code_lang = line[3:].strip()
                code_buf = []
            else:
                in_code = False
                code = "\n".join(code_buf)
                highlighted = highlight_code(code, code_lang)
                w = min(_term_width() - 4, 80)
                border = c("  " + "─" * w, MUTED)
                print(border)
                for cl in highlighted.split("\n"):
                    print(c("  │ ", MUTED) + cl)
                print(border)
                code_buf = []
                code_lang = ""
            i += 1
            continue

        if in_code:
            code_buf.append(line)
            i += 1
            continue

        if line.startswith("### "):
            print(c(f"\n  {line[4:]}", ACCENT))
        elif line.startswith("## "):
            print(c(f"\n  {line[3:]}", ACCENT, bold=True))
        elif line.startswith("# "):
            w = _term_width() - 4
            txt = line[2:]
            pad = max(0, (w - len(txt)) // 2)
            print(c(f"\n  {'─'*pad} {txt} {'─'*pad}", ACCENT, bold=True))
        elif line.startswith("> "):
            print(c(f"  │ {line[2:]}", MUTED))
        elif re.match(r"^\s*[-*+]\s+", line):
            m = re.match(r"^(\s*)([-*+])\s+(.*)", line)
            if m:
                indent = "  " * (len(m.group(1)) // 2 + 1)
                print(f"{indent}{c('•', ACCENT)} {_inline(m.group(3))}")
        elif re.match(r"^\d+\.\s+", line):
            m = re.match(r"^(\d+)\.\s+(.*)", line)
            if m:
                print(f"  {c(m.group(1)+'.', ACCENT)} {_inline(m.group(2))}")
        elif line.strip() == "":
            print()
        else:
            print(f"  {_inline(line)}")
        i += 1


def _inline(text: str) -> str:
    if not _is_tty():
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        return text
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: c(m.group(1), BWHITE, bold=True), text)
    text = re.sub(r"\*(.+?)\*",     lambda m: c(m.group(1), BWHITE), text)
    text = re.sub(r"`([^`]+)`",     lambda m: c(m.group(1), BYELLOW), text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", lambda m: c(m.group(1), BCYAN), text)
    return text


# ── Spinner ─────────────────────────────────────────────────────────────────
class Spinner:
    last_frame_idx = 0

    def __init__(self, text: str):
        self.text = text
        self.start_time = time.time()
        self.last_update = 0.0
        self.visible = False
        self.is_tty = _is_tty()
        self.last_len = 0

        frames_ascii = [
            "#=        ","=#        "," =#       ","  =#      ",
            "   =#     ","    =#    ","     =#   ","      =#  ",
            "       =# ","        =#","        #=","       #= ",
            "      #=  ","     #=   ","    #=    ","   #=     ",
            "  #=      "," #=       ",
        ]
        if self.is_tty:
            t = str.maketrans("=#", "░█")
            self.frames = [f.translate(t) for f in frames_ascii]
            self.scan = "█"
        else:
            self.frames = frames_ascii
            self.scan = "#"
        self.frame_idx = Spinner.last_frame_idx

    def _hide_cursor(self):
        if sys.platform != "win32":
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

    def _show_cursor(self):
        if sys.platform != "win32":
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    def step(self, text=None):
        if text:
            self.text = text
        if not self.is_tty:
            return
        now = time.time()
        if not self.visible and now - self.start_time >= 0.4:
            self.visible = True
            self._hide_cursor()
        if not self.visible or now - self.last_update < 0.1:
            return
        self.last_update = now
        frame = self.frames[self.frame_idx]
        self.frame_idx = (self.frame_idx + 1) % len(self.frames)
        Spinner.last_frame_idx = self.frame_idx
        max_w = _term_width() - 2
        raw_line = frame + " " + self.text
        line = c(frame, ACCENT) + " " + c(self.text, MUTED)
        visible_len = len(raw_line[:max_w])
        pad = " " * max(0, self.last_len - visible_len)
        sys.stdout.write(f"\r{line}{pad}")
        self.last_len = visible_len
        scan_pos = frame.find(self.scan)
        if scan_pos >= 0:
            backs = visible_len + len(pad) - scan_pos
            sys.stdout.write("\b" * backs)
        sys.stdout.flush()

    def end(self):
        if self.visible and self.is_tty:
            sys.stdout.write("\r" + " " * (self.last_len + 5) + "\r")
            sys.stdout.flush()
            self._show_cursor()
        self.visible = False


class WaitingSpinner:
    """Background thread spinner. Use as context manager or start/stop."""
    def __init__(self, text="Waiting for AI…", delay=0.1):
        self.spinner = Spinner(text)
        self.delay = delay
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        while not self._stop.is_set():
            self.spinner.step()
            time.sleep(self.delay)
        self.spinner.end()

    def start(self):
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=0.5)
        self.spinner.end()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.stop()
