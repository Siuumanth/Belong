from pathlib import Path

# ============================================================
# CONFIG
# ============================================================

# Project directory to scan
SOURCE_DIR = Path(r"D:/code/Golang/Belong/belong-api/db/migrations")

# Output directory
OUTPUT_DIR = Path(r"D:/code/Golang/Belong/archieve")

# Files/extensions you want to extract
# Examples: ".go", ".py", ".sql"
INCLUDE_EXTENSIONS = [
    ".go",
    ".py",
    ".sql",
]

# Optional: specific filenames
# Leave empty if extensions are enough.
INCLUDE_FILENAMES = [
    # "docker-compose.yml",
    # "Dockerfile",
]

# Directories to ignore
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
}

OUTPUT_FILE = OUTPUT_DIR / "all_SQL.txt"


# ============================================================
# EXTRACTION
# ============================================================

def should_include(path: Path) -> bool:
    # Ignore excluded directories
    if any(part in EXCLUDE_DIRS for part in path.parts):
        return False

    # Include by extension
    if path.suffix.lower() in INCLUDE_EXTENSIONS:
        return True

    # Include specific filenames
    if path.name in INCLUDE_FILENAMES:
        return True

    return False


def extract_files():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    files = [
        path
        for path in SOURCE_DIR.rglob("*")
        if path.is_file() and should_include(path)
    ]

    files.sort()

    with OUTPUT_FILE.open("w", encoding="utf-8") as out:
        for path in files:
            relative_path = path.relative_to(SOURCE_DIR)

            out.write("\n")
            out.write("=" * 100 + "\n")
            out.write(f"FILE: {relative_path}\n")
            out.write("=" * 100 + "\n\n")

            try:
                content = path.read_text(encoding="utf-8")
                out.write(content)
            except UnicodeDecodeError:
                out.write("[Could not decode file as UTF-8]\n")

            out.write("\n\n")

    print(f"Extracted {len(files)} files.")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    extract_files()