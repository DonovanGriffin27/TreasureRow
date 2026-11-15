# Noah Higgs
"""Build the Beta Release zip (TreasureRow_Beta.zip) from this folder.

Run from the repo:   python app/package_beta.py
The zip is written next to the app folder and is checked before it is finished:
no .env, __pycache__, venv, or uploads, and no keys or secrets in any file.
Works on Windows, Mac, and Linux. install.sh and the .command file are marked
executable inside the zip so they open with a double-click on a Mac.
"""
import re
import sys
import zipfile
from pathlib import Path

APP = Path(__file__).resolve().parent
OUT = APP.parent / "TreasureRow_Beta.zip"
TOP = "TreasureRow"

SKIP_DIRS = {"venv", ".venv", "env", "__pycache__", ".pytest_cache", ".git",
             ".elasticbeanstalk", "uploads"}
SKIP_FILES = {".env", ".env.test", ".DS_Store", "README.md", "package_beta.py"}
EXECUTABLE = {"install.sh", "Launch TreasureRow.command"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".yml", ".yaml", ".json", ".config",
                 ".html", ".js", ".css", ".sh", ".command", ".example", ".cfg",
                 ".conf", ".ini", ".toml"}
SECRET_PATTERNS = {
    "AWS access key id": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "AWS secret key assignment": re.compile(
        r"aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{30,}", re.I),
}


def wanted(path):
    rel = path.relative_to(APP)
    if any(part in SKIP_DIRS for part in rel.parts[:-1]):
        return False
    if path.name in SKIP_FILES or path.suffix in {".pyc", ".pyo"}:
        return False
    if path.name.startswith(".env") and path.name not in {".env.example", ".env.test.example"}:
        return False
    return True


def main():
    files = sorted(p for p in APP.rglob("*") if p.is_file() and wanted(p))
    problems = []
    for path in files:
        if path.suffix in TEXT_SUFFIXES or path.name.startswith(".env"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    problems.append(f"{label} in {path.relative_to(APP)}")
    beta_readme = APP / "README_BETA.md"
    if not beta_readme.exists():
        problems.append("README_BETA.md is missing")
    for name in EXECUTABLE:
        if not (APP / name).exists():
            problems.append(f"{name} is missing")
    if problems:
        print("NOT building the zip. Fix these first:")
        for item in problems:
            print("  -", item)
        sys.exit(1)

    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        def add(path, arcname):
            info = zipfile.ZipInfo.from_file(path, f"{TOP}/{arcname}")
            mode = 0o755 if arcname in EXECUTABLE else 0o644
            info.external_attr = (mode | 0o100000) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())

        add(beta_readme, "README.md")  # the Beta README is the one graders see
        for path in files:
            if path == beta_readme:
                continue
            add(path, path.relative_to(APP).as_posix())

    with zipfile.ZipFile(OUT) as zf:
        names = zf.namelist()
    bad = [n for n in names if "__pycache__" in n or "/venv/" in n
           or n.endswith("/.env") or "/uploads/" in n]
    if bad:
        OUT.unlink()
        print("Zip rejected, it contained:", bad)
        sys.exit(1)
    print(f"Built {OUT} with {len(names)} files. No .env, __pycache__, venv, or secrets found.")


if __name__ == "__main__":
    main()
