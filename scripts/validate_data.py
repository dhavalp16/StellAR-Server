import os
import json
import tkinter as tk
from tkinter import filedialog

def main():
    root = tk.Tk()
    root.withdraw()

    print("--- Label Spy Tool ---")
    source_dir = filedialog.askdirectory(title="Select your JSON folder")
    if not source_dir: return

    found_labels = set()
    files = [f for f in os.listdir(source_dir) if f.endswith('.json')]
    
    print(f"Scanning {len(files)} files...")

    for filename in files:
        path = os.path.join(source_dir, filename)
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                for shape in data.get('shapes', []):
                    found_labels.add(shape['label'])
        except:
            pass

    print("\nXXX RESULTS XXX")
    print("The script found these EXACT names in your files:")
    print("------------------------------------------------")
    for label in found_labels:
        print(f"'{label}'")
    print("------------------------------------------------")
    print("Update your 'CLASSES' list in the main script to match these exactly!")

if __name__ == "__main__":
    main()