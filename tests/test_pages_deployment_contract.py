from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "planner" / "static"


def test_pages_api_config_has_build_marker():
    source = (STATIC / "pages-api-config.js").read_text(encoding="utf-8")
    assert "__PLANNER_API_BASE__" in source


def test_pages_workflow_substitutes_build_marker():
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "vars.PLANNER_API_BASE" in workflow
    assert "pages-api-config.js" in workflow
    assert "__PLANNER_API_BASE__" in workflow


def test_pages_api_config_loads_before_app():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert html.index("./pages-api-config.js") < html.index("./app.js")
