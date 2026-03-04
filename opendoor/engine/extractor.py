"""
Extracts FILE: blocks and fenced code from AI responses.
Writes them to disk. Inspired by aider editblock_coder.
"""
import re
from pathlib import Path

FILE_HEADER = re.compile(r"^(?:FILE|file|File)\s*:\s*(.+?)\s*$", re.MULTILINE)
FENCE_OPEN  = re.compile(r"^```(\w*)\s*$", re.MULTILINE)
FENCE_CLOSE = re.compile(r"^```\s*$", re.MULTILINE)
PRE_FENCE   = re.compile(
    r"(?:^|\n)\*?\*?`?([A-Za-z0-9_./-]+\.[a-zA-Z]{1,8})`?\*?\*?\s*\n```",
    re.MULTILINE
)
EXT_MAP = {
    "python":"py","py":"py","javascript":"js","js":"js",
    "typescript":"ts","ts":"ts","jsx":"jsx","tsx":"tsx",
    "html":"html","css":"css","rust":"rs","go":"go",
    "java":"java","bash":"sh","shell":"sh","sh":"sh",
    "json":"json","yaml":"yaml","yml":"yml","toml":"toml",
    "sql":"sql","markdown":"md","md":"md","c":"c","cpp":"cpp",
}


def extract_files(response: str, known_files: list = None) -> dict:
    """Returns {filename: content} dict."""
    result = {}
    known = set(known_files or [])

    # Pass 1: FILE: path syntax
    parts = FILE_HEADER.split(response)
    if len(parts) > 1:
        i = 1
        while i < len(parts) - 1:
            fname = parts[i].strip().strip("`").strip()
            block = parts[i + 1]
            code = _first_fence(block)
            result[fname] = code if code is not None else block.strip()
            i += 2
        if result:
            return result

    # Pass 2: filename on line before fence (even more liberal)
    # Matches "main.js", "**main.js**", "File: main.js", "Create src/index.js with code:"
    # We allow up to 100 characters of text between the filename and the fence.
    PRE_FENCE_LIBERAL = re.compile(
        r"(?:(?:file|create|named|in|to|directory)\s+)?\*?\*?`?([\w./\\-]+\.[a-zA-Z]{1,8})`?\*?\*?.*?\n```",
        re.MULTILINE | re.IGNORECASE | re.DOTALL
    )
    
    # We need to manually verify the gap isn't too large
    for m in PRE_FENCE_LIBERAL.finditer(response):
        fname = m.group(1).strip()
        header_text = m.group(0)
        if len(header_text) > 150: continue # Skip if too much text between name and fence
        
        start = m.end()
        end_m = FENCE_CLOSE.search(response, start)
        if end_m:
            code = response[start:end_m.start()].lstrip("\n")
            result[fname] = code
    if result:
        return result

    # Pass 3: guess from fences
    for lang, code in _all_fences(response):
        guessed = _guess_fname(lang, code, known)
        if guessed:
            result[guessed] = code

    return result


def apply_files(files: dict, root: str, io=None) -> list:
    """Write files to disk. Returns list of abs paths written."""
    written = []
    for fname, content in files.items():
        p = Path(root) / fname
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            written.append(str(p.resolve()))
            if io: io.tool_output(f"Written: {fname}")
        except Exception as e:
            if io: io.tool_error(f"{fname}: {e}")
    return written


def _first_fence(text: str):
    m = FENCE_OPEN.search(text)
    if not m: return None
    start = m.end()
    end_m = FENCE_CLOSE.search(text, start)
    return text[start:end_m.start()].strip() if end_m else text[start:].strip()


def _all_fences(text: str):
    results, pos = [], 0
    while True:
        m = FENCE_OPEN.search(text, pos)
        if not m: break
        lang, start = m.group(1), m.end()
        end_m = FENCE_CLOSE.search(text, start)
        if not end_m: break
        results.append((lang, text[start:end_m.start()].strip()))
        pos = end_m.end()
    return results


def _guess_fname(lang: str, code: str, known: set) -> str:
    # Look for FILE: comment inside the code (top 5 lines)
    top_lines = "\n".join(code.splitlines()[:5])
    m = re.search(r"(?:#|//|--|/\*)\s*(?:FILE|file|File)\s*:\s*([A-Za-z0-9_./-]+\.[a-zA-Z]{1,8})", top_lines)
    if m:
        return m.group(1).strip()

    ext = EXT_MAP.get(lang.lower())
    if not ext: return None
    for f in known:
        if f.endswith("." + ext): return f
    if lang in ("python","py"):
        m = re.search(r"^(?:class|def)\s+(\w+)", code, re.MULTILINE)
        if m: return m.group(1).lower() + ".py"
    if lang in ("javascript","js"):
        m = re.search(r"^(?:export (?:default )?)?(?:class|function)\s+(\w+)", code, re.MULTILINE)
        if m: return m.group(1).lower() + ".js"
    return None
