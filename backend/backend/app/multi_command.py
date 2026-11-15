
import hashlib
import json
import re
import unicodedata
from fastapi import HTTPException

def norm(text):
    text = "".join(
        c for c in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(c) != "Mn"
    )
    return " ".join(text.strip(" .?!").split())

VERBS = r"ligue|ligar|liga|acenda|acender|desligue|desligar|desliga|apague|apagar"
POWER = re.compile(r"^(" + VERBS + r")\s+(.+)$")
OFF = {"desligue", "desligar", "desliga", "apague", "apagar"}

def light(device):
    return device.get("kind") == "light" or (
        not device.get("kind")
        and re.match(r"^(luz|lampada)\b", norm(device["name"]))
    )

def resolve(target, inherited, config, devices):
    target = norm(target)
    target = re.sub(r"^(?:a|o|as|os)\s+", "", target)
    names = lambda d: {
        norm(d["name"]), norm(d["id"]),
        norm(d["id"].replace("-", " "))
    }
    # Nome completo tem prioridade, inclusive nomes contendo "e".
    exact = [d for d in devices.values() if target in names(d)]
    if exact:
        return exact, "light" if all(light(d) for d in exact) else inherited

    kind = inherited
    match = re.match(r"^(luzes|luz|lampadas|lampada|tomadas|tomada)\b\s*(.*)$", target)
    if match:
        kind = "light" if match[1] in {"luzes", "luz", "lampadas", "lampada"} else "switch"
        target = match[2]
    if kind is None:
        raise ValueError("Diga quais dispositivos deseja controlar.")

    pool = [
        d for d in devices.values()
        if (light(d) if kind == "light" else
            not light(d) and not d.get("kind", "").endswith("sensor"))
    ]

    if target in {"todas", "todos", "todas as luzes", "todos os dispositivos"}:
        return pool, kind
    if target.startswith(("todas as ", "todos os ")):
        rest = re.sub(r"^tod[ao]s (?:as|os) ", "", target)
        if rest in {"luzes", "lampadas"}:
            return [d for d in devices.values() if light(d)], "light"
        if rest == "tomadas":
            return [d for d in pool if not light(d)], "switch"

    target = re.sub(r"^(?:da|do|das|dos|na|no|de|em)\s+", "", target)
    if target in {"casa", "toda a casa", "todos os comodos"}:
        return pool, kind

    rooms = config["rooms"]
    matching_rooms = [
        r for r in rooms
        if target in {norm(r["name"]), norm(r["id"]), norm(r["id"].replace("-", " "))}
    ]
    if not matching_rooms and target == "quarto":
        matching_rooms = [
            r for r in rooms if norm(r["name"]).startswith("quarto")
        ]
    if len(matching_rooms) != 1:
        options = ", ".join(r["name"] for r in matching_rooms)
        raise ValueError(
            "Qual quarto voce quer? " + options + "."
            if options else "Nao identifiquei o comodo: " + target + "."
        )
    found = [d for d in pool if d["room_id"] == matching_rooms[0]["id"]]
    if len(found) != 1:
        raise ValueError(
            "Informe o dispositivo completo em " + matching_rooms[0]["name"] + "."
        )
    return found, kind

def plan(text, config, devices):
    phrase = re.sub(r"^aether[, ]+", "", norm(text))
    if not POWER.match(phrase):
        return None
    compound = (
        " e " in phrase or ";" in phrase or "," in phrase
        or re.search(r"\b(todas|todos)\b", phrase)
    )
    if not compound:
        return None
    if re.search(r"\b(nao|exceto|menos|depois|antes|se|quando)\b", phrase):
        raise ValueError("Esse pedido tem uma condicao. Envie as acoes separadamente.")

    clauses = re.split(r"(?:\s+e\s+|;\s*|,\s*)(?=(?:" + VERBS + r")\s)", phrase)
    actions = []
    kind = None
    for clause in clauses:
        match = POWER.fullmatch(clause.strip())
        if not match:
            raise ValueError("Nao entendi uma parte do pedido.")
        action = "turn_off" if match[1] in OFF else "turn_on"
        target = match[2]
        # Tenta o alvo completo antes de separar a lista.
        try:
            found, kind = resolve(target, kind, config, devices)
            targets = [(found, kind)]
        except ValueError:
            parts = re.split(r"\s+e\s+|,\s*|;\s*", target)
            if len(parts) == 1:
                raise
            targets = []
            for part in parts:
                found, kind = resolve(part, kind, config, devices)
                targets.append((found, kind))
        for found, _ in targets:
            if not found:
                raise ValueError("Nao encontrei dispositivos para esse pedido.")
            for device in found:
                if action not in device.get("capabilities", []):
                    raise ValueError(device["name"] + " nao suporta essa acao.")
                if not device.get("available"):
                    raise ValueError(device["name"] + " esta indisponivel.")
                item = {"device_id": device["id"], "action": action}
                if item not in actions:
                    actions.append(item)
    if len(actions) > 50:
        raise ValueError("Use no maximo cinquenta acoes por pedido.")
    return actions

def make_multi_handler(connect, config, devices, send, lock):
    with connect() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS multi_requests "
            "(id TEXT PRIMARY KEY, text TEXT NOT NULL, plan TEXT NOT NULL, result TEXT)"
        )

    def handle(text, rid):
        with lock:
            with connect() as con:
                saved = con.execute(
                    "SELECT text,plan,result FROM multi_requests WHERE id=?", (rid,)
                ).fetchone()
            if saved:
                if saved["text"] != text:
                    raise HTTPException(409, "Identificador usado com outro pedido.")
                if saved["result"]:
                    return json.loads(saved["result"])
                actions = json.loads(saved["plan"])
            else:
                try:
                    actions = plan(text, config, devices)
                except ValueError as error:
                    return {
                        "status": "rejected",
                        "message": str(error) + " Nenhuma acao foi executada.",
                        "actions_executed": False
                    }
                if actions is None:
                    return None
                with connect() as con:
                    con.execute(
                        "INSERT INTO multi_requests VALUES (?,?,?,NULL)",
                        (rid, text, json.dumps(actions))
                    )

            steps, ok, failed = [], [], []
            for index, action in enumerate(actions):
                device = devices.get(action["device_id"], {})
                name = device.get("name", action["device_id"])
                ident = "multi:" + hashlib.sha256(
                    (rid + ":" + str(index)).encode()
                ).hexdigest()
                try:
                    result = send({**action, "request_id": ident})
                    steps.append(result)
                    if result.get("status") == "confirmed":
                        verb = "liguei" if action["action"] == "turn_on" else "desliguei"
                        origin = "Na simulacao, " if result.get("source") == "simulation" else ""
                        ok.append(origin + verb + " " + name)
                    else:
                        failed.append(name)
                except HTTPException as error:
                    steps.append({
                        **action, "status": "failed", "detail": error.detail
                    })
                    failed.append(name)

            message = ". ".join(ok)
            if message:
                message += "."
            if failed:
                message += " Nao consegui concluir a acao em: " + ", ".join(failed) + "."
            result = {
                "status": "confirmed" if not failed else "partial" if ok else "failed",
                "message": message.strip(),
                "actions_executed": bool(ok),
                "routine": {
                    "type": "multi_command", "steps": steps,
                    "status": "confirmed" if not failed else "partial" if ok else "failed"
                }
            }
            with connect() as con:
                con.execute(
                    "UPDATE multi_requests SET result=? WHERE id=?",
                    (json.dumps(result, ensure_ascii=False), rid)
                )
            return result
    return handle
