"""API local: simulador, conversa, rotinas e ponte física configurável."""
import json
import re
import unicodedata
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from . import hardware
from .extensions import setup as setup_extensions
from .automation import setup as setup_automation
from .forecast_service import setup as setup_forecasts
from .assistant_service import setup as setup_assistant
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT = Path(__file__).resolve().parents[2]


class Command(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=100)
    device_id: str = Field(min_length=1, max_length=100)
    action: Literal["turn_on", "turn_off", "set_brightness", "set_color"]
    brightness: Annotated[int, Field(strict=True, ge=0, le=100)] | None = None
    color: tuple[Annotated[int, Field(strict=True, ge=0, le=255)], Annotated[int, Field(strict=True, ge=0, le=255)], Annotated[int, Field(strict=True, ge=0, le=255)]] | None = None

    @model_validator(mode="after")
    def validate_parameters(self):
        if (self.brightness is not None) != (self.action == "set_brightness"):
            raise ValueError("brightness é obrigatório e exclusivo de set_brightness")
        if (self.color is not None) != (self.action == "set_color"):
            raise ValueError("color é obrigatório e exclusivo de set_color")
        return self


class TemperatureReading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float = Field(strict=True, ge=-50, le=100, allow_inf_nan=False)


class TextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=300)


def normalize_text(value):
    value = "".join(c for c in unicodedata.normalize("NFD", value.lower()) if unicodedata.category(c) != "Mn")
    return " ".join(value.strip().rstrip(".?!").split())


