
import csv
import json
import math
import random
import unicodedata
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import HTMLResponse

ROOT = Path(__file__).resolve().parents[2] / "data" / "energy_demo"
REPORT = ROOT / "report.json"

# Potencias e perfis ficticios; nao representam os dispositivos cadastrados.
DEVICES = [
    ("geladeira", 150, "cycle"),
    ("chuveiro", 5500, "shower"),
    ("ar-condicionado", 1000, "ac"),
    ("televisao", 110, "tv"),
    ("iluminacao", 60, "light"),
    ("computador", 200, "pc"),
]

def train():
    ROOT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(672)
    start = datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=-3)))
    rows, totals = [], []
    for index in range(120 * 24):
        stamp = start + timedelta(hours=index)
        hour = stamp.hour
        weekend = stamp.weekday() >= 5
        total = 0.0
        for name, watts, profile in DEVICES:
            minutes = 0.0
            if profile == "cycle":
                minutes = rng.uniform(16, 26)
            elif profile == "shower" and hour in (7, 20):
                minutes = rng.uniform(8, 18)
            elif profile == "ac" and hour in (19, 20, 21, 22, 23):
                minutes = rng.uniform(25, 60)
            elif profile == "tv" and (18 <= hour <= 22 or weekend and 13 <= hour <= 16):
                minutes = rng.uniform(20, 60)
            elif profile == "light" and (hour == 6 or 18 <= hour <= 23):
                minutes = rng.uniform(30, 60)
            elif profile == "pc" and (19 <= hour <= 22 or weekend and 10 <= hour <= 16):
                minutes = rng.uniform(25, 60)
            kwh = watts * minutes / 60000
            rows.append({
                "timestamp": stamp.isoformat(), "device": name,
                "power_w": watts, "minutes_on": round(minutes, 3),
                "energy_kwh": round(kwh, 6), "source": "synthetic"
            })
            total += kwh
        totals.append((stamp, total))

    def fit(samples):
        groups = defaultdict(list)
        for stamp, value in samples:
            groups[f"{stamp.weekday()}:{stamp.hour}"].append(value)
        return {key: sum(values) / len(values) for key, values in groups.items()}

    cut = 96 * 24
    fitted = fit(totals[:cut])
    errors, baseline_errors = [], []
    for index in range(cut, len(totals)):
        stamp, actual = totals[index]
        prediction = fitted[f"{stamp.weekday()}:{stamp.hour}"]
        errors.append(abs(actual - prediction))
        baseline_errors.append(abs(actual - totals[index - 168][1]))

    # Avaliacao acima usa apenas o treino. Agora ajusta o modelo de uso com todos os dados.
    final_model = fit(totals)
    target = totals[-1][0] + timedelta(hours=1)
    prediction = final_model[f"{target.weekday()}:{target.hour}"]

    recent = defaultdict(float)
    recent_start = totals[-1][0] - timedelta(hours=167)
    for row in rows:
        if datetime.fromisoformat(row["timestamp"]) >= recent_start:
            recent[row["device"]] += row["energy_kwh"]

    # Cenarios independentes: reduzir o tempo de uso, mantendo a potencia.
    fractions = {
        "chuveiro": 0.20, "ar-condicionado": 0.15,
        "televisao": 0.20, "iluminacao": 0.20, "computador": 0.15
    }
    suggestions = []
    for name, fraction in fractions.items():
        saved = recent[name] * fraction
        suggestions.append({
            "device": name,
            "reduction_percent": round(fraction * 100),
            "estimated_saving_7_days_kwh": round(saved, 3),
            "assumption": "Mesmo perfil semanal e mesma potencia; reducao do tempo de uso."
        })
    suggestions.sort(key=lambda item: item["estimated_saving_7_days_kwh"], reverse=True)

    report = {
        "source": "synthetic",
        "dataset_id": "aether-fictional-house-v1",
        "seed": 672,
        "model": "Regressao pela media de consumo por dia da semana e hora",
        "model_version": "synthetic-seasonal-mean-v1",
        "days": 120,
        "rows": len(rows),
        "train_days": 96,
        "test_days": 24,
        "evaluation": {
            "model_mae_kwh": round(sum(errors) / len(errors), 6),
            "previous_week_baseline_mae_kwh": round(sum(baseline_errors) / len(baseline_errors), 6),
            "method": "Corte temporal; modelo de avaliacao ajustado somente nos primeiros 96 dias."
        },
        "period_start": start.isoformat(),
        "period_end": (totals[-1][0] + timedelta(hours=1)).isoformat(),
        "recent_7_days_kwh": round(sum(recent.values()), 3),
        "by_device_7_days_kwh": dict(sorted(recent.items(), key=lambda item: item[1], reverse=True)),
        "next_hour": {
            "start": target.isoformat(),
            "end": (target + timedelta(hours=1)).isoformat(),
            "prediction_kwh": round(prediction, 3)
        },
        "suggestions": suggestions,
        "notice": "Casa e consumos ficticios. Resultado nao valida desempenho em residencias reais."
    }
    with (ROOT / "consumption.csv").open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    for name, value in (("model.json", final_model), ("report.json", report)):
        destination = ROOT / name
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
        temporary.replace(destination)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report

