from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "planner" / "static"
INDEX = STATIC / "index.html"


def test_required_runtime_dependencies_are_loaded_in_order():
    html = INDEX.read_text(encoding="utf-8")
    scripts = re.findall(r'<script[^>]+src=["\'](\./[^"\']+)["\']', html)
    required = ["./api-config.js", "./app.js", "./simple-setup.js", "./school-official.js", "./product-suite.js", "./advanced-import.js", "./runtime-fixes.js", "./adaptive-v3.js", "./adaptive-why.js", "./sync-bridge.js", "./sync-ui.js"]
    missing = [x for x in required if x not in scripts]
    assert not missing, f"required runtime assets are not loaded: {missing}"
    p = {x: scripts.index(x) for x in required}
    assert p["./api-config.js"] < p["./app.js"] < p["./simple-setup.js"]
    assert p["./runtime-fixes.js"] < p["./adaptive-v3.js"] < p["./adaptive-why.js"]
    assert p["./sync-bridge.js"] < p["./sync-ui.js"]


def test_api_config_has_no_unconfigured_production_placeholder():
    source = (STATIC / "api-config.js").read_text(encoding="utf-8")
    assert "REPLACE_WITH_YOUR_BACKEND_URL" not in source


def test_inline_handlers_reference_declared_callables():
    sources = [p.read_text(encoding="utf-8") for p in STATIC.glob("*.js")]
    sources.append(INDEX.read_text(encoding="utf-8"))
    text = "\n".join(sources)
    declared = set(re.findall(r"(?:function|async function)\s+([A-Za-z_$][\w$]*)\s*\(", text))
    declared.update(re.findall(r"window\.([A-Za-z_$][\w$]*)\s*=", text))
    handlers = re.findall(r'onclick=["\']\s*([A-Za-z_$][\w$]*)\s*\(', text)
    missing = sorted({name for name in handlers if name not in declared})
    assert not missing, f"inline handlers reference missing globals: {missing}"


def test_frontend_uses_only_known_core_api_prefixes():
    text = "\n".join(p.read_text(encoding="utf-8") for p in STATIC.glob("*.js"))
    paths = set(re.findall(r"(?:api|window\.plannerApiUrl)\(\s*['\"](/[^'\"]+)", text))
    allowed = ("/health", "/profile", "/subjects", "/topics", "/exams", "/plan", "/replan", "/setup", "/presets", "/sessions", "/analytics", "/memory", "/calibrate", "/snapshot", "/export", "/workspace", "/v2")
    unknown = sorted(p for p in paths if not p.startswith(allowed))
    assert not unknown, f"frontend references unexpected API paths: {unknown}"


def test_legacy_stale_asset_is_not_part_of_the_boot_graph():
    html = INDEX.read_text(encoding="utf-8")
    assert "./finalize.js" not in html
    assert "./bridge.js" not in html
    assert "./mode-fix.js" not in html
    assert "./product-hotfix.js" not in html
