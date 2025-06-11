import os
import json
import logging
from datetime import datetime
from pathlib import Path
from tinydb import TinyDB, Query
import paho.mqtt.client as mqtt
from credentials import MQTT_USERNAME, MQTT_PASSWORD, MQTT_BROKER, MQTT_PORT

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Datenbank vorbereiten
db_path = Path("db/data.json")
db_path.parent.mkdir(parents=True, exist_ok=True)
db = TinyDB(db_path)
Bottle = Query()

# Interner Cache zum Zwischenspeichern und Kombinieren von Subdaten (falls nötig)
data_cache = {}

# MQTT Callback: Verbindung erfolgreich
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("MQTT Verbindung hergestellt")
        client.subscribe("iot1/teaching_factory/#")
    else:
        logger.error(f"MQTT Verbindung fehlgeschlagen mit Code {rc}")

# Upsert in TinyDB (nach bottle ID)
def upsert_data(bottle_id: str, key: str, value):
    entry = db.get(Bottle.bottle == bottle_id)
    if entry:
        entry[key] = value
        db.update(entry, Bottle.bottle == bottle_id)
        logger.debug(f"Aktualisiert: bottle={bottle_id} | key={key}")
    else:
        new_entry = {"bottle": bottle_id, key: value}
        db.insert(new_entry)
        logger.debug(f"Eingefügt: bottle={bottle_id} | key={key}")

# MQTT Callback: Neue Nachricht
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode("utf-8")

    try:
        data = json.loads(payload)
        logger.debug(f"Empfangenes Topic: {topic}")
        logger.debug(f"Payload: {data}")

        # Rezeptdaten (ohne bottle_id → wird separat gespeichert)
        if "recipe" in topic:
            recipe_id = data.get("id", "unknown")
            data["creation_date"] = str(data.get("creation_date", "unknown"))
            db.insert({"type": "recipe", "recipe_id": recipe_id, "recipe": data})
            logger.info(f"Rezept {recipe_id} gespeichert")

        elif "final_weight" in topic or "drop_oscillation" in topic or "ground_truth" in topic:
            bottle_id = data.get("bottle")
            if bottle_id:
                key = topic.split("/")[-1]
                upsert_data(bottle_id, key, data)

        elif "dispenser" in topic:
            bottle_id = data.get("bottle")
            dispenser_color = data.get("dispenser")
            if not bottle_id or not dispenser_color:
                logger.warning("Ungültige dispenser Daten: bottle/dispenser fehlt")
                return
            upsert_data(bottle_id, f"dispenser_{dispenser_color}", data)

        elif "temperature" in topic:
            dispenser_color = data.get("dispenser")
            if not dispenser_color:
                logger.warning("Ungültige temperature Daten: dispenser fehlt")
                return
            db.insert({
                "type": "temperature",
                "dispenser": dispenser_color,
                "time": data.get("time"),
                "temperature_C": data.get("temperature_C")
            })
            logger.debug(f"Temperatur für {dispenser_color} gespeichert")


    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Fehler bei Payload: {payload} | Fehler: {e}")

# Haupt-Loop
def mqtt_loop():
    client = mqtt.Client()
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    mqtt_loop()
