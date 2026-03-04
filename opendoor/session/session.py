"""Session — file management and context building. مستوحى من aider.base_coder."""
import re
from pathlib import Path


SKIP_DIRS = {".git","__pycache__","node_modules",".venv","venv",
             ".env","dist","build",".tox",".pytest_cache",".mypy_cache"}
SKIP_EXTS = {".pyc",".pyo",".pyd",".so",".dll",".exe",
             ".jpg",".jpeg",".png",".gif",".ico",".svg",
             ".zip",".tar",".gz",".lock","db",".sqlite"}


class Session:
    def __init__(self, root="."):
        self.root = str(Path(root).resolve())
        self.mode = "code"
        self.abs_fnames: set = set()
        self.read_only_fnames: set = set()
        self.done_messages: list = []
        self.cur_messages: list = []

    def add_file(self, path: str):
        p = Path(path) if Path(path).is_absolute() else Path(self.root) / path
        p = p.resolve()
        if not p.exists(): return False, f"Not found: {path}"
        if not p.is_file(): return False, f"Not a file: {path}"
        abs_p = str(p)
        if abs_p in self.abs_fnames: return False, f"Already in session: {p.name}"
        self.read_only_fnames.discard(abs_p)
        self.abs_fnames.add(abs_p)
        return True, f"Added: {self.rel(abs_p)}"

    def add_files_by_glob(self, pattern: str):
        results = []
        try:
            matches = list(Path(self.root).glob(pattern))
        except Exception as e:
            return [(False, str(e))]
        if not matches:
            return [(False, f"No match: {pattern}")]
        for p in sorted(matches):
            if p.is_file():
                results.append(self.add_file(str(p)))
        return results

    def drop_file(self, name: str):
        matched = [f for f in self.abs_fnames if name in f]
        if not matched:
            matched_ro = [f for f in self.read_only_fnames if name in f]
            for m in matched_ro:
                self.read_only_fnames.discard(m)
            return (True, f"Dropped {len(matched_ro)}") if matched_ro else (False, f"No match: {name}")
        for m in matched:
            self.abs_fnames.discard(m)
        return True, f"Dropped {len(matched)} file(s)"

    def drop_all(self):
        self.abs_fnames.clear()
        self.read_only_fnames.clear()

    def get_all_project_files(self) -> list:
        result = []
        root = Path(self.root)
        for p in root.rglob("*"):
            # Check if any path part is in SKIP_DIRS
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            
            # Strict safety for Build mode: hide the assistant's own code
            if self.mode == "build" and "opendoor" in p.parts:
                continue

            if p.suffix in SKIP_EXTS:
                continue
            if p.is_file():
                try:
                    result.append(str(p.relative_to(root)))
                except ValueError:
                    pass
        return sorted(result)

    def get_rel_files(self) -> list:
        return sorted(self.rel(f) for f in self.abs_fnames)

    def get_files_content(self) -> str:
        prompt = ""
        for fname in sorted(self.abs_fnames):
            try:
                content = Path(fname).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            rel = self.rel(fname)
            prompt += f"\n{rel}\n```\n{content}\n```\n"
        return prompt

    def get_read_only_content(self) -> str:
        prompt = ""
        for fname in sorted(self.read_only_fnames):
            try:
                content = Path(fname).read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            prompt += f"\n{self.rel(fname)} (read-only)\n```\n{content}\n```\n"
        return prompt

    def write_file(self, path: str, content: str):
        p = Path(path) if Path(path).is_absolute() else Path(self.root) / path
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            self.abs_fnames.add(str(p.resolve()))
            return True, f"Written: {self.rel(str(p.resolve()))}"
        except Exception as e:
            return False, f"Write failed: {e}"

    def add_user_message(self, text: str):
        self.cur_messages.append({"role":"user","content":text})

    def add_assistant_message(self, text: str):
        self.cur_messages.append({"role":"assistant","content":text})

    def commit_messages(self):
        self.done_messages.extend(self.cur_messages)
        self.cur_messages = []

    def clear_history(self):
        self.cur_messages = []
        self.done_messages = []

    def get_history(self) -> list:
        return self.done_messages + self.cur_messages

    def build_system_prompt(self) -> str:
        files_content = self.get_files_content()
        read_only = self.get_read_only_content()
        prompt = (
            "You are OpenDoor, an expert AI coding assistant.\n"
            "You have direct access to the user's filesystem through powerful tools.\n\n"
            "## RULES:\n"
            "1. You MUST help the user by creating, editing, and debugging files.\n"
            "2. NEVER apologize for being an AI or claim you cannot access files.\n"
            "3. To write/create a file, use EXACTLY this format:\n"
            "   FILE: path/filename.ext\n"
            "   ```\n"
            "   (complete file content here)\n"
            "   ```\n"
            "4. ALWAYS provide the FULL file content — never truncated.\n"
            "5. CRITICAL: NEVER modify or suggest changes to files in the 'opendoor/' directory unless the user explicitly asks to edit the assistant's own code.\n"
            "6. CRITICAL: If the user asks for a NEW project, ALWAYS create a NEW DEDICATED FOLDER.\n"
            "   Example: If user says 'create a draw app', you MUST use paths like:\n"
            "   FILE: draw-app/package.json\n"
            "   FILE: draw-app/src/main.js\n"
            "   Do NOT write files directly to the root '.' unless it's a single file request.\n"
            "6. CRITICAL: Every code block MUST be preceded by the 'FILE: path' tag on its own line.\n"
            "   Example:\n"
            "   FILE: folder/file.py\n"
            "   ```python\n"
            "   code here\n"
            "   ```\n\n"
        )
        if self.mode == "build":
            prompt += (
                "\nCRITICAL BUILD MODE RULES:\n"
                "- YOU ARE AN EXPERT BUILDER. Your goal is to create complete, working projects.\n"
                "- NEVER say 'I cannot access files' or 'I don't have access'. You HAVE access through tools.\n"
                "- If the user asks about a file/folder NOT in the 'Currently editing' list below, simply say 'I don't see that in my current session, can you add it using /add?' or similar.\n"
                "- ALWAYS use the 'FILE: path' format for ALL code output.\n"
                "- NO conversational filler. NO introductory text. Just the files.\n"
                "- If creating a new project, use a dedicated subfolder (e.g. PROJECT/file.py).\n"
                "- Every file must be complete. No placeholders.\n"
            )

        if files_content:
            prompt += "\n## Files in session (you can edit these):\n" + files_content + "\n"
        if read_only:
            prompt += "## Read-only context:\n" + read_only + "\n"
        if self.abs_fnames:
            names = ", ".join(sorted(self.rel(f) for f in self.abs_fnames))
            prompt += f"\nCurrently editing: {names}\n"
        return prompt

    def suggest_files(self, user_message: str) -> list:
        # Split by non-alphanumeric, but keep path separators if possible? 
        # Actually simplified: just lower case and look for overlaps.
        msg_low = user_message.lower()
        words = [w for w in re.split(r"\W+", msg_low) if len(w) >= 3]
        
        all_files = self.get_all_project_files()
        in_session = set(self.get_rel_files())
        suggestions = []
        
        for f in all_files:
            if f in in_session:
                continue
            
            # Safety: In build mode, don't suggest internal opendoor files
            if self.mode == "build" and ("opendoor" in Path(f).parts):
                continue

            f_low = f.lower().replace("\\", "/") # normalize for search
            
            # Match if any word is in the path, or if the path is in the message
            if any(w in f_low for w in words) or (len(f_low) > 5 and f_low in msg_low):
                suggestions.append(f)
        
        # Sort by relevance: shorter paths (more likely root files) first
        suggestions.sort(key=lambda x: (len(Path(x).parts), len(x)))
        return suggestions[:10]

    def rel(self, abs_path: str) -> str:
        try:
            return str(Path(abs_path).relative_to(self.root))
        except ValueError:
            return abs_path
