from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "planner/static/index.html").read_text(encoding="utf-8")
APP = (ROOT / "planner/static/app.js").read_text(encoding="utf-8")
PRODUCT = (ROOT / "planner/static/product-suite.js").read_text(encoding="utf-8")
SCHOOL = (ROOT / "planner/static/school-official.js").read_text(encoding="utf-8")
PERSONAL = (ROOT / "planner/static/personal-v2.js").read_text(encoding="utf-8")
SCRUB = (ROOT / "planner/static/human-scrub-fixes.js").read_text(encoding="utf-8")
GUARD = (ROOT / "planner/static/button-path-guards.js").read_text(encoding="utf-8")
RECOVERY = (ROOT / "planner/static/startup-recovery.js").read_text(encoding="utf-8")
FINAL = (ROOT / "planner/static/final-button-fix.js").read_text(encoding="utf-8")

CASES = {
    "Today nav": "data-view=\"today\"",
    "My Week nav": "data-view=\"week\"",
    "Curriculum nav": "data-view=\"curriculum\"",
    "Exams nav": "data-view=\"exams\"",
    "Progress nav": "data-view=\"insights\"",
    "Change plan": "window.openPlannerSetup",
    "Change mode": "window.openPlannerSetup",
    "Header rebuild uses canonical global": "window.replanWeek",
    "First-time USMLE": "startStep1()",
    "First-time personal": "startPersonalPlanner()",
    "School picker": "openSchoolPicker",
    "Batterjee school entry": "bmc: {",
    "Harvard school entry": "harvard: {",
    "Johns Hopkins school entry": "hopkins: {",
    "Mayo school entry": "mayo: {",
    "School visual marks": "school-mark",
    "School chooser close": "school-close",
    "School year picker": "window.levelPicker",
    "School course picker": "coursePicker",
    "School build": "buildSchool",
    "Other school -> personal": "startPersonalPlanner",
    "Personal build": "function build()",
    "Personal timetable import": "importTimetable",
    "Personal cancel": "#pv-cancel",
    "Personal make plan": "#pv-build",
    "Replan canonical endpoint": "/v2/plan/persist",
    "Curriculum add topic": "window.addCustomTopic",
    "Exam save + replan": "saveTime()",
    "Progress recalibrate": "calibrate()",
    "Session complete": "completeSession(false)",
    "Session complete + replan": "completeSession(true)",
    "Session cancel": "closeModal()",
    "Tools launcher": "window.openTools",
    "Dynamic Tools guard": "removeAttribute('data-view')",
    "Startup recovery": "showOfflineRecovery",
    "Offline school button": "#offline-school",
    "Direct school button capture": "#school-direct-entry",
}

HAYSTACK = "\n".join((INDEX, APP, PRODUCT, SCHOOL, PERSONAL, SCRUB, GUARD, RECOVERY, FINAL))
for name, needle in CASES.items():
    if needle not in HAYSTACK:
        raise SystemExit(f"MISSING PATH CONTRACT: {name}: {needle}")

if "$('#reset-btn').onclick=()=>{state.view='today';load()}" in APP:
    raise SystemExit("REGRESSION: Change plan still hard-resets to Today")
if "$('#replan-btn').onclick=replanWeek" in APP:
    raise SystemExit("REGRESSION: header Rebuild week still captures legacy replan function")

# The old dead-end message must not be shipped in any runtime layer. The
# offline fallback has its own self-contained school chooser now.
FORBIDDEN = "Medical school setup is still loading. Please try again."
for path, text in {
    "index.html": INDEX,
    "app.js": APP,
    "school-official.js": SCHOOL,
    "runtime-fixes.js": (ROOT / "planner/static/runtime-fixes.js").read_text(encoding="utf-8"),
    "human-scrub-fixes.js": SCRUB,
    "startup-recovery.js": RECOVERY,
}.items():
    if FORBIDDEN in text:
        raise SystemExit(f"REGRESSION: stale school-loading error remains in {path}")

print(f"button path scrub: OK ({len(CASES)} contracts)")