def create_app(config_path=None, db_path=None):
    config_file = Path(config_path or ROOT / "config/house.json")
    config = json.loads(config_file.read_text(encoding="utf-8-sig"))
    rooms = {r["id"] for r in config["rooms"]}
    devices = {d["id"]: d for d in config["devices"]}
    if len(rooms) != len(config["rooms"]) or len(devices) != len(config["devices"]):
        raise ValueError("IDs duplicados na configuração")
    for d in devices.values():
        if d.get("kind") in {"temperature_sensor","energy_sensor"}:
            if d.get("kind")=="energy_sensor":
                if d["room_id"] not in rooms or d["capabilities"] != ["read_energy"]:raise ValueError("Configuração energia inválida")
                continue
            if d["room_id"] not in rooms or d["capabilities"] != ["read_temperature"] or not isinstance(d["available"], bool):
                raise ValueError("Configuração de sensor inválida")
            continue
        if d["room_id"] not in rooms or d["initial_state"] not in {"on", "off"}:
            raise ValueError("Cômodo ou estado inicial inválido")
        if not isinstance(d["available"], bool) or not set(d["capabilities"]) <= {"turn_on", "turn_off", "set_brightness", "set_color"}:
            raise ValueError("Disponibilidade ou capacidade inválida")
    database = Path(db_path or ROOT / "data/aether.sqlite3")
    database.parent.mkdir(parents=True, exist_ok=True)

    def connect():
        connection = sqlite3.connect(database, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    with connect() as con:
        con.execute("CREATE TABLE IF NOT EXISTS states (id TEXT PRIMARY KEY, state TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS commands (id TEXT PRIMARY KEY, payload TEXT NOT NULL, code INTEGER NOT NULL, result TEXT NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS temperature_readings (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, value REAL NOT NULL, timestamp TEXT NOT NULL)")
        con.execute("CREATE INDEX IF NOT EXISTS temperature_device_id ON temperature_readings(device_id, id)")
        columns = {row[1] for row in con.execute("PRAGMA table_info(states)")}
        if "brightness" not in columns:
            con.execute("ALTER TABLE states ADD COLUMN brightness INTEGER")
        if "color" not in columns:
            con.execute("ALTER TABLE states ADD COLUMN color TEXT")
        for d in devices.values():
            if d.get("kind") in {"temperature_sensor","energy_sensor"}:
                continue
            con.execute("INSERT OR IGNORE INTO states (id, state) VALUES (?, ?)", (d["id"], d["initial_state"]))

    mutation_lock=threading.RLock()
    api = FastAPI(title="Aether AI — casa local", version="0.13.0")

    evaluate_automation = setup_automation(api, connect, devices)
    forecast_summary = setup_forecasts(api, connect)
    from .energy_demo import setup as setup_energy_demo
    setup_energy_demo(api)

    @api.get("/")
    def home():
        return {"project": "Aether AI", "mode": "simulation", "docs": "/docs", "devices": "/api/v1/devices"}

    @api.get("/painel", include_in_schema=False)
    def dashboard():
        return FileResponse(ROOT / "frontend/index.html", headers={"Cache-Control": "no-store"})

    @api.get("/features.js",include_in_schema=False)
    def feature_script():return FileResponse(ROOT / "frontend/features.js",media_type="application/javascript",headers={"Cache-Control":"no-store"})

    @api.get("/api/v1/house")
    def house():
        return {"id": config["id"], "name": config["name"], "rooms": config["rooms"], "source": "mixed" if any(d.get("source")=="home_assistant" for d in devices.values()) else "simulation"}

    @api.get("/api/v1/devices")
    def list_devices():
        with connect() as con:
            states = {row["id"]: dict(row) for row in con.execute("SELECT * FROM states")}
        result = []
        for d in list(devices.values()):
            if d.get('source')=='home_assistant':
                try:result.append(hardware.read(d))
                except HTTPException:result.append({**d,'source':'home_assistant','available':False,'state':'unknown','connection_error':'Sem leitura física confirmada'})
                continue
            if d.get("kind") in {"temperature_sensor","energy_sensor"}:
                result.append({**d, "source": "simulation"})
                continue
            current = states[d["id"]]
            item = {**d, "source": "simulation", "state": current["state"] if d["available"] else "unknown"}
            if "set_brightness" in d["capabilities"]:
                item["brightness"] = current["brightness"] if d["available"] else None
            if "set_color" in d["capabilities"]:
                item["color"] = json.loads(current["color"]) if d["available"] and current["color"] else None
            result.append(item)
        return result

    def require_sensor(device_id):
        d = devices.get(device_id)
        if d is None:
            raise HTTPException(404, "device_not_found")
        if d.get("kind") != "temperature_sensor":
            raise HTTPException(422, "unsupported_reading")
        if not d["available"]:
            raise HTTPException(503, "device_unavailable")
        return d

    def reading_result(device_id, row):
        return {"device_id": device_id, "source": "simulation", "available": True,
                "measurement": "temperature", "value": row["value"] if row else None,
                "unit": "°C", "timestamp": row["timestamp"] if row else None,
                "status": "recorded" if row else "no_reading"}

    @api.post("/api/v1/simulation/sensors/{device_id}/readings", status_code=201)
    def simulate_temperature(device_id: str, body: TemperatureReading):
        d=require_sensor(device_id)
        if d.get("source")=="home_assistant":raise HTTPException(409,"Use Sincronizar para obter a leitura física.")
        timestamp = datetime.now(timezone.utc).isoformat()
        with connect() as con:
            con.execute("BEGIN IMMEDIATE")
            reading = con.execute("INSERT INTO temperature_readings (device_id, value, timestamp) VALUES (?, ?, ?)",
                        (device_id, body.value, timestamp))
            evaluate_automation(con, device_id, body.value, reading.lastrowid, timestamp)
        return reading_result(device_id, {"value": body.value, "timestamp": timestamp})

    @api.get("/api/v1/sensors/{device_id}/reading")
    def latest_temperature(device_id: str):
        d=require_sensor(device_id)
        if d.get('source')=='home_assistant':
            item=hardware.read(d)
            if not item['available'] or item.get('unit') not in {'°C','C'}:raise HTTPException(503,'Leitura física em °C indisponível')
            return {**reading_result(device_id,{'value':item['value'],'timestamp':item['observed_at']}),'source':'home_assistant'}
        with connect() as con:
            row = con.execute("SELECT value, timestamp FROM temperature_readings WHERE device_id=? ORDER BY id DESC LIMIT 1", (device_id,)).fetchone()
        return reading_result(device_id, row)

    @api.get("/api/v1/sensors/{device_id}/readings")
    def temperature_history(device_id: str, limit: int = Query(20, ge=1, le=100),
                            offset: int = Query(0, ge=0)):
        # Histórico armazenado permanece consultável mesmo com sensor indisponível.
        d = devices.get(device_id)
        if d is None:
            raise HTTPException(404, "device_not_found")
        if d.get("kind") != "temperature_sensor":
            raise HTTPException(422, "unsupported_reading")
        with connect() as con:
            con.execute("BEGIN")
            total = con.execute("SELECT COUNT(*) FROM temperature_readings WHERE device_id=?", (device_id,)).fetchone()[0]
            rows = con.execute("SELECT id, value, timestamp FROM temperature_readings WHERE device_id=? ORDER BY id DESC LIMIT ? OFFSET ?", (device_id, limit, offset)).fetchall()
        return {"device_id": device_id, "source": d.get("source","simulation"), "available": d["available"],
                "measurement": "temperature", "unit": "°C", "order": "newest_first",
                "total": total, "limit": limit, "offset": offset,
                "readings": [{"id": row["id"], "value": row["value"], "timestamp": row["timestamp"]} for row in rows]}

    @api.post("/api/v1/commands")
    def command(body: Command):
        with mutation_lock:
            payload = json.dumps(body.model_dump(exclude_none=True), sort_keys=True)
            with connect() as con:
                # Transação serializa deduplicação, mudança de estado e registro.
                con.execute("BEGIN IMMEDIATE")
                cached = con.execute("SELECT * FROM commands WHERE id=?", (body.request_id,)).fetchone()
                if cached:
                    if cached["payload"] != payload:
                        raise HTTPException(409, "request_id já usado com outro conteúdo; escolha outro ID")
                    result, code = json.loads(cached["result"]), cached["code"]
                else:
                    d = devices.get(body.device_id)
                    code, reason = 200, None
                    if d is None:
                        code, reason = 404, "device_not_found"
                    elif not d["available"]:
                        code, reason = 503, "device_unavailable"
                    elif body.action not in d["capabilities"]:
                        code, reason = 422, "unsupported_action"
                    current = con.execute("SELECT * FROM states WHERE id=?", (body.device_id,)).fetchone()
                    if not reason and d.get("source")!="home_assistant" and body.action == "set_color" and current["state"] != "on":
                        code, reason = 409, "light_off_turn_on_first"
                    result = {"request_id": body.request_id, "device_id": body.device_id,
                              "action": body.action, "source": d.get("source","simulation") if d else "simulation",
                              "timestamp": datetime.now(timezone.utc).isoformat(),
                              "status": "failed" if reason else "confirmed"}
                    if reason:
                        result["error"] = reason
                    elif d.get('source')=='home_assistant':
                        result['source']='home_assistant'
                        try:
                            observed=hardware.execute(d,body)
                            result.update(state=observed['state'],observed_at=observed.get('observed_at'))
                            if body.brightness is not None:result['brightness']=observed.get('brightness')
                            if body.color is not None:result['color']=observed.get('color')
                        except HTTPException as exc:
                            code=exc.status_code;result.update(status='failed',error=exc.detail)
                    else:
                        state = current["state"]
                        if body.action in {"turn_on", "turn_off"}:
                            state = "on" if body.action == "turn_on" else "off"
                            if state == "on" and current["brightness"] == 0:
                                con.execute("UPDATE states SET brightness=100 WHERE id=?", (body.device_id,))
                        elif body.action == "set_brightness":
                            state = "on" if body.brightness > 0 else "off"
                            con.execute("UPDATE states SET brightness=? WHERE id=?", (body.brightness, body.device_id))
                            result["brightness"] = body.brightness
                        else:
                            con.execute("UPDATE states SET color=? WHERE id=?", (json.dumps(body.color), body.device_id))
                            result["color"] = list(body.color)
                        con.execute("UPDATE states SET state=? WHERE id=?", (state, body.device_id))
                        result["state"] = state
                    con.execute("INSERT INTO commands VALUES (?, ?, ?, ?)",
                                (body.request_id, payload, code, json.dumps(result)))
            if code != 200:
                raise HTTPException(code, detail=result)
            return result

    @api.get("/api/v1/commands/{request_id}")
    def get_command(request_id: str):
        with connect() as con:
            row = con.execute("SELECT result FROM commands WHERE id=?", (request_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Comando não encontrado")
        return json.loads(row["result"])

    @api.get("/api/v1/events")
    def events(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        with connect() as con:
            rows = con.execute("SELECT result FROM commands ORDER BY rowid DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        return [json.loads(row["result"]) for row in rows]

    @api.post("/api/v1/text")
    def text_command(body: TextRequest):
        phrase = normalize_text(body.text)
        phrase = re.sub(r"^aether[, ]+", "", phrase).strip()
        base = {"request_id": body.request_id, "source": "simulation", "engine": "rules"}
        def reply(status, message, **extra):
            return {**base, "status": status, "message": message, **extra}
        if phrase in {"qual o consumo previsto", "qual e o consumo previsto", "qual o consumo previsto para a proxima hora", "qual e o consumo previsto para a proxima hora", "previsao de consumo"}:
            result = forecast_summary()
            return reply(result["status"], result["message"], forecast=result.get("forecast"))
        colors = {"azul": [0, 0, 255], "verde": [0, 255, 0], "vermelho": [255, 0, 0],
                  "branco": [255, 255, 255], "roxo": [128, 0, 255], "amarelo": [255, 255, 0], "vermelha": [255, 0, 0], "branca": [255, 255, 255], "roxa": [128, 0, 255], "amarela": [255, 255, 0]}
        action_name, target, extra, kind = None, None, {}, None
        power = re.fullmatch(r"(ligue|ligar|liga|acenda|desligue|desligar|desliga|apague) (?:a |o )?(.+)", phrase)
        brightness = re.fullmatch(r"(?:coloque|ajuste|defina) (?:o )?brilho (?:da |do |de )?(.+?) (?:em|para) (-?\d+)(?:%| por cento)?", phrase)
        color = re.fullmatch(r"(?:coloque|deixe|deixa) (?:a )?(.+?)(?: (?:em|na cor))? (azul|verde|vermelho|vermelha|branco|branca|roxo|roxa|amarelo|amarela)", phrase)
        temp = re.fullmatch(r"(?:qual (?:e |foi )?a (?:ultima )?|consulte a (?:ultima )?|consultar a (?:ultima )?)?(?:ultima )?temperatura(?: registrada| medida)?(?: (?:da |do |de |na |no |em )?(.+?))?(?: e (?:em que horario|qual (?:e |foi )?o horario|quando (?:foi registrada|foi medida)))?", phrase)
        if brightness:
            target, value = brightness.groups()
            if not 0 <= int(value) <= 100:
                return reply("rejected", "O brilho deve estar entre 0 e 100%. Nenhuma ação foi executada.")
            action_name, extra, kind = "set_brightness", {"brightness": int(value)}, "light"
        elif color:
            target, value = color.groups()
            action_name, extra, kind = "set_color", {"color": colors[value]}, "light"
        elif temp:
            target, kind = temp.group(1), "temperature_sensor"
        elif power:
            verb, target = power.groups()
            action_name = "turn_on" if verb in {"ligue", "ligar", "liga", "acenda"} else "turn_off"
        else:
            return reply("not_understood", "Ainda não reconheço essa frase. Use um dos exemplos e envie uma ação por vez. Nenhuma ação foi executada.")
        candidates = []
        room_names = {r["id"]: normalize_text(r["name"]) for r in config["rooms"]}
        for d in list(devices.values()):
            sensor = d.get("kind") == "temperature_sensor"
            light = bool(re.match(r"(?:luz|lampada)\b", normalize_text(d["name"])))
            if kind == "temperature_sensor" and not sensor: continue
            if kind == "light" and not light: continue
            if kind is None and sensor: continue
            aliases = {normalize_text(d["name"]), normalize_text(d["id"]), normalize_text(d["id"].replace("-", " "))}
            if kind in {"light", "temperature_sensor"}:
                aliases.update({room_names[d["room_id"]], normalize_text(d["room_id"])})
            # Comparação exata impede executar parcialmente pedidos compostos ou negativos.
            if target is None or target in aliases or (target in {"luz", "lampada"} and light) or (target == "tomada" and normalize_text(d["name"]).startswith("tomada")):
                candidates.append(d)
        if len(candidates) != 1:
            return reply("needs_clarification", "Informe o nome completo do dispositivo ou o cômodo. Nenhuma ação foi executada.",
                         candidates=[{"id": d["id"], "name": d["name"]} for d in candidates], pending_command={"action":action_name,**extra} if action_name and candidates else None)
        d = candidates[0]
        try:
            if kind == "temperature_sensor":
                reading = latest_temperature(d["id"])
                if reading["value"] is None:
                    return reply("no_reading", "Esse sensor ainda não tem uma amostra registrada.", reading=reading)
                return reply("answered", f"Última temperatura registrada em {d['name']}: {reading['value']:g} °C. Consulte o horário da amostra abaixo.", reading=reading)
            result = command(Command(request_id=body.request_id, device_id=d["id"], action=action_name, **extra))
            return reply("confirmed", f"Comando confirmado para {d['name']}.", command=result)
        except HTTPException as exc:
            reason = exc.detail.get("error") if isinstance(exc.detail, dict) else exc.detail
            messages = {"unsupported_action": "Esse dispositivo não suporta essa função.",
                        "device_unavailable": "O dispositivo está indisponível.",
                        "light_off_turn_on_first": "Ligue a luz antes de alterar sua cor."}
            return reply("failed", messages.get(reason, str(reason)), error=exc.detail, http_status=exc.status_code)

    extra = setup_extensions(api,connect,config,devices,config_file,list_devices,lambda data: command(Command(**data)),ROOT,mutation_lock)
    setup_assistant(api, connect, list_devices, forecast_summary, lambda text, rid: text_command(TextRequest(text=text, request_id=rid)),extra,lambda:config['rooms'])
    # AETHER_ENERGY_COACH_V1
    from .energy_coach import setup as setup_energy_coach
    setup_energy_coach(api, connect, ROOT)
    # AETHER_MAQUETTE_V12
    from .maquette import setup as setup_maquette
    setup_maquette(api, connect, ROOT)
    # AETHER_LOCAL_NLU_V14
    from .local_chat import setup as setup_local_chat
    setup_local_chat(api, connect)
    # AETHER_LOCAL_BOTH_V16
    api.state.registered_devices=list_devices
    api.state.registered_rooms=lambda:config['rooms']
    api.state.registered_command=lambda data:command(Command(**data))
    # AETHER_NEURAL_V20
    from .neural_api import setup as setup_neural
    setup_neural(api, ROOT)
    return api


app = create_app()
