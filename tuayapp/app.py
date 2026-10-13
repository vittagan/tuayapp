import hashlib, hmac, json, os, time, uuid
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()
app = Flask(__name__)
BASE = os.getenv("TUYA_BASE_URL", "https://openapi.tuyaeu.com").rstrip("/")
ACCESS_ID = os.getenv("TUYA_ACCESS_ID", "").strip()
ACCESS_SECRET = os.getenv("TUYA_ACCESS_SECRET", "").strip()
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "12"))

DEFAULT = [
    {"name": f"Реле {i}", "id": "", "switch_code": "switch_1",
     "dps": {"power": "cur_power", "current": "cur_current", "voltage": "cur_voltage"},
     "scale": {"power": 10, "current": 1000, "voltage": 10}}
    for i in range(1, 6)
]
DEVICES = json.loads(os.getenv("DEVICES_JSON", json.dumps(DEFAULT, ensure_ascii=False)))
if not isinstance(DEVICES, list) or len(DEVICES) != 5:
    raise RuntimeError("DEVICES_JSON должен содержать ровно 5 устройств")
_token, _expiry = None, 0

def _headers(method, path, body="", token=""):
    ts, nonce = str(int(time.time() * 1000)), uuid.uuid4().hex
    body_hash = hashlib.sha256(body.encode()).hexdigest()
    to_sign = f"{method.upper()}\n{body_hash}\n\n{path}"
    msg = f"{ACCESS_ID}{token}{ts}{nonce}{to_sign}"
    signature = hmac.new(ACCESS_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest().upper()
    return {"client_id": ACCESS_ID, "t": ts, "nonce": nonce,
            "sign": signature, "sign_method": "HMAC-SHA256", "Content-Type": "application/json"}

def _request(method, path, body=None, needs_token=True):
    global _token, _expiry
    if not ACCESS_ID or not ACCESS_SECRET:
        raise RuntimeError("Заполните TUYA_ACCESS_ID и TUYA_ACCESS_SECRET в .env")
    if needs_token and (not _token or time.time() >= _expiry):
        result = _request("GET", "/v1.0/token?grant_type=1", needs_token=False)
        _token, _expiry = result["access_token"], time.time() + int(result.get("expire_time", 3600)) - 60
    body_text = json.dumps(body, separators=(",", ":"), ensure_ascii=False) if body is not None else ""
    headers = _headers(method, path, body_text, _token if needs_token else "")
    if needs_token:
        headers["access_token"] = _token
    response = requests.request(method, BASE + path, headers=headers,
                                data=body_text if body is not None else None, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise RuntimeError(data.get("msg", "Ошибка Tuya Cloud API"))
    return data.get("result")

def _status(device):
    did = str(device.get("id", "")).strip()
    name = device.get("name", "Реле")
    if not did or did.startswith("TUYA_DEVICE_ID_"):
        return {"name": name, "id": did, "online": False, "switch": None,
                "metrics": {}, "error": "Укажите настоящий Device ID в .env"}
    try:
        rows = _request("GET", f"/v1.0/devices/{did}/status") or []
        values = {str(row.get("code")): row.get("value") for row in rows}
        metrics = {}
        for key in ("power", "current", "voltage"):
            raw = values.get(device.get("dps", {}).get(key))
            scale = device.get("scale", {}).get(key, 1)
            metrics[key] = raw / scale if isinstance(raw, (int, float)) and scale else None
        code = device.get("switch_code", "switch_1")
        return {"name": name, "id": did, "online": True, "switch": values.get(code),
                "switch_code": code, "metrics": metrics, "error": None}
    except Exception as exc:
        return {"name": name, "id": did, "online": False, "switch": None,
                "metrics": {}, "error": str(exc)}

def _set_switch(device, on):
    did = str(device.get("id", "")).strip()
    if not did or did.startswith("TUYA_DEVICE_ID_"):
        raise RuntimeError(f'{device.get("name", "Реле")}: не задан настоящий Device ID')
    code = device.get("switch_code", "switch_1")
    result = _request("POST", f"/v1.0/devices/{did}/commands",
                      {"commands": [{"code": code, "value": bool(on)}]})
    if result is False:
        raise RuntimeError(f'{device.get("name", "Реле")}: Tuya отклонила команду')
    return {"name": device.get("name", "Реле"), "success": True}

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/devices")
def devices():
    return jsonify({"devices": [_status(d) for d in DEVICES], "updated_at": int(time.time() * 1000)})

@app.post("/api/devices/<int:index>/switch")
def switch_one(index):
    if index < 0 or index >= len(DEVICES):
        return jsonify({"error": "Неизвестное устройство"}), 404
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("on"), bool):
        return jsonify({"error": "Ожидается on: true или on: false"}), 400
    try:
        return jsonify(_set_switch(DEVICES[index], data["on"]))
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

@app.post("/api/switch-all")
def switch_all():
    data = request.get_json(silent=True) or {}
    if not isinstance(data.get("on"), bool):
        return jsonify({"error": "Ожидается on: true или on: false"}), 400
    results = []
    for device in DEVICES:
        try:
            results.append(_set_switch(device, data["on"]))
        except Exception as exc:
            results.append({"name": device.get("name", "Реле"), "success": False, "error": str(exc)})
    failed = [item for item in results if not item["success"]]
    return jsonify({"results": results, "success": not failed}), (502 if failed else 200)

@app.get("/health")
def health():
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
