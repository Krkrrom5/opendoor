"""
Coder — streaming + reflection loop. Inspired by aider.base_coder.
"""
from __future__ import annotations
import ast, traceback
from pathlib import Path
from opendoor.engine.extractor import extract_files, apply_files
from opendoor.ui.terminal import WaitingSpinner


class Coder:
    max_reflections = 3

    def __init__(self, llm, io, session, stream=True, auto_apply=True, verbose=False):
        self.llm = llm
        self.io = io
        self.session = session
        self.stream = stream
        self.auto_apply = auto_apply
        self.verbose = verbose
        self.partial = ""
        self.reflected_message = None
        self.num_reflections = 0
        self.commands = None  # set after init

    def run_one(self, user_message: str):
        """Process one user message — with reflection loop like aider."""
        self.session.add_user_message(user_message)
        self.reflected_message = None
        self.num_reflections = 0
        message = user_message

        while message:
            self.reflected_message = None
            self._send(message)
            if not self.reflected_message:
                break
            if self.num_reflections >= self.max_reflections:
                self.io.tool_warning(f"Max reflections ({self.max_reflections}) reached.")
                break
            self.num_reflections += 1
            self.io.tool_output(f"\n  ↻ Reflection {self.num_reflections}…\n")
            message = self.reflected_message

        self.session.commit_messages()

    def _send(self, text: str):
        messages = self._build_messages(text)

        if self.verbose:
            for m in messages:
                self.io.tool_output(f"[{m['role']}] {m['content'][:100]}…")

        spinner = WaitingSpinner("Waiting for AI…")
        spinner.start()

        self.partial = ""
        md_stream = None
        interrupted = False
        first_chunk = True

        try:
            if self.stream:
                md_stream = self.io.get_assistant_stream()

            for chunk in self.llm.send(messages, stream=self.stream):
                if first_chunk:
                    spinner.stop()
                    first_chunk = False
                self.partial += chunk
                if md_stream:
                    md_stream.update(chunk)

            if md_stream:
                md_stream.finish()
            elif self.partial:
                self.io.assistant_output(self.partial, stream=False)

        except KeyboardInterrupt:
            spinner.stop()
            if md_stream:
                try: md_stream.finish()
                except: pass
            interrupted = True
            self.io.tool_warning("Interrupted.")
        except Exception as e:
            spinner.stop()
            if md_stream:
                try: md_stream.finish()
                except: pass
            self.io.tool_error(f"LLM error: {e}")
            if self.verbose:
                self.io.tool_error(traceback.format_exc())
            return
        finally:
            spinner.stop()

        if not self.partial or interrupted:
            return

        self.io.ai_output_log(self.partial)
        self.session.add_assistant_message(self.partial)

        if self.auto_apply:
            self._apply_response(self.partial)

    def _apply_response(self, response: str):
        """Extract files from AI response and write them. Like aider.apply_updates."""
        known = self.session.get_rel_files()
        files = extract_files(response, known_files=known)
        if not files:
            if "```" in response:
                self.io.tool_warning("Found code blocks but no FILE: tags or filenames detected. I can't apply these changes automatically.")
            return

        self.io.tool_output(f"\n  Found {len(files)} file(s):\n")
        
        # Confirmation prompt
        if not self.io.confirm_ask("Apply these changes? (Yes - No create this project)", "y"):
            self.io.tool_output("  Discarded.")
            return

        written = apply_files(files, self.session.root, io=self.io)

        for abs_path in written:
            self.session.abs_fnames.add(abs_path)

        self.io.set_files(self.session.get_all_project_files())

        # Auto-fix syntax errors (reflection)
        py_files = [f for f in written if f.endswith(".py")]
        if py_files:
            errors = []
            for fp in py_files:
                try:
                    ast.parse(Path(fp).read_text(encoding="utf-8"))
                except SyntaxError as e:
                    errors.append(f"{self.session.rel(fp)}: line {e.lineno}: {e.msg}")
            if errors:
                self.io.tool_warning("Syntax errors:\n" + "\n".join(errors))
                self.reflected_message = (
                    "There are syntax errors:\n" + "\n".join(errors) +
                    "\nPlease fix them and provide the corrected files."
                )

    def _build_messages(self, user_text: str) -> list:
        """Build full message list for LLM. Like aider.format_messages."""
        msgs = [{"role":"system","content":self.session.build_system_prompt()}]
        for m in self.session.done_messages[-20:]:
            msgs.append(m)
        msgs.append({"role":"user","content":user_text})
        return msgs

    def suggest_files(self, user_message: str) -> list:
        return self.session.suggest_files(user_message)
