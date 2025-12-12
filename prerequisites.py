import subprocess
import sys

REQUIRED_PACKAGES = {
    "PIL": "Pillow",  # import name : pip package name
}

def check_and_install():
    missing = []
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append((module_name, pip_name))

    if not missing:
        print("[✔] All required packages are installed.")
        return

    print("[✖] Missing packages detected:")
    for mod, _ in missing:
        print(f"  - {mod}")

    response = input("Install missing packages now? (y/n): ").strip().lower()
    if response != "y":
        print("Cannot continue without required packages. Exiting.")
        sys.exit(1)

    for module_name, pip_name in missing:
        print(f"Installing {pip_name}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])

    print("[✔] All missing packages installed.")