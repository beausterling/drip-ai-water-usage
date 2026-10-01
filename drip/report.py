"""Self-contained HTML breakdown, opened by Cmd+clicking the status-line segment."""
import json
import os
from datetime import date, datetime, timedelta

from . import ledger
from .coeffs import BANDS, Coefficients, Tokens
from .sources import PROVENANCE, SOURCES

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "report_template.html")
REPORT_PATH = os.path.join(os.path.dirname(ledger.DB_PATH), "report.html")
TOKEN_COLS = "SUM(input), SUM(output), SUM(cache_read), SUM(cache_write)"


def _price(coeffs, rows, band, onsite):
    """rows of (model, in, out, cr, cw) -> dict with per-model detail + totals."""
    models, total = [], {"ml": 0.0, "wh": 0.0, "range": {b: 0.0 for b in BANDS}}
    for model, *tk in rows:
        t = Tokens(*tk)
        ml = coeffs.water_ml(t, model, band, onsite)
        wh = coeffs.energy_wh(t, model, band)
        wf = coeffs.water_factor(band, onsite)
        per = coeffs.per_1k_wh(model, band)
        parts = {k: getattr(t, k) * per[k] / 1000 * wf for k in ("input", "output", "cache_read", "cache_write")}
        models.append({"model": model, "est": coeffs.is_estimated(model), "ml": ml, "wh": wh,
                       "tokens": vars(t), "parts": parts})
        total["ml"] += ml
        total["wh"] += wh
        for b in BANDS:
            total["range"][b] += coeffs.water_ml(t, model, b, onsite)
    models.sort(key=lambda m: -m["ml"])
    return {"models": models, **total}


def build(db, band="mid", onsite=False, n_sessions=40, n_days=30):
    c = Coefficients()
    sessions = []
    for sid, tool, project, start, end in db.execute(
            "SELECT session, tool, project, MIN(ts), MAX(ts) FROM usage GROUP BY session "
            "ORDER BY MAX(ts) DESC LIMIT ?", (n_sessions,)):
        rows = db.execute(f"SELECT model, {TOKEN_COLS} FROM usage WHERE session=? GROUP BY model", (sid,)).fetchall()
        sessions.append({"id": sid, "tool": tool, "project": os.path.basename(project or "") or "?",
                         "start": start, "end": end, **_price(c, rows, band, onsite)})
    since = (date.today() - timedelta(days=n_days - 1)).isoformat()
    days = {}
    for day, model, *tk in db.execute(
            f"SELECT day, model, {TOKEN_COLS} FROM usage WHERE day >= ? GROUP BY day, model", (since,)):
        days[day] = days.get(day, 0.0) + c.water_ml(Tokens(*tk), model, band, onsite)
    day_list = [((date.today() - timedelta(days=i)).isoformat()) for i in range(n_days - 1, -1, -1)]
    all_rows = db.execute(f"SELECT model, {TOKEN_COLS} FROM usage GROUP BY model").fetchall()
    wf = c.water_factor(band, onsite)
    used = {r[0] for r in all_rows}
    model_rows = []
    for m in c.cfg["model"]:
        if m.get("fallback"):
            continue
        prefix = m["match"].replace("*", "")
        per = c.per_1k_wh(prefix, band)
        model_rows.append({"model": prefix.rstrip("-") + ("*" if prefix.endswith("-") else ""),
                           "used": any(u.startswith(prefix) for u in used),
                           **{k: v * wf for k, v in per.items()}})
    return {
        "generated": datetime.now().isoformat(),
        "sources": SOURCES, "provenance": PROVENANCE,
        "coeffs": {"parts": c.cfg["water_factor_parts"], "e": c.cfg["energy"],
                   "wf": c.cfg["water_factor_onsite" if onsite else "water_factor"], "models": model_rows},
        "band": band, "onsite": onsite, "reviewed": c.cfg.get("last_reviewed"),
        "sessions": sessions,
        "days": [{"day": d, "ml": days.get(d, 0.0)} for d in day_list],
        "all": _price(c, all_rows, band, onsite),
        "today": days.get(date.today().isoformat(), 0.0),
    }


def write(db, band="mid", onsite=False, path=REPORT_PATH):
    data = build(db, band, onsite)
    with open(TEMPLATE_PATH) as f:
        template = f.read()
    page = template.replace("/*DATA*/null", json.dumps(data).replace("</", "<\\/"))
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(page)
    os.replace(tmp, path)
    return path
