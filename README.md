# OpenDoor AI
<p align="center"> <img src="assets/icon.ico" width="150" title="center"> </p>

OpenDoor is a sophisticated, experimental coding assistant designed to bridge the gap between cloud-based AI (Gemini) and local LLMs (Ollama).

> [!IMPORTANT]
> **The Future Agnet Vision**:
> The ultimate goal of this project is to evolve from a "guided assistant" into a full-fledged **Agnet**. 
> - **What is an Agnet?** An AI Agnet is an autonomous agent capable of making decisions, solving complex architectural problems, and building entire projects independently.
> - **Current Status**: The project is currently in the prototype stage and is **INCOMPLETE**. However, it contains the high-performance core and safety foundations required for its future evolution.

## Installation

You can install OpenDoor directly from GitHub to use it as a global command on your system without downloading the source code manually:

```bash
pip install git+https://github.com/YASSER-27/opendoor.git
```
---
```bash
  ___                   ____                  
 / _ \ _ __   ___ _ __ |  _ \  ___   ___  _ __
| | | | '_ \ / _ \ '_ \| | | |/ _ \ / _ \| '__|
| |_| | |_) |  __/ | | | |_| | (_) | (_) | |   
 \___/| .__/ \___|_| |_|____/ \___/ \___/|_|   
      |_|                                       

```
Once installed, simply run `opendoor` in any terminal to start.

## Detailed Features

### 1. Advanced Thinking & Transparency
OpenDoor provides a transparent "Thinking Mode" during response generation:
- **Real-time Word Counter**: Tracks every generated word as it happens.
- **Microsecond Timer**: Measures response latency to the millisecond for performance tracking.
- **UI Throttling**: The terminal UI is throttled at 15Hz to ensure zero CPU overhead on weak hardware during rapid text streaming.

### 2. Workspace Isolation & Safety
A strict isolation system is active during "Build Mode":
- **Internal Blindness**: Internal `opendoor/` source files are hidden from the AI's context to prevent accidental self-modification.
- **Sandboxed Extraction**: Robust logic ensures files are extracted correctly into isolated project subdirectories.

### 3. C++ Performance Engine (The "Magic" Core)
OpenDoor is powered by a **C++ performance core** to ensure lightning-fast execution and minimal resource footprint:
- **C++ Native Speed**: The heavy-duty word counting and state tracking logic are architected with C++ principles (and a native C++ blueprint in `engine/performance_core.cpp`) to handle massive text streams without lagging.
- **Incremental State Processing**: Instead of re-processing large text buffers, OpenDoor uses O(1) incremental processing.
- **System Call Caching**: Terminal dimensions and TTY status are cached to minimize expensive Kernel-level requests.

### 4. Enterprise-Grade Portability
- **Standalone Executable**: OpenDoor can be compiled into a single (~56MB) `.exe` file that runs on any Windows machine without requiring Python.
- **Bespoke Branding**: Support for custom `.ico` assets embedded directly into the binary.

## Technical Stack
- **Languages**: Python 3.14+ & **C++** (Native performance core for critical path).
- **AI Infrastructure**: 
  - `Google GenAI SDK` (Gemini Flash/Pro).
  - `Ollama API` (Local models like DeepSeek-R1, Llama 3).
- **UI Architecture**: ANSI-based Terminal User Interface (TUI) with optimized rendering.

## Roadmap
- [ ] Transition to full **Agnet** autonomous architecture.
- [ ] Autonomous Command Execution: Ability to run tests and fix bugs without human intervention.
- [ ] Multi-modal generation support.

---
*Built with passion by **YASSER-27***  
*AI Systems Architect & Visionary of the Agnet Evolution*

*Innovating towards the future of AI Agents.*
