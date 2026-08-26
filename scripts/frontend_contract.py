from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "planner" / "static" / "index.html"
BRIDGE = ROOT / "planner" / "static" / "sync-bridge.js"
SYNC_UI = ROOT / "planner" / "static" / "sync-ui.js"


def main() -> None:
    index = INDEX.read_text(encoding="utf-8")
    bridge = BRIDGE.read_text(encoding="utf-8")
    sync_ui = SYNC_UI.read_text(encoding="utf-8")

    required_scripts = (
        './sync-bridge.js',
        './app.js',
        './sync-ui.js',
    )
    positions = [index.index(script) for script in required_scripts]
    assert positions == sorted(positions), 'sync bridge must load before the legacy app and sync UI'
    assert 'X-Planner-Revision' in bridge
    assert 'X-Planner-User' in bridge
    assert 'status === 409' in bridge
    assert 'plannerSync' in sync_ui
    assert '/workspace/state' in sync_ui
    assert '/v2/reconcile/sessions' in sync_ui
    print('frontend integration contract: OK')


if __name__ == '__main__':
    main()
