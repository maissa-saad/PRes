"""
Simulation 1 : Comparaison Edge vs Fog vs Cloud
================================================
- Topologie étoile : 1 device + 3 nœuds (Edge, Fog, Cloud)
- IPT proches : Edge=200-300, Fog=1000-2000, Cloud=10000-12000
- Population NON déterministe : distribution de Poisson
- Mesure : délai moyen de bout en bout
- Courbe : délai en fonction de l'IPT pour chaque niveau
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
from yafs.distribution import exponential_distribution  # Poisson <-> inter-arrivées exponentielles

os.makedirs("results_ipt", exist_ok=True)

# ─────────────────────────────────────────────
# PARAMÈTRES
# ─────────────────────────────────────────────

# Plages d'IPT pour chaque niveau (MIPS)
IPT_EDGE_VALUES  = [200, 250, 300]
IPT_FOG_VALUES   = [1000, 1500, 2000]
IPT_CLOUD_VALUES = [10000, 11000, 12000]

PR_DEVICE_EDGE   = 2    # ms - délai device -> edge
PR_EDGE_FOG      = 5    # ms - délai edge -> fog
PR_FOG_CLOUD     = 10   # ms - délai fog -> cloud

INSTRUCTIONS     = 2000  # charge de calcul du message (en MIPS*ms)
SIM_TIME         = 5000  # durée de simulation
POISSON_RATE     = 100   # taux moyen d'arrivée (1 message toutes les 100 unités)


# ─────────────────────────────────────────────
# TOPOLOGIE ÉTOILE
# ─────────────────────────────────────────────
def create_topology(ipt_edge, ipt_fog, ipt_cloud):
    """
    Topologie en étoile :
    Device(1) --> Edge(0) --> Fog(2) --> Cloud(3)
                     |
                  Sink(4)
    """
    t = Topology()
    G = nx.Graph()

    # Noeuds
    G.add_node(0, IPT=ipt_edge,  RAM=4000)   # EDGE
    G.add_node(1, IPT=99999,     RAM=2000)   # DEVICE (source)
    G.add_node(2, IPT=ipt_fog,   RAM=8000)   # FOG
    G.add_node(3, IPT=ipt_cloud, RAM=16000)  # CLOUD
    G.add_node(4, IPT=99999,     RAM=2000)   # SINK (actuator)

    # Liens
    G.add_edge(1, 0, BW=100, PR=PR_DEVICE_EDGE)   # Device -> Edge
    G.add_edge(0, 2, BW=100, PR=PR_EDGE_FOG)       # Edge   -> Fog
    G.add_edge(2, 3, BW=100, PR=PR_FOG_CLOUD)      # Fog    -> Cloud
    G.add_edge(0, 4, BW=100, PR=1)                 # Edge   -> Sink

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
                 instructions=INSTRUCTIONS,
                 bytes=500000)
    m2 = Message("M2", "Processing", "Actuator",
                 instructions=100,
                 bytes=100000)

    app.add_source_messages(m1)
    app.add_service_module("Processing", m1, m2, lambda: 1.0)
    return app


# ─────────────────────────────────────────────
# PLACEMENT
# ─────────────────────────────────────────────
def make_placement(node_id):
    return JSONPlacement(name="pl", json={
        "initialAllocation": [
            {"app": "App", "module_name": "Processing", "id_resource": node_id}
        ]
    })


# ─────────────────────────────────────────────
# CALCUL DÉLAI
# ─────────────────────────────────────────────
def compute_delay(filepath):
    try:
        df      = pd.read_csv(filepath + ".csv")
        df_link = pd.read_csv(filepath + "_link.csv")
    except FileNotFoundError:
        return float("nan")

    df_comp = df[df["type"] == "COMP_M"].copy()
    if df_comp.empty:
        return float("nan")

    # Délai moyen = traitement + réseau
    delay_proc = (df_comp["time_out"] - df_comp["time_emit"]).mean()
    delay_net  = df_link["latency"].mean()
    return delay_proc + delay_net


# ─────────────────────────────────────────────
# UNE SIMULATION
# ─────────────────────────────────────────────
def run_sim(ipt_edge, ipt_fog, ipt_cloud, node_id, tag):
    t   = create_topology(ipt_edge, ipt_fog, ipt_cloud)
    app = create_app()
    pl  = make_placement(node_id)

    filepath = f"results_ipt/{tag}"
    s = Sim(t, default_results_path=filepath)
    s.deploy_app(app, pl, DeviceSpeedAwareRouting())
    s.deploy_sink("App", node=4, module="Actuator")

    # Distribution de Poisson = inter-arrivées exponentielles
    dist = exponential_distribution(name="Poisson", lambd=POISSON_RATE)
    s.deploy_source("App", id_node=1,
                    msg=app.get_message("M1"),
                    distribution=dist)
    s.run(SIM_TIME)
    return compute_delay(filepath)


# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────
print("Démarrage des simulations...\n")

labels   = []
d_edge   = []
d_fog    = []
d_cloud  = []

# On compare les 3 niveaux pour chaque "palier" d'IPT
for i in range(len(IPT_EDGE_VALUES)):
    ipt_e = IPT_EDGE_VALUES[i]
    ipt_f = IPT_FOG_VALUES[i]
    ipt_c = IPT_CLOUD_VALUES[i]

    label = f"E={ipt_e}\nF={ipt_f}\nC={ipt_c}"
    labels.append(label)

    print(f"[{i+1}/3] IPT Edge={ipt_e} | Fog={ipt_f} | Cloud={ipt_c}")

    de = run_sim(ipt_e, ipt_f, ipt_c, node_id=0, tag=f"edge_{i}")
    df_ = run_sim(ipt_e, ipt_f, ipt_c, node_id=2, tag=f"fog_{i}")
    dc = run_sim(ipt_e, ipt_f, ipt_c, node_id=3, tag=f"cloud_{i}")

    d_edge.append(de)
    d_fog.append(df_)
    d_cloud.append(dc)

    print(f"    Edge={de:.2f}  Fog={df_:.2f}  Cloud={dc:.2f}")


# ─────────────────────────────────────────────
# COURBE
# ─────────────────────────────────────────────
x = np.arange(len(labels))
width = 0.25

fig, ax = plt.subplots(figsize=(10, 6))

bars_e = ax.bar(x - width, d_edge,  width, label="Edge",  color="steelblue")
bars_f = ax.bar(x,         d_fog,   width, label="Fog",   color="orange")
bars_c = ax.bar(x + width, d_cloud, width, label="Cloud", color="tomato")

ax.set_xlabel("Configuration IPT (Edge / Fog / Cloud) en MIPS")
ax.set_ylabel("Délai moyen de bout en bout (ms)")
ax.set_title("Comparaison Edge vs Fog vs Cloud\n(population Poisson, topologie étoile)")
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=9)
ax.legend()
ax.grid(True, linestyle="--", alpha=0.5, axis="y")
plt.tight_layout()
plt.savefig("results_ipt/comparaison_niveaux.png", dpi=150)
print("\nCourbe sauvegardée : results_ipt/comparaison_niveaux.png")
plt.show()
