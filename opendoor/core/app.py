"""Main run loop — like aider.main."""
from __future__ import annotations
import os, sys, json
from pathlib import Path
from opendoor.api.gemini import GeminiLLM
from opendoor.api.ollama import OllamaLLM
from opendoor.commands.commands import Commands, SwitchMode
from opendoor.core.coder import Coder
from opendoor.io_layer.io import InputOutput
from opendoor.session.session import Session
from opendoor.ui.terminal import (
    c, rule, print_info, print_error, print_warning, print_success,
    ACCENT, SUCCESS, ERROR, WARNING, MUTED, INFO, BOLD, RESET, BCYAN, _term_width
)

BANNER = r"""
  ___                   ____                  
 / _ \ _ __   ___ _ __ |  _ \  ___   ___  _ __
| | | | '_ \ / _ \ '_ \| | | |/ _ \ / _ \| '__|
| |_| | |_) |  __/ | | | |_| | (_) | (_) | |   
 \___/| .__/ \___|_| |_|____/ \___/ \___/|_|   
      |_|                                       
"""

CONFIG_FILE = ".opendoor_config.json"

def _load_config():
    p = Path(CONFIG_FILE)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except: pass
    return {}

def _save_config(data):
    try:
        Path(CONFIG_FILE).write_text(json.dumps(data, indent=2), encoding="utf-8")
    except: pass



def _select_llm_interactively(io, config):
    if "provider" in config and "model" in config:
        msg = f"Use previous settings: {c(config['provider'], SUCCESS)} ({c(config['model'], SUCCESS)})?"
        if io.confirm_ask(msg, "y"):
            if config["provider"] == "Google Gemini":
                return GeminiLLM(model=config["model"])
            else:
                return OllamaLLM(model=config["model"])

    io.tool_output("\nSelect AI Provider:")
    io.tool_output(f"  {c('1', SUCCESS)}. Google Gemini")
    io.tool_output(f"  {c('2', SUCCESS)}. Ollama (Local)")
    
    choice = io.prompt_ask("Choice [1-2]").strip()
    
    if choice == "1":
        provider = "Google Gemini"
        temp_llm = GeminiLLM()
        models = temp_llm.list_models()
        io.tool_output("\nSelect Gemini Model:")
    else:
        provider = "Ollama"
        temp_llm = OllamaLLM()
        models = temp_llm.list_models()
        if not models:
            io.tool_error("No Ollama models found. Is Ollama running?")
            return None
        io.tool_output("\nSelect Ollama Model:")
        
    for i, m in enumerate(models, 1):
        io.tool_output(f"  {c(str(i), SUCCESS)}. {m}")
        
    m_choice = io.prompt_ask(f"Choice [1-{len(models)}]").strip()
    try:
        model_name = models[int(m_choice)-1]
    except:
        model_name = models[0]
        
    config["provider"] = provider
    config["model"] = model_name
    _save_config(config)

    io.tool_output(f"✓ Provider: {provider} ({model_name})")
    if provider == "Google Gemini":
        return GeminiLLM(model=model_name)
    return OllamaLLM(model=model_name)


def _select_mode_interactively(io, config):
    modes = ["code", "chat", "ask", "build"]
    
    if "mode" in config:
        msg = f"Use previous mode: {c(config['mode'], SUCCESS)}?"
        if io.confirm_ask(msg, "y"):
            return config["mode"]

    io.tool_output("\nSelect Mode:")
    for i, m in enumerate(modes, 1):
        desc = {
            "code": "Edit/Add code",
            "chat": "General chat",
            "ask": "Answer questions",
            "build": "Build project/feature"
        }.get(m, "")
        io.tool_output(f"  {c(str(i), SUCCESS)}. {m.capitalize():<5} — {desc}")
    
    choice = io.prompt_ask(f"Choice [1-{len(modes)}]").strip()
    mapping = {"1": "code", "2": "chat", "3": "ask", "4": "build"}
    mode = mapping.get(choice, "code")
    
    config["mode"] = mode
    _save_config(config)
    
    io.tool_output(f"✓ Mode set to: {mode}")
    return mode


