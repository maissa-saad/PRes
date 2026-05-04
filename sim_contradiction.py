"""
Simulation 3 : Contradiction entre délai aller-retour et IPT
=============================================================
Le prof dit : "montrer que le temps aller-retour et l'IPT sont contradictoires"

-> Un IPT élevé = traitement rapide = bon pour la latence de calcul
-> Mais un nœud puissant (Cloud) est souvent LOIN = délai réseau aller-retour élevé
-> Ces deux effets s'opposent : c'est la contradiction à montrer

Courbe : 
  - X = IPT Cloud (de faible à très élevé)
  - Y gauche = délai de calcul seul (diminue quand IPT augmente)
  - Y droite = délai réseau aller-retour (constant, lié à la distance)
  - On montre que les deux courbes évoluent en sens opposé
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

os.makedirs("results_contradiction", exist_ok=True)

# ─────────────────────────────────────────────
# PARAMÈTRES
# ─────────────────────────────────────────────
IPT_EDGE     = 200      # MIPS fixe
INSTRUCTIONS = 2000     # charge du message
PR_CLOUD     = 50       # délai réseau aller-retour fixe (Edge <-> Cloud)
SIM_TIME     = 5000

# IPT Cloud à faire varier
IPT_CLOUD_VALUES = [200, 300, 500, 800, 1000, 2000, 5000, 10000, 12000]


# ─────────────────────────────────────────────
# TOPOLOGIE
# ─────────────────────────────────────────────
def create_topology(ipt_cloud, pr_cloud):
    t = Topology()
    G = nx.Graph()

    G.add_node(0, IPT=IPT_EDGE,  RAM=4000)    # EDGE
    G.add_node(1, IPT=99999,     RAM=2000)    # SOURCE
    G.add_node(2, IPT=99999,     RAM=2000)    # SINK
    G.add_node(3, IPT=ipt_cloud, RAM=16000)   # CLOUD

    G.add_edge(1, 0, BW=100, PR=2)
    G.add_edge(0, 2, BW=100, PR=2)
    G.add_edge(0, 3, BW=100, PR=pr_cloud)     # lien Edge <-> Cloud

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
# CALCUL DÉLAI SÉPARÉ (calcul vs réseau)
# ─────────────────────────────────────────────
def compute_delays_separated(filepath):
    try:
        df      = pd.read_csv(filepath + ".csv")
        df_link = pd.read_csv(filepath + "_link.csv")
    except FileNotFoundError:
        return float("nan"), float("nan")

    df_comp = df[df["type"] == "COMP_M"].copy()
    if df_comp.empty:
        return float("nan"), float("nan")

    # Délai de calcul pur (temps passé dans le module)
    delay_calcul = (df_comp["time_out"] - df_comp["time_emit"]).mean()

    # Délai réseau aller-retour (tous les sauts réseau)
    delay_reseau = df_link["latency"].mean()

    return delay_calcul, delay_reseau


# ─────────────────────────────────────────────
# UNE SIMULATION
# ─────────────────────────────────────────────
def run_sim(ipt_cloud, node_id, tag):
    t   = create_topology(ipt_cloud, PR_CLOUD)
    app = create_app()
    pl  = JSONPlacement(name="pl", json={
        "initialAllocation": [
            {"app": "App", "module_name": "Processing", "id_resource": node_id}
        ]
    })

    filepath = f"results_contradiction/{tag}"
    s = Sim(t, default_results_path=filepath)
    s.deploy_app(app, pl, DeviceSpeedAwareRouting())
    s.deploy_sink("App", node=2, module="Actuator")

    dist = exponential_distribution(name="Poisson", lambd=100)
    s.deploy_source("App", id_node=1,
                    msg=app.get_message("M1"),
                    distribution=dist)
    s.run(SIM_TIME)
    return compute_delays_separated(filepath)


# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────
print("Simulation contradiction IPT vs aller-retour...\n")

calculs_cloud  = []
reseaux_cloud  = []
calculs_edge   = []
reseaux_edge   = []

# Edge : une seule fois (IPT fixe)
dc_e, dr_e = run_sim(IPT_CLOUD_VALUES[0], node_id=0, tag="edge_ref")

for ipt_c in IPT_CLOUD_VALUES:
    print(f"IPT Cloud = {ipt_c}")
    dc, dr = run_sim(ipt_c, node_id=3, tag=f"cloud_{ipt_c}")
    calculs_cloud.append(dc)
    reseaux_cloud.append(dr)
    calculs_edge.append(dc_e)
    reseaux_edge.append(dr_e)
    print(f"  Cloud : calcul={dc:.2f}  réseau={dr:.2f}")
    print(f"  Edge  : calcul={dc_e:.2f}  réseau={dr_e:.2f}")


# ─────────────────────────────────────────────
# COURBE PRINCIPALE : la contradiction
# ─────────────────────────────────────────────
fig, ax1 = plt.subplots(figsize=(11, 6))

color_calcul = "steelblue"
color_reseau = "tomato"

# Délai de calcul Cloud (diminue avec l'IPT)
line1, = ax1.plot(IPT_CLOUD_VALUES, calculs_cloud,
                  marker='o', color=color_calcul, linewidth=2,
                  label="Délai de calcul Cloud (diminue avec IPT)")

# Délai réseau aller-retour Cloud (constant)
ax2 = ax1.twinx()
line2, = ax2.plot(IPT_CLOUD_VALUES, reseaux_cloud,
                  marker='s', linestyle='--', color=color_reseau, linewidth=2,
                  label=f"Délai réseau aller-retour Cloud (PR={PR_CLOUD} ms, constant)")

# Délai total Cloud
delais_total_cloud = [c + r for c, r in zip(calculs_cloud, reseaux_cloud)]
line3, = ax1.plot(IPT_CLOUD_VALUES, delais_total_cloud,
                  marker='^', linestyle=':', color='purple', linewidth=2,
                  label="Délai total Cloud (calcul + réseau)")

# Délai Edge (référence, constant)
ax1.axhline(y=dc_e + dr_e, color='green', linestyle='-.', linewidth=1.5,
            label=f"Délai total Edge (référence, IPT={IPT_EDGE})")

ax1.set_xlabel("IPT Cloud (MIPS)")
ax1.set_ylabel("Délai de calcul (ms)", color=color_calcul)
ax2.set_ylabel("Délai réseau aller-retour (ms)", color=color_reseau)
ax1.tick_params(axis='y', labelcolor=color_calcul)
ax2.tick_params(axis='y', labelcolor=color_reseau)

lines = [line1, line2, line3]
labels_lines = [l.get_label() for l in lines]
ax1.legend(lines, labels_lines, loc='upper right', fontsize=9)

ax1.set_title(
    "Contradiction entre IPT et délai aller-retour\n"
    "Augmenter l'IPT réduit le calcul mais ne compense pas le délai réseau"
)
ax1.grid(True, linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig("results_contradiction/contradiction_ipt_aller_retour.png", dpi=150)
print("\nCourbe sauvegardée : results_contradiction/contradiction_ipt_aller_retour.png")
plt.show()
