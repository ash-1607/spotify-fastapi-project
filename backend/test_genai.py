# inspect_genai.py
import os, pprint, importlib
import google.generativeai as genai

print("GENAI module file:", getattr(genai, "__file__", "no __file__"))
print("GENAI module attrs snapshot (first 200 chars of repr):")
pprint.pprint([name for name in dir(genai) if not name.startswith("_")])

# Try to print version info if present
print("has __version__:", hasattr(genai, "__version__"))
if hasattr(genai, "__version__"):
    print("version:", getattr(genai, "__version__"))
