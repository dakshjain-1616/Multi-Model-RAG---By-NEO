import os
import re
import ast
from pathlib import Path

def extract_imports_from_file(filepath):
    imports = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read(), filename=str(filepath))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split('.')[0])
            except SyntaxError:
                pass
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return imports

project_root = Path('/root/claude_tests/MultiModelRag')
all_imports = set()

python_files = list(project_root.glob('*.py'))
python_files.extend(project_root.glob('src/*.py'))

print("=== Scanning Python files ===")
for py_file in python_files:
    print(f"Scanning: {py_file.name}")
    imports = extract_imports_from_file(py_file)
    all_imports.update(imports)

stdlib_modules = {
    'os', 'sys', 'json', 'time', 'datetime', 'pathlib', 're', 'ast',
    'io', 'typing', 'collections', 'itertools', 'functools', 'operator',
    'logging', 'argparse', 'subprocess', 'shutil', 'tempfile', 'unittest',
    'warnings', 'copy', 'pickle', 'base64', 'hashlib', 'uuid', 'enum',
    'threading', 'multiprocessing', 'socket', 'urllib', 'http', 'email',
    'xml', 'html', 'csv', 'configparser', 'zipfile', 'tarfile', 'gzip'
}

third_party = sorted([imp for imp in all_imports if imp not in stdlib_modules])

print("\n=== Third-party imports detected ===")
for imp in third_party:
    print(f"  - {imp}")

package_mapping = {
    'PIL': 'Pillow',
    'cv2': 'opencv-python',
    'yaml': 'PyYAML',
    'dotenv': 'python-dotenv',
    'sentence_transformers': 'sentence-transformers',
    'chromadb': 'chromadb',
    'streamlit': 'streamlit',
    'reportlab': 'reportlab',
    'openai': 'openai',
    'anthropic': 'anthropic',
    'google': 'google-generativeai',
    'docx': 'python-docx',
    'pptx': 'python-pptx',
    'openpyxl': 'openpyxl',
    'pandas': 'pandas',
    'numpy': 'numpy',
    'torch': 'torch',
    'torchvision': 'torchvision'
}

requirements = []
for imp in third_party:
    pkg_name = package_mapping.get(imp, imp)
    requirements.append(pkg_name)

requirements_content = '\n'.join(sorted(set(requirements)))

output_file = project_root / 'requirements.txt'
with open(output_file, 'w') as f:
    f.write(requirements_content + '\n')

print(f"\n=== Generated requirements.txt ===")
print(requirements_content)
print(f"\n✓ Saved to: {output_file}")