def _project_summary(session, io):
    all_f = session.get_all_project_files()
    py  = sum(1 for f in all_f if f.endswith(".py"))
    js  = sum(1 for f in all_f if f.endswith((".js",".ts",".jsx",".tsx")))
    git = (Path(session.root)/".git").exists()
    w = _term_width()
    sep = c("─"*w, MUTED)
    print(sep)
    print(c(f"  Project  ", ACCENT, bold=True) + c(session.root, INFO))
    print(c(f"  Files    ", ACCENT) + c(f"{len(all_f)} total", INFO) +
          c(f"  (Python:{py}  JS/TS:{js})", MUTED))
    print(c(f"  Git      ", ACCENT) + (c("✓ repository", SUCCESS) if git else c("✗ none", MUTED)))
    print(sep)
    print()


def _suggest_and_offer(coder, user_msg, io):
    suggestions = coder.suggest_files(user_msg)
    in_session = set(coder.session.get_rel_files())
    new = [f for f in suggestions if f not in in_session]
    if new:
        print(c(f"  Suggested: ", MUTED) + c(", ".join(new[:5]), ACCENT))
        if io.confirm_ask("Add to session?", "y"):
            for f in new[:5]:
                ok, msg = coder.session.add_file(f)
                if ok: io.tool_output(f"  ✓ {msg}")


def run(root=".", files=None, model=None, stream=True, verbose=False, auto_apply=True):
    io = InputOutput(stream=stream)

    print(c(BANNER, ACCENT))
    print(c("  AI coding assistant", MUTED) +
          c("  type /help", ACCENT) + c(" for commands\n", MUTED))

    session = Session(root=root)
    io.tool_output("Scanning project…")
    io.set_files(session.get_all_project_files())
    _project_summary(session, io)

    if files:
        for f in files:
            ok, msg = session.add_file(f)
            if ok: print_success(msg)
            else:  print_error(msg)

    config = _load_config()
    llm = _select_llm_interactively(io, config)
    if not llm:
        io.tool_error("Failed to initialize LLM.")
        sys.exit(1)

    mode = _select_mode_interactively(io, config)
    session.mode = mode

    coder = Coder(llm=llm, io=io, session=session,
                  stream=stream, auto_apply=auto_apply, verbose=verbose)
    commands = Commands(io=io, session=session, coder=coder)
    coder.commands = commands

    # Quick help
    print()
    cmds = c("/add /drop /ls /run /diff /commit /tokens /clear /exit", ACCENT)
    print(c("  Commands: ", MUTED) + cmds)
    print()

    while True:
        prompt = f"[{mode}]> "

        try:
            rule()
            user_input = io.get_input(prompt_text=prompt)
        except EOFError:
            io.tool_output("\nGoodbye!")
            break
        except KeyboardInterrupt:
            print_warning("Ctrl+C — /exit to quit")
            continue

        if not user_input.strip():
            continue

        if commands.is_command(user_input):
            try:
                commands.run(user_input)
            except SwitchMode as sm:
                mode = sm.mode
                io.tool_output(f"Mode → [{mode}]")
            except SystemExit:
                break
            continue

        io.user_input(user_input)
        _suggest_and_offer(coder, user_input, io)

        try:
            coder.run_one(user_input)
        except KeyboardInterrupt:
            print_warning("Interrupted.")
        except Exception as e:
            print_error(f"Error: {e}")
            if verbose:
                import traceback
                io.tool_error(traceback.format_exc())
def main_entry():
    import argparse
    p = argparse.ArgumentParser(prog="opendoor", description="OpenDoor AI coding assistant")
    p.add_argument("files", nargs="*", help="Files to open immediately")
    p.add_argument("--root", default=".", help="Project root (default: current dir)")
    p.add_argument("--model", default=None, help="Model name override")
    p.add_argument("--no-stream", action="store_true", help="Disable streaming")
    p.add_argument("--no-apply", action="store_true", help="Don't auto-write files")
    p.add_argument("-v","--verbose", action="store_true", help="Verbose output")
    args = p.parse_args()
    
    run(root=args.root, files=args.files or [], model=args.model,
        stream=not args.no_stream, verbose=args.verbose, auto_apply=not args.no_apply)
