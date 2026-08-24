from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "planner" / "static"
INDEX = STATIC / "index.html"


def test_every_index_asset_exists():
    html = INDEX.read_text(encoding="utf-8")
    refs = re.findall(r'(?:src|href)=["\'](\./[^"\']+)["\']', html)
    missing = [ref for ref in refs if not (STATIC / ref[2:]).is_file()]
    assert not missing, f"index.html references missing assets: {missing}"


def test_no_duplicate_script_paths():
    html = INDEX.read_text(encoding="utf-8")
    scripts = re.findall(r'<script[^>]+src=["\'](\./[^"\']+)["\']', html)
    assert len(scripts) == len(set(scripts)), "index.html loads a script more than once"


def test_adaptive_explanation_layer_is_loaded_after_adaptive_engine():
    html = INDEX.read_text(encoding="utf-8")
    scripts = re.findall(r'<script[^>]+src=["\'](\./[^"\']+)["\']', html)
    assert "./adaptive-v3.js" in scripts
    assert "./adaptive-why.js" in scripts
    assert scripts.index("./adaptive-v3.js") < scripts.index("./adaptive-why.js")


def test_all_frontend_javascript_parses_when_node_is_available():
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        return
    for path in sorted(STATIC.glob("*.js")):
        result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
        assert result.returncode == 0, f"JavaScript syntax error in {path.name}:\n{result.stderr}"


def test_inline_handlers_only_call_global_functions():
    sources = [p.read_text(encoding="utf-8") for p in STATIC.glob("*.js")]
    sources.append(INDEX.read_text(encoding="utf-8"))
    text = "\n".join(sources)
    declared = set(re.findall(r"(?:function|async function)\s+([A-Za-z_$][\w$]*)\s*\(", text))
    declared.update(re.findall(r"window\.([A-Za-z_$][\w$]*)\s*=", text))
    handlers = re.findall(r'onclick=["\']\s*([A-Za-z_$][\w$]*)\s*\(', text)
    ignored = {"if", "for", "while", "function"}
    missing = sorted({name for name in handlers if name not in declared and name not in ignored})
    assert not missing, f"Inline click handlers reference functions that are not globally callable: {missing}"
