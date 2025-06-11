import os
from pathlib import Path
from datetime import datetime
from tinydb import TinyDB, Query
import matplotlib.pyplot as plt
import pandas as pd
from config import EXPORT_START, EXPORT_END, EXPORT_GRAPHS

DB_PATH = Path("db/data.json")
REPORT_ROOT = Path("report")

# Hole Daten aus TinyDB
def load_data():
    db = TinyDB(DB_PATH)
    data = db.all()
    df = pd.json_normalize(data)

    # Zeitstempel als int speichern (fällt zurück auf 0 falls nicht vorhanden)
    df["timestamp"] = df.get("final_weight.time", df.get("timestamp", 0)).fillna(0).astype(int)

    # Zeitraumfilter
    df = df[(df["timestamp"] >= EXPORT_START) & (df["timestamp"] <= EXPORT_END)]

    return df


# Reportverzeichnis vorbereiten
def create_report_dir():
    now = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = REPORT_ROOT / now
    path.mkdir(parents=True, exist_ok=True)
    return path

# 1: Histogramm Endgewicht
def plot_final_weight_distribution(df, outdir):
    weights = df["final_weight.final_weight"].dropna()
    plt.figure()
    plt.hist(weights, bins=20)
    plt.title("Endgewicht-Verteilung")
    plt.xlabel("Gramm")
    plt.ylabel("Häufigkeit")
    plt.savefig(outdir / "final_weight_distribution.svg")
    plt.close()

# 2: Scatter: Füllmenge vs. Endgewicht
def plot_fill_vs_weight(df, outdir):
    plt.figure()
    plt.scatter(df["dispenser_green.fill_level_grams"], df["final_weight.final_weight"], label="Grün", alpha=0.6)
    plt.scatter(df["dispenser_blue.fill_level_grams"], df["final_weight.final_weight"], label="Blau", alpha=0.6)
    plt.scatter(df["dispenser_red.fill_level_grams"], df["final_weight.final_weight"], label="Rot", alpha=0.6)
    plt.title("Füllmenge vs. Endgewicht")
    plt.xlabel("Füllmenge (g)")
    plt.ylabel("Endgewicht (g)")
    plt.legend()
    plt.savefig(outdir / "fill_level_vs_final_weight.svg")
    plt.close()

# 3: Vibration über Zeit
def plot_vibration(df, outdir):
    plt.figure()
    for color in ["red", "blue", "green"]:
        col = f"dispenser_{color}.vibration-index"
        plt.plot(pd.to_datetime(df["timestamp"], unit='s'), df[col], label=color)
    plt.title("Vibrationsindex über Zeit")
    plt.xlabel("Zeit")
    plt.ylabel("Vibration Index")
    plt.legend()
    plt.savefig(outdir / "vibration_index_over_time.svg")
    plt.close()

# 4: Temperatur nach Dispenser
def plot_temperature(df, outdir):
    df_temp = df[df["type"] == "temperature"]
    if df_temp.empty:
        return
    plt.figure()
    for color in df_temp["dispenser"].unique():
        subset = df_temp[df_temp["dispenser"] == color]
        timestamps = pd.to_datetime(subset["time"].astype(int), unit="s")
        plt.plot(timestamps, subset["temperature_C"], label=color)
    plt.title("Temperaturverlauf je Dispenser")
    plt.xlabel("Zeit")
    plt.ylabel("°C")
    plt.legend()
    plt.savefig(outdir / "temperature_per_dispenser.svg")
    plt.close()

# 5: Defektanteil
def plot_crack_pie(df, outdir):
    values = df["ground_truth.is_cracked"].dropna().astype(str)
    counts = values.value_counts()
    labels = ["Defekt" if k == "1" else "Intakt" for k in counts.index]
    plt.figure()
    plt.pie(counts, labels=labels, autopct="%1.1f%%", startangle=90)
    plt.title("Defektquote Flaschen")
    plt.savefig(outdir / "crack_rate_pie.svg")
    plt.close()

# Main-Funktion
def generate_report():
    df = load_data()
    outdir = create_report_dir()
    if EXPORT_GRAPHS.get("final_weight_distribution"):
        plot_final_weight_distribution(df, outdir)
    if EXPORT_GRAPHS.get("fill_level_vs_final_weight"):
        plot_fill_vs_weight(df, outdir)
    if EXPORT_GRAPHS.get("vibration_index_over_time"):
        plot_vibration(df, outdir)
    if EXPORT_GRAPHS.get("temperature_per_dispenser"):
        plot_temperature(df, outdir)
    if EXPORT_GRAPHS.get("crack_rate_pie"):
        plot_crack_pie(df, outdir)

    print(f"✅ Report gespeichert unter: {outdir.resolve()}")

if __name__ == "__main__":
    generate_report()
