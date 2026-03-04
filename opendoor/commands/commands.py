"""Commands — /add /drop /ls /run /diff /commit ... مستوحى من aider.commands."""
import subprocess, sys
from pathlib import Path


class SwitchMode(Exception):
    def __init__(self, mode): self.mode = mode


class Commands:
    def __init__(self, io, session, coder=None):
        self.io = io
        self.session = session
        self.coder = coder

    def is_command(self, inp: str) -> bool:
        return bool(inp) and inp.strip()[0] in "/!"

    def run(self, inp: str):
        inp = inp.strip()
        if inp.startswith("!"):
            return self.cmd_run(inp[1:].strip())
        parts = inp.split(None, 1)
        raw = parts[0].lstrip("/").replace("-","_")
        args = parts[1] if len(parts) > 1 else ""
        method = getattr(self, f"cmd_{raw}", None)
        if not method:
            all_cmds = [a[4:] for a in dir(self) if a.startswith("cmd_")]
            matches = [c for c in all_cmds if c.startswith(raw)]
            if len(matches) == 1:
                method = getattr(self, f"cmd_{matches[0]}")
            elif len(matches) > 1:
                self.io.tool_error(f"Ambiguous: {', '.join('/'+c for c in matches)}")
                return
            else:
                self.io.tool_error(f"Unknown command: /{raw}  (type /help)")
                return
        return method(args)

    def get_commands(self) -> list:
        return sorted("/"+a[4:].replace("_","-") for a in dir(self) if a.startswith("cmd_"))

    # ─── Commands ──────────────────────────────────────────────────────────

    def cmd_help(self, args):
        "Show all commands"
        self.io.tool_output("\nCommands:\n")
        for attr in sorted(dir(self)):
            if not attr.startswith("cmd_"): continue
            name = "/"+attr[4:].replace("_","-")
            doc = (getattr(self,attr).__doc__ or "").strip()
            self.io.tool_output(f"  {name:<22} {doc}")
        self.io.tool_output()

    def cmd_add(self, args):
        "Add file(s) to session   /add main.py   /add src/*.py"
        if not args.strip():
            self.io.tool_error("Usage: /add <file> [glob...]")
            return
        for token in args.split():
            if any(c in token for c in "*?"):
                results = self.session.add_files_by_glob(token)
            else:
                results = [self.session.add_file(token)]
            for ok, msg in (results if isinstance(results, list) else [results]):
                if ok: self.io.tool_output(f"  ✓ {msg}")
                else:  self.io.tool_error(f"  ✗ {msg}")
        self.io.set_files(self.session.get_all_project_files())

    def cmd_drop(self, args):
        "Remove file(s) from session   /drop main.py   /drop (all)"
        if not args.strip():
            self.session.drop_all()
            self.io.tool_output("Dropped all files.")
            return
        for token in args.split():
            ok, msg = self.session.drop_file(token)
            if ok: self.io.tool_output(f"  ✓ {msg}")
            else:  self.io.tool_error(f"  ✗ {msg}")

    def cmd_ls(self, args):
        "List all project files — shows what's in session"
        all_files = self.session.get_all_project_files()
        in_sess = set(self.session.get_rel_files())
        ro = set(self.session.rel(f) for f in self.session.read_only_fnames)
        self.io.tool_output(f"\nProject: {self.session.root}\n")
        if in_sess:
            self.io.tool_output("  [In session — editable]")
            for f in sorted(in_sess):
                self.io.tool_output(f"    ● {f}")
        if ro:
            self.io.tool_output("  [Read-only]")
            for f in sorted(ro):
                self.io.tool_output(f"    ○ {f}")
        other = [f for f in all_files if f not in in_sess and f not in ro]
        if other:
            self.io.tool_output(f"  [Not in session — {len(other)} files]")
            for f in other[:30]:
                self.io.tool_output(f"    · {f}")
            if len(other) > 30:
                self.io.tool_output(f"    … and {len(other)-30} more")
        self.io.tool_output()

    def cmd_files(self, args):
        "Alias for /ls"
        return self.cmd_ls(args)

    def cmd_clear(self, args):
        "Clear chat history"
        self.session.clear_history()
        self.io.tool_output("History cleared.")

    def cmd_reset(self, args):
        "Drop all files + clear history"
        self.session.drop_all()
        self.session.clear_history()
        self.io.tool_output("Reset complete.")

    def cmd_run(self, args):
        "Run a shell command   /run python main.py   or !python main.py"
        if not args.strip():
            self.io.tool_error("Usage: /run <command>")
            return
        self.io.tool_output(f"$ {args}")
        try:
            r = subprocess.run(args, shell=True, capture_output=True,
                               text=True, cwd=self.session.root, timeout=60)
            if r.stdout: self.io.tool_output(r.stdout.rstrip())
            if r.stderr: self.io.tool_warning(r.stderr.rstrip())
            if r.returncode != 0:
                self.io.tool_error(f"Exit code: {r.returncode}")
                # Offer to fix errors
                if self.coder and r.stderr:
                    fix = self.io.confirm_ask("Ask AI to fix this error?", "y")
                    if fix:
                        msg = f"Running `{args}` gave this error:\n```\n{r.stderr}\n```\nPlease fix it."
                        self.coder.run_one(msg)
        except subprocess.TimeoutExpired:
            self.io.tool_error("Timed out (60s)")
        except Exception as e:
            self.io.tool_error(str(e))

    def cmd_tokens(self, args):
        "Show context window usage estimate"
        files = self.session.get_files_content()
        hist = " ".join(m["content"] for m in self.session.get_history())
        sys_prompt = self.session.build_system_prompt()
        total_chars = len(sys_prompt) + len(hist)
        est = total_chars // 4
        self.io.tool_output(f"\nContext estimate: ~{est:,} tokens")
        self.io.tool_output(f"  Files: {len(self.session.abs_fnames)} ({len(files)//4:,} tok)")
        self.io.tool_output(f"  History: {len(self.session.get_history())} messages")
        self.io.tool_output()

    def cmd_diff(self, args):
        "Show git diff"
        self.cmd_run("git diff")

    def cmd_commit(self, args):
        "Git commit   /commit fix: update logic"
        msg = args.strip() or "opendoor: update"
        self.cmd_run(f'git add -A && git commit -m "{msg}"')

    def cmd_undo(self, args):
        "Undo last git commit"
        if self.io.confirm_ask("Undo last commit?", "n"):
            self.cmd_run("git reset --soft HEAD~1")

    def cmd_git(self, args):
        "Run any git command   /git log --oneline -5"
        self.cmd_run("git " + args)

    def cmd_der(self, args):
        "Switch AI provider and model"
        self.io.tool_output("\nSelect AI Provider:")
        self.io.tool_output("  1. Google Gemini")
        self.io.tool_output("  2. Ollama")
        
        choice = self.io.get_input("Choice [1-2]: ").strip()
        
        if choice == "1":
            from opendoor.api.gemini import GeminiLLM
            temp_llm = GeminiLLM()
            models = temp_llm.list_models()
            self.io.tool_output("\nSelect Gemini Model:")
            for i, m in enumerate(models, 1):
                self.io.tool_output(f"  {i}. {m}")
            
            m_choice = self.io.get_input(f"Choice [1-{len(models)}]: ").strip()
            try:
                idx = int(m_choice) - 1
                if 0 <= idx < len(models):
                    new_model = models[idx]
                    self.coder.llm = GeminiLLM(model=new_model)
                    self.io.tool_output(f"✓ Provider: Gemini ({new_model})")
                else:
                    self.io.tool_error("Invalid choice.")
            except ValueError:
                self.io.tool_error("Invalid input.")
                
        elif choice == "2":
            from opendoor.api.ollama import OllamaLLM
            temp_llm = OllamaLLM()
            models = temp_llm.list_models()
            if not models:
                self.io.tool_error("No Ollama models found. Is Ollama running?")
                return
            
            self.io.tool_output("\nSelect Ollama Model:")
            for i, m in enumerate(models, 1):
                self.io.tool_output(f"  {i}. {m}")
            
            m_choice = self.io.get_input(f"Choice [1-{len(models)}]: ").strip()
            try:
                idx = int(m_choice) - 1
                if 0 <= idx < len(models):
                    new_model = models[idx]
                    self.coder.llm = OllamaLLM(model=new_model)
                    self.io.tool_output(f"✓ Provider: Ollama ({new_model})")
                else:
                    self.io.tool_error("Invalid choice.")
            except ValueError:
                self.io.tool_error("Invalid input.")
        else:
            self.io.tool_error("Invalid provider choice.")

    def cmd_cd(self, args):
        "Change directory   /cd path/to/dir"
        path = args.strip()
        if not path:
            self.io.tool_error("Usage: /cd <path>")
            return
        
        target = Path(self.session.root) / path
        target = target.resolve()
        
        if not target.exists():
            self.io.tool_error(f"Directory not found: {path}")
            return
        if not target.is_dir():
            self.io.tool_error(f"Not a directory: {path}")
            return
            
        self.session.root = str(target)
        self.io.set_files(self.session.get_all_project_files())
        self.io.tool_output(f"✓ Root changed to: {self.session.root}")

    def cmd_mode(self, args):
        "Switch mode   /mode code|chat|ask|build"
        mode = args.strip().lower()
        if mode not in ("code","chat","ask","build"):
            self.io.tool_error("Modes: code | chat | ask | build")
            return
        raise SwitchMode(mode)

    def cmd_exit(self, args):
        "Exit OpenDoor"
        self.io.tool_output("Goodbye! 👋")
        sys.exit(0)

    def cmd_quit(self, args):
        "Exit OpenDoor"
        self.cmd_exit(args)