def report():
    if not REPORT.exists():
        return None
    return json.loads(REPORT.read_text(encoding="utf-8"))

def reply(text):
    phrase = "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )
    if not any(word in phrase for word in ("econom", "consumo", "energia", "kwh", "gasto")):
        return None
    if any(word in phrase for word in ("histor", "dataset", "uci")):
        return None
    data = report()
    if not data:
        return "A demonstra\u00e7\u00e3o de energia ainda precisa ser treinada.", "synthetic_energy"
    if any(word in phrase for word in ("econom", "sugest", "reduzir", "dica")):
        tips = data["suggestions"][:2]
        parts = ["Na nossa casa fict\u00edcia, estas s\u00e3o duas possibilidades de economia."]
        for tip in tips:
            parts.append(
                f"Reduzir em {tip['reduction_percent']} por cento o tempo de uso de "
                f"{tip['device']} representaria cerca de "
                f"{tip['estimated_saving_7_days_kwh']:.1f} quilowatts-hora em uma semana."
            )
        parts.append("A estimativa considera a mesma pot\u00eancia e o mesmo perfil semanal.")
        return " ".join(parts), "synthetic_energy"
    if any(word in phrase for word in ("previs", "proxima hora", "amanha")):
        future = data["next_hour"]
        return (
            f"No fim do hist\u00f3rico fict\u00edcio, a previs\u00e3o para a hora iniciada em "
            f"{future['start']} foi de {future['prediction_kwh']:.2f} quilowatts-hora. "
            "Esse hor\u00e1rio pertence \u00e0 demonstra\u00e7\u00e3o, e n\u00e3o ao consumo atual da casa."
        ), "synthetic_energy"
    top = next(iter(data["by_device_7_days_kwh"]))
    return (
        f"Nos \u00faltimos sete dias do hist\u00f3rico fict\u00edcio, o consumo foi de "
        f"{data['recent_7_days_kwh']:.1f} quilowatts-hora. "
        f"O equipamento que mais consumiu foi {top}. "
        "Posso sugerir formas de reduzir esse consumo simulado."
    ), "synthetic_energy"

def setup(api):
    @api.get("/api/v1/energy-demo/report")
    def get_report():
        data = report()
        if data is None:
            raise HTTPException(503, "Execute treinar_energia_demo.py primeiro.")
        return data

    @api.get("/energia-demo", include_in_schema=False)
    def dashboard():
        return HTMLResponse(
            '<!doctype html><html lang="pt-BR"><meta charset="utf-8">'
            '<title>Aether - Energia simulada</title>'
            '<style>body{font:18px system-ui;max-width:900px;margin:40px auto;padding:20px;'
            'background:#101b2b;color:#edf5ff}pre{white-space:pre-wrap;font:15px monospace}'
            'button{padding:12px;margin:8px;cursor:pointer}</style>'
            '<h1>Aether: energia simulada</h1>'
            '<p>Casa ficticia. Consulte os consumos, a avaliacao e os cenarios abaixo.</p>'
            '<button id="listen">Ouvir sugestoes</button><p id="message"></p><pre id="data"></pre>'
            '<script>'
            'let player;'
            'fetch("/api/v1/energy-demo/report").then(async r=>{'
            'const d=await r.json();document.querySelector("#data").textContent=JSON.stringify(d,null,2);'
            '}).catch(()=>document.querySelector("#data").textContent="Falha ao carregar.");'
            'document.querySelector("#listen").onclick=async function(){'
            'this.disabled=true;const m=document.querySelector("#message");m.textContent="Preparando...";'
            'try{const id=crypto.randomUUID();'
            'const r=await fetch("/api/v1/assistant/chat",{method:"POST",headers:{"Content-Type":"application/json"},'
            'body:JSON.stringify({text:"Como economizar energia?",request_id:id,session_id:"energy-demo"})});'
            'if(!r.ok)throw Error("Falha ao consultar o Aether.");'
            'const d=await r.json();m.textContent=d.answer;'
            'const s=await fetch("/api/v1/voice/speak",{method:"POST",headers:{"Content-Type":"application/json"},'
            'body:JSON.stringify({text:d.answer})});if(!s.ok)throw Error("Confira a configuracao de voz.");'
            'const url=URL.createObjectURL(await s.blob());player=new Audio(url);'
            'player.onended=()=>URL.revokeObjectURL(url);'
            'player.onerror=()=>URL.revokeObjectURL(url);await player.play();'
            '}catch(e){m.textContent=e.message;}finally{this.disabled=false;}};'
            '</script></html>'
        )

if __name__ == "__main__":
    train()
