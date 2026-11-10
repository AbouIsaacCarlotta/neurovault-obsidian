"""
maintain.py — One-command maintenance runner for NeuroVault DIY.
Runs tag_audit.py (tag cleaning & consolidation) followed by cross_linker.py (knowledge graph linking).
By default, both operate strictly on the Knowledge/ folder so personal notes remain untouched.
"""
import os
import sys
import subprocess


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    flags = [arg for arg in sys.argv[1:] if arg in ("--dry-run", "--all")]

    print("=== NeuroVault Knowledge Maintenance Started ===")
    print("\n--- Step 1: Tag Audit & Consolidation ---")
    res1 = subprocess.run([sys.executable, "tag_audit.py", *flags])
    if res1.returncode != 0:
        print("❌ Tag audit failed. Stopping before cross-linking.")
        sys.exit(res1.returncode)

    print("\n--- Step 2: Knowledge Graph Cross-Linking ---")
    res2 = subprocess.run([sys.executable, "cross_linker.py", *flags])
    if res2.returncode != 0:
        print("❌ Cross-linking failed.")
        sys.exit(res2.returncode)

    print("\n=== NeuroVault Knowledge Maintenance Complete ===")


if __name__ == "__main__":
    main()
