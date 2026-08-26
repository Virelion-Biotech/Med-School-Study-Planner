from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "planner/static/index.html").read_text(encoding="utf-8")
APP = (ROOT / "planner/static/app.js").read_text(encoding="utf-8")
PRODUCT = (ROOT / "planner/static/product-suite.js").read_text(encoding="utf-8")
SCHOOL = (ROOT / "planner/static/school-official.js").read_text(encoding="utf-8")
PERSONAL = (ROOT / "planner/static/personal-v2.js").read_text(encoding="utf-8")
SCRUB = (ROOT / "planner/static/human-scrub-fixes.js").read_text(encoding="utf-8")
GUARD = (ROOT / "planner/static/button-path-guards.js").read_text(encoding="utf-8")


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
    "Batterjee year picker": "levelPicker()",
    "Batterjee course picker": "coursePicker",
    "Batterjee build": "buildBMC",
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
}

for name, needle in CASES.items():
    haystack = "\n".join((INDEX, APP, PRODUCT, SCHOOL, PERSONAL, SCRUB, GUARD))
    if needle not in haystack:
        raise SystemExit(f"MISSING PATH CONTRACT: {name}: {needle}")

# Explicitly prohibit the most important regressions that the human scrub found.
if "$('#reset-btn').onclick=()=>{state.view='today';load()}" in APP:
    raise SystemExit("REGRESSION: Change plan still hard-resets to Today")
if "$('#replan-btn').onclick=replanWeek" in APP:
    raise SystemExit("REGRESSION: header Rebuild week still captures legacy replan function")

print(f"button path scrub: OK ({len(CASES)} contracts)")
