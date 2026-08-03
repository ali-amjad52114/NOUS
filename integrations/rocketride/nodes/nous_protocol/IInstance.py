"""RocketRide data-plane node: guarded, deterministic Nous execution."""
import json
import urllib.error
import urllib.request

from rocketlib import Entry, IInstanceBase, debug

from .IGlobal import IGlobal


class IInstance(IInstanceBase):
    IGlobal: IGlobal

    def __init__(self):
        super().__init__()
        self.buffer = []

    def open(self, entry: Entry):
        self.buffer = []

    def writeText(self, text: str):
        self.buffer.append(text)

    @staticmethod
    def _resolve(value, inputs):
        if isinstance(value, str) and value.startswith("$"):
            return inputs.get(value[1:], value)
        if isinstance(value, dict):
            return {k: IInstance._resolve(v, inputs) for k, v in value.items()}
        if isinstance(value, list):
            return [IInstance._resolve(v, inputs) for v in value]
        return value

    @staticmethod
    def _post(url, body):
        request = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "X-Nous-Executor": "RocketRide"})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Nous callback {url} failed ({exc.code}): {detail}") from exc

    def closing(self):
        cfg = self.IGlobal.config or {}
        try:
            payload = json.loads("".join(self.buffer))
            steps = cfg.get("steps", [])
            payload.update({
                "protocol_id": cfg["protocol_id"],
                "trigger_class": cfg["trigger_class"],
                "planned_actions": [step["action"] for step in steps],
            })
            base = cfg["callback_base"].rstrip("/")
            preconditions = self._post(base + "/actions/preconditions", payload)
            if not preconditions.get("ok"):
                raise RuntimeError(f"preconditions rejected: {preconditions}")
            results = []
            for index, step in enumerate(steps, 1):
                step_body = {**payload, "step_id": f"step-{index:03d}-{step['action']}",
                             "action": step["action"],
                             "params": self._resolve(step.get("params", {}),
                                                     payload.get("inputs", {}))}
                results.append(self._post(base + "/actions/execute", step_body))
            verification = self._post(base + "/actions/verify", payload)
            result = {"ok": bool(verification.get("ok")), "run_id": payload["run_id"],
                      "protocol_id": payload["protocol_id"],
                      "preconditions": preconditions, "steps": results,
                      "verification": verification}
        except Exception as exc:
            debug(f"Nous protocol execution failed: {exc}")
            result = {"ok": False, "error": str(exc)}
        self.instance.writeText(json.dumps(result, separators=(",", ":")))
