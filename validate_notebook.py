import json

# Validate notebook
with open('03_test_xgboost_jan2025.ipynb', 'r', encoding='utf-8') as f:
    notebook = json.load(f)

print("✅ JSON valid!")
print(f"   Cells: {len(notebook['cells'])}")
print(f"   Format: nbformat {notebook['nbformat']}.{notebook['nbformat_minor']}")
print(f"   File size: {len(json.dumps(notebook))} bytes")
print("\n📤 Ready to upload to Google Colab!")
