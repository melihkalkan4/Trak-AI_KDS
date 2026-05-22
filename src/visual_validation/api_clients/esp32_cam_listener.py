"""
ESP32-CAM listener (optional, MQTT path).

The existing src/mqtt_orchestrator.py already subscribes to
`trakaia/rover/data` and decodes the image field — we DON'T duplicate that.
This module exposes a *thin* drop-in callable that the orchestrator can
invoke for the cross-modal pipeline, and also a stand-alone subscriber
for the case where the orchestrator is not running (e.g. on a dev box
that only cares about visual consensus).

Drop-in usage from src/mqtt_orchestrator.on_message:
    from visual_validation.api_clients.esp32_cam_listener import (
        publish_field_prediction_from_payload,
    )
    publish_field_prediction_from_payload(payload, mqtt_client)

Stand-alone:
    python -m visual_validation.api_clients.esp32_cam_listener
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Optional

from .. import config
from ..models.field_yolov8 import FieldYOLOv8Predictor


logger = logging.getLogger("trakai.visual.esp32")

# Singleton — lazy-loaded so importing this module is cheap
_PREDICTOR: Optional[FieldYOLOv8Predictor] = None


def _get_predictor() -> FieldYOLOv8Predictor:
    global _PREDICTOR
    if _PREDICTOR is None:
        _PREDICTOR = FieldYOLOv8Predictor()
    return _PREDICTOR


def publish_field_prediction_from_payload(payload: dict, mqtt_client=None) -> dict | None:
    """
    Run YOLOv8 on the image inside an MQTT rover payload and (optionally)
    publish the harmonized prediction on `trakaia/visual/field`.

    Returns the prediction dict (or None when no image was present).
    """
    pred = _get_predictor().handle_mqtt_payload(payload)
    if pred is None:
        return None
    out = pred.to_dict()
    # Forward rover metadata so the consensus engine can join on site/timestamp
    for k in ("rover_id", "site_id", "lat", "lon", "timestamp"):
        if k in payload:
            out[k] = payload[k]
    if mqtt_client is not None:
        try:
            mqtt_client.publish(config.MQTT_TOPIC_FIELD_PREDICTION,
                                json.dumps(out, ensure_ascii=False))
            logger.info("Published YOLOv8 prediction -> %s",
                        config.MQTT_TOPIC_FIELD_PREDICTION)
        except Exception:                                       # noqa: BLE001
            logger.exception("MQTT publish failed")
    return out


# ---------------------------------------------------------------------------
# Stand-alone subscriber (only used outside the orchestrator)
# ---------------------------------------------------------------------------
def _run_standalone() -> int:                                    # pragma: no cover
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("paho-mqtt not installed", file=sys.stderr)
        return 1

    config.ensure_dirs()
    client = mqtt.Client(client_id="trakai-visual-field")

    def on_connect(c, _u, _f, rc, *_):
        print(f"[esp32-listener] connected rc={rc}, subscribing {config.MQTT_TOPIC_ROVER}")
        c.subscribe(config.MQTT_TOPIC_ROVER)

    def on_message(c, _u, msg):
        try:
            payload = json.loads(msg.payload)
        except Exception:                                       # noqa: BLE001
            logger.warning("non-JSON payload on %s", msg.topic)
            return
        publish_field_prediction_from_payload(payload, mqtt_client=c)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=60)
    client.loop_forever()
    return 0


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(_run_standalone())


__all__ = [
    "publish_field_prediction_from_payload",
]
