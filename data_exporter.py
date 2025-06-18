#!/usr/bin/env python3
import os
import csv
import json
from tinydb import TinyDB

DB_PATH  = 'db/data.json'
OUT_DIR  = 'regression'
OUT_FILE = os.path.join(OUT_DIR, 'Collected_data.csv')

db      = TinyDB(DB_PATH)
entries = db.all()
data    = {}

# 1) Dispenser-, final_weight-, drop_oscillation- und ground_truth-Daten einsammeln, Zeiten merken
for e in entries:
    if 'bottle' in e and e.get('type') != 'temperature':
        b   = e['bottle']
        rec = data.setdefault(b, {})

        # Dispenser
        for color in ('red','blue','green'):
            key = f'dispenser_{color}'
            if key in e:
                disp = e[key]
                rec[f'vibration_index_{color}']  = disp.get('vibration-index',    0.0)
                rec[f'fill_level_grams_{color}'] = disp.get('fill_level_grams',   0.0)
                rec[f'_time_{color}']            = disp.get('time')

        # final_weight
        if 'final_weight' in e:
            rec['final_weight'] = e['final_weight'].get('final_weight', 0.0)

        # drop_oscillation (Liste von Strings)
        if 'drop_oscillation' in e:
            rec['drop_oscillation'] = e['drop_oscillation'].get('drop_oscillation', [])

        # is_cracked
        if 'ground_truth' in e:
            rec['is_cracked'] = int(e['ground_truth'].get('is_cracked', 0))

# 2) Temperatur-Daten zuordnen (via bottle oder Zeitstempel)
for e in entries:
    if e.get('type') == 'temperature':
        color = e['dispenser']
        temp  = e.get('temperature_C', 0.0)
        if 'bottle' in e:
            rec = data.setdefault(e['bottle'], {})
            rec[f'temperature_{color}'] = temp
        else:
            t = e.get('time')
            for rec in data.values():
                if rec.get(f'_time_{color}') == t:
                    rec[f'temperature_{color}'] = temp
                    break

# 3) CSV schreiben, nur vollständige Feature-Sätze (kein 0.0 bei den numerischen Features)
os.makedirs(OUT_DIR, exist_ok=True)

header = [
    'bottle',
    'vibration_index_red','fill_level_grams_red',
    'vibration_index_blue','fill_level_grams_blue',
    'vibration_index_green','fill_level_grams_green',
    'final_weight',
    'temperature_green','temperature_red','temperature_blue',
    'drop_oscillation',
    'is_cracked'
]

with open(OUT_FILE, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    kept = 0

    for b, rec in data.items():
        # Numerische Features sammeln (ohne drop_oscillation und label)
        features = []
        for c in ('red','blue','green'):
            features += [
                rec.get(f'vibration_index_{c}', 0.0),
                rec.get(f'fill_level_grams_{c}', 0.0)
            ]
        features.append(rec.get('final_weight', 0.0))
        for c in ('green','red','blue'):
            features.append(rec.get(f'temperature_{c}', 0.0))

        # Label und drop_oscillation holen
        label = rec.get('is_cracked')
        drops = rec.get('drop_oscillation')

        # Nur weiter, wenn Label und drop_oscillation existieren
        if label is None or drops is None:
            continue

        # Kein numerisches Feature darf 0.0 sein
        if any(val == 0.0 for val in features):
            continue

        # drop_oscillation als JSON-String
        drop_str = json.dumps(drops, ensure_ascii=False)

        # Zeile schreiben
        writer.writerow([b] + features + [drop_str, label])
        kept += 1

print(f"✔ '{OUT_FILE}' erstellt. {kept} vollständige Datensätze.") 
