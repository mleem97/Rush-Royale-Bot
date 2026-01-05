import sys
import requests
from packaging.requirements import Requirement, InvalidRequirement
from packaging.version import parse as parse_version

def get_pypi_data(package_name):
    """Holt Metadaten von der PyPI JSON API."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        pass
    return None

def extract_max_python_version(data):
    """Extrahiert die höchste Python-Version aus den Trove Classifiers."""
    if not data or 'info' not in data:
        return None

    classifiers = data['info'].get('classifiers', [])
    supported_versions = []

    for c in classifiers:
        # Wir suchen nach Einträgen wie "Programming Language :: Python :: 3.12"
        if c.startswith("Programming Language :: Python :: 3."):
            parts = c.split(" :: ")
            if len(parts) == 3:
                version_str = parts[2]
                # Wir filtern reine Nummern (z.B. ignorieren wir "3.x" oder "Implementation")
                if version_str[0].isdigit():
                    try:
                        # parse_version garantiert korrekten Vergleich (3.10 > 3.9)
                        supported_versions.append(parse_version(version_str))
                    except:
                        continue

    if supported_versions:
        # Sortieren und das Höchste zurückgeben
        supported_versions.sort()
        return str(supported_versions[-1])
    
    return None

def process_requirements(file_path):
    print(f"{'Paket':<25} | {'Aktuelle Req.'} | {'Max. Python (laut PyPI)'}")
    print("-" * 75)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Leere Zeilen, Kommentare und pip-Optionen ignorieren
                if not line or line.startswith('#') or line.startswith('-'):
                    continue

                try:
                    # Robustes Parsing der Requirement-Zeile
                    req = Requirement(line)
                    package_name = req.name
                    
                    data = get_pypi_data(package_name)
                    max_ver = extract_max_python_version(data)

                    if max_ver:
                        display_ver = max_ver
                    else:
                        display_ver = "Keine Info / Unbekannt"

                    # req.specifier zeigt an, was in der txt steht (z.B. ==1.0.0)
                    specifier_str = str(req.specifier) if req.specifier else "Any"
                    
                    print(f"{package_name:<25} | {specifier_str:<13} | {display_ver}")

                except InvalidRequirement:
                    # Falls eine Zeile nicht geparst werden kann, wird sie übersprungen
                    print(f"{line[:25]:<25} | {'ERROR':<13} | Ungültiges Format")

    except FileNotFoundError:
        print(f"Fehler: Datei '{file_path}' nicht gefunden.")

if __name__ == "__main__":
    # Standardmäßig requirements.txt, kann aber beim Aufruf geändert werden
    filename = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    process_requirements(filename)
    