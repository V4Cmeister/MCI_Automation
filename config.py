from datetime import datetime

# --- Zeitraum ---
EXPORT_START = 1749028771
EXPORT_END = 1749028947

# --- Graph-Auswahl (auskommentieren = nicht exportieren) ---
EXPORT_GRAPHS = {
    "final_weight_distribution": True,
    "fill_level_vs_final_weight": True,
    "vibration_index_over_time": True,
    "temperature_per_dispenser": True,
    "crack_rate_pie": True
}