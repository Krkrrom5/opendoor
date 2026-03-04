import subprocess
import sys
import os

def build():
    print("Starting OpenDoor Standalone Build...")
    
    # Path to the main entry point
    entry_point = "main.py"
    
    # Icon path
    icon_path = os.path.join("assets", "icon.ico")
    if not os.path.exists(icon_path):
        icon_path = "icon.ico" # Fallback to current dir
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", "opendoor",
        "--clean",
        # Collect all parts of the google-genai package
        "--collect-all", "google.genai",
        # Ensure common lexers are available
        "--hidden-import", "pygments.lexers.python",
        "--hidden-import", "pygments.lexers.javascript",
        "--hidden-import", "pygments.lexers.html",
        "--hidden-import", "pygments.lexers.css",
        "--hidden-import", "pygments.lexers.shell",
        "--hidden-import", "pygments.lexers.c_cpp",
    ]
    
    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])
        print(f"Using icon: {icon_path}")
    
    cmd.append(entry_point)
    
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("\nSUCCESS! your executable is in the 'dist' folder.")
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: Build failed with exit code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    build()
