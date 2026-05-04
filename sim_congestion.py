"""
Simulation 2 corrigée : Congestion et file d'attente
=====================================================
Corrections :
- On pousse le taux de charge jusqu'à ρ > 1 pour voir la vraie saturation
- On compte les messages perdus correctement via les colonnes YAFS réelles
- On affiche une seule courbe claire : délai vs taux de charge
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

from yafs.core import Sim
from yafs.topology import Topology
from yafs.application import Application, Message
from yafs.placement import JSONPlacement
from yafs.path_routing import DeviceSpeedAwareRouting
from yafs.distribution import exponential_distribution

os.makedirs("results_congestion2", exist_ok=True)

# ─────────────────────────────────────────────
# PARAMÈTRES
# ─────────────────────────────────────────────
IPT_EDGE     = 200      # MIPS
INSTRUCTIONS = 2000     # instructions par message

# Temps de service par message = INSTRUCTIONS / IPT_EDGE = 10 ms
# Saturation atteinte quand inter-arrivée < 10 ms (1 msg toutes les 10 ms)
# On fait varier l'inter-arrivée de 500ms (très faible charge) à 5ms (surcharge)
ARRIVAL_RATES = [500, 300, 200, 100, 50, 30, 20, 15, 12, 10, 8, 6, 5]

SIM_TIME = 10000  # plus long pour avoir plus de données


# ─────────────────────────────────────────────
# TOPOLOGIE
# ─────────────────────────────────────────────
def create_topology():
    t = Topology()
    G = nx.Graph()

    G.add_node(0, IPT=IPT_EDGE, RAM=4000)
    G.add_node(1, IPT=99999,    RAM=2000)   # SOURCE
    G.add_node(2, IPT=99999,    RAM=2000)   # SINK

    G.add_edge(1, 0, BW=100, PR=2)
    G.add_edge(0, 2, BW=100, PR=2)

    t.G = G
    return t


# ─────────────────────────────────────────────
# APPLICATION
# ─────────────────────────────────────────────
def create_app():
    app = Application(name="App")
    app.set_modules([
        {"Sensor":     {"Type": Application.TYPE_SOURCE}},
        {"Processing": {"RAM": 10, "Type": Application.TYPE_MODULE}},
        {"Actuator":   {"Type": Application.TYPE_SINK}}
    ])
    m1 = Message("M1", "Sensor", "Processing",
                 instructions=INSTRUCTIONS, bytes=500000)
    m2 = Message("M2", "Processing", "Actuator",
                 instructions=100, bytes=100000)
    app.add_source_messages(m1)
    app.add_service_module("Processing", m1, m2, lambda: 1.0)
    return app


# ─────────────────────────────────────────────
# CALCUL DÉLAI ET MESSAGES TRAITÉS
# ─────────────────────────────────────────────
def compute_metrics(filepath):
    try:
        df      = pd.read_csv(filepath + ".csv")
        df_link = pd.read_csv(filepath + "_link.csv")
    except FileNotFoundError:
        return float("nan"), 0, 0

    df_comp = df[df["type"] == "COMP_M"].copy()
    if df_comp.empty:
        return float("nan"), 0, 0

    # Délai moyen = calcul + réseau
    delay = (df_comp["time_out"] - df_comp["time_emit"]).mean()
    delay += df_link["latency"].mean()

    # Nombre de messages traités (COMP_M = computation message)
    n_traites = len(df_comp)

    # Nombre de messages générés (toutes les lignes où un message est émis)
    n_emis = len(df[df["type"] == "EMIT_M"]) if "EMIT_M" in df["type"].values else n_traites

    return delay, n_traites, n_emis


# ─────────────────────────────────────────────
# UNE SIMULATION
# ─────────────────────────────────────────────
def run_sim(arrival_rate, tag):
    t   = create_topology()
    app = create_app()
    pl  = JSONPlacement(name="pl", json={
        "initialAllocation": [
            {"app": "App", "module_name": "Processing", "id_resource": 0}
        ]
    })

    filepath = f"results_congestion2/{tag}"
    s = Sim(t, default_results_path=filepath)
    s.deploy_app(app, pl, DeviceSpeedAwareRouting())
    s.deploy_sink("App", node=2, module="Actuator")

    dist = exponential_distribution(name="Poisson", lambd=arrival_rate)
    s.deploy_source("App", id_node=1,
                    msg=app.get_message("M1"),
                    distribution=dist)
    s.run(SIM_TIME)
    return compute_metrics(filepath)


# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────
# Temps de traitement d'un message = INSTRUCTIONS / IPT
temps_service = INSTRUCTIONS / IPT_EDGE  # = 10 ms

print(f"IPT Edge = {IPT_EDGE} MIPS")
print(f"Instructions/message = {INSTRUCTIONS}")
print(f"Temps de service = {temps_service} ms/message")
print(f"Saturation attendue quand inter-arrivée < {temps_service} ms\n")

delays    = []
n_traites_list = []
charges   = []

for rate in ARRIVAL_RATES:
    # Taux de charge ρ = taux_arrivée / taux_service
    # taux_arrivée = 1/rate (msg/ms), taux_service = 1/temps_service (msg/ms)
    rho = temps_service / rate
    charges.append(rho)

    print(f"Inter-arrivée={rate}ms | ρ={rho:.2f}")
    d, n_t, n_e = run_sim(rate, f"rate_{rate}")
    delays.append(d)
    n_traites_list.append(n_t)
    print(f"  -> Délai={d:.2f} ms | Traités={n_t}")


# ─────────────────────────────────────────────
# COURBES
# ─────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

# ── Courbe 1 : délai vs taux de charge ──
valid = [(c, d) for c, d in zip(charges, delays) if not np.isnan(d)]
c_vals = [v[0] for v in valid]
d_vals = [v[1] for v in valid]

ax1.plot(c_vals, d_vals, marker='o', color='steelblue',
         linewidth=2, markersize=7)
ax1.axvline(x=1.0, color='red', linestyle='--', linewidth=2,
            label='Saturation (ρ = 1)')
ax1.fill_betweenx([min(d_vals)*0.95, max(d_vals)*1.05],
                  0, 1.0, alpha=0.08, color='green',
                  label='Zone sous-chargée')
ax1.fill_betweenx([min(d_vals)*0.95, max(d_vals)*1.05],
                  1.0, max(c_vals)*1.05, alpha=0.08, color='red',
                  label='Zone saturée')

ax1.set_xlabel("Taux de charge  ρ = λ / μ", fontsize=11)
ax1.set_ylabel("Délai moyen de bout en bout (ms)", fontsize=11)
ax1.set_title("Congestion : délai vs charge réseau\n"
              f"(nœud Edge, IPT={IPT_EDGE} MIPS, file M/M/1)", fontsize=11)
ax1.legend(fontsize=9)
ax1.grid(True, linestyle='--', alpha=0.5)

# ── Courbe 2 : nombre de messages traités vs inter-arrivée ──
ax2.plot(ARRIVAL_RATES, n_traites_list, marker='s',
         color='darkorange', linewidth=2, markersize=7)
ax2.axvline(x=temps_service, color='red', linestyle='--', linewidth=2,
            label=f'Saturation (inter-arrivée = {temps_service} ms)')
ax2.set_xlabel("Inter-arrivée moyenne (ms)  →  charge augmente vers la gauche",
               fontsize=10)
ax2.set_ylabel("Nombre de messages traités", fontsize=11)
ax2.set_title("Congestion : messages traités selon la charge\n"
              "(une chute = nœud saturé, messages perdus)", fontsize=11)
ax2.invert_xaxis()  # charge augmente de droite à gauche
ax2.legend(fontsize=9)
ax2.grid(True, linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig("results_congestion2/congestion.png", dpi=150)
print("\nCourbe sauvegardée : results_congestion2/congestion.png")
plt.show()