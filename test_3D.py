"""
Simulation YAFS - Courbe 3D interactive (Plotly)
=================================================
Axes :
  X = Rapport IPT_cloud / IPT_edge  (en %)
  Y = Délai réseau Edge <-> Cloud   (PR, en ms)
  Z = Délai global de bout en bout  (ms)

Plusieurs surfaces = plusieurs tailles de workflow (nb d'instructions)

Lancer : python main_3D_interactif.py
"""

import os
import itertools
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import networkx as nx

from yafs.core import Sim
from yafs.topology import Topology
from yafs.application import Application, Message
from yafs.placement import JSONPlacement
from yafs.path_routing import DeviceSpeedAwareRouting
from yafs.distribution import deterministic_distribution

# ─────────────────────────────────────────────
# PARAMÈTRES DE LA GRILLE DE SIMULATION
# ─────────────────────────────────────────────

IPT_EDGE = 200          # MIPS fixe pour le edge

# Rapports IPT_cloud / IPT_edge à tester  (%)
# 100% = même puissance, 500% = cloud 5x plus puissant
IPT_RATIOS_PCT = [100, 150, 200, 300, 500, 1000]

# Délais réseau Edge <-> Cloud à tester (ms / unités sim)
PR_VALUES = [1, 2, 5, 10, 20, 50, 100, 200]

# Tailles de workflow (instructions en unités sim)
# Petit = 500, Moyen = 2000, Gros = 10000
WORKFLOW_SIZES = {
    "Petit  (500 instr)":  500,
    "Moyen  (2000 instr)": 2000,
    "Gros   (10000 instr)": 10000,
}

SIM_TIME = 3000
os.makedirs("results3d", exist_ok=True)


# ─────────────────────────────────────────────
# TOPOLOGIE
# ─────────────────────────────────────────────
def create_topology(IPT_cloud, PR_edge_cloud):
    t = Topology()
    G = nx.Graph()

    G.add_node(0, IPT=IPT_EDGE,  RAM=4000)   # EDGE
    G.add_node(1, IPT=99999,     RAM=2000)   # SOURCE (neutre)
    G.add_node(2, IPT=99999,     RAM=2000)   # SINK   (neutre)
    G.add_node(3, IPT=IPT_cloud, RAM=8000)   # CLOUD

    G.add_edge(1, 0, BW=100, PR=1)               # Source -> Edge  (fixe 1ms)
    G.add_edge(0, 2, BW=100, PR=1)               # Edge   -> Sink  (fixe 1ms)
    G.add_edge(0, 3, BW=100, PR=PR_edge_cloud)    # Edge   -> Cloud (variable)

    t.G = G
    return t


# ─────────────────────────────────────────────
# APPLICATION
# ─────────────────────────────────────────────
def create_app(instructions):
    app = Application(name="App")
    app.set_modules([
        {"Sensor":     {"Type": Application.TYPE_SOURCE}},
        {"Processing": {"RAM": 10, "Type": Application.TYPE_MODULE}},
        {"Actuator":   {"Type": Application.TYPE_SINK}}
    ])

    m1 = Message("M1", "Sensor", "Processing",
                 instructions=instructions,
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
def make_placement(node_id, name):
    return JSONPlacement(name=name, json={
        "initialAllocation": [
            {"app": "App", "module_name": "Processing", "id_resource": node_id}
        ]
    })


# ─────────────────────────────────────────────
# CALCUL DÉLAI
# ─────────────────────────────────────────────
def compute_delay(file):
    try:
        df      = pd.read_csv(file + ".csv")
        df_link = pd.read_csv(file + "_link.csv")
    except FileNotFoundError:
        return float("nan")

    df_comp = df[df["type"] == "COMP_M"].copy()
    if df_comp.empty:
        return float("nan")

    delay_proc    = (df_comp["time_out"] - df_comp["time_emit"]).mean()
    delay_network = df_link["latency"].mean()
    return delay_proc + delay_network


# ─────────────────────────────────────────────
# UNE SIMULATION
# ─────────────────────────────────────────────
def run_sim(IPT_cloud, PR_edge_cloud, instructions, placement_node, name_tag):
    fname = f"results3d/{name_tag}"
    t     = create_topology(IPT_cloud, PR_edge_cloud)
    app   = create_app(instructions)
    pl    = make_placement(placement_node, name_tag)

    s = Sim(t, default_results_path=fname)
    s.deploy_app(app, pl, DeviceSpeedAwareRouting())
    s.deploy_sink("App", node=2, module="Actuator")
    s.deploy_source("App", id_node=1,
                    msg=app.get_message("M1"),
                    distribution=deterministic_distribution(100, name="Det"))
    s.run(SIM_TIME)
    return compute_delay(fname)


# ─────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ─────────────────────────────────────────────
# Résultats : dict[workflow_label] -> 2D array (ratio x PR)
results_cloud = {label: np.full((len(IPT_RATIOS_PCT), len(PR_VALUES)), np.nan)
                 for label in WORKFLOW_SIZES}
results_edge  = {label: np.full((len(IPT_RATIOS_PCT), len(PR_VALUES)), np.nan)
                 for label in WORKFLOW_SIZES}

total = len(WORKFLOW_SIZES) * len(IPT_RATIOS_PCT) * len(PR_VALUES)
done  = 0

print(f"Démarrage : {total * 2} simulations au total\n")

for label, instr in WORKFLOW_SIZES.items():
    for i, ratio_pct in enumerate(IPT_RATIOS_PCT):
        IPT_cloud = int(IPT_EDGE * ratio_pct / 100)
        for j, PR in enumerate(PR_VALUES):
            tag_c = f"cloud_r{ratio_pct}_pr{PR}_w{instr}"
            tag_e = f"edge_r{ratio_pct}_pr{PR}_w{instr}"

            d_cloud = run_sim(IPT_cloud, PR, instr, 3, tag_c)
            d_edge  = run_sim(IPT_cloud, PR, instr, 0, tag_e)

            results_cloud[label][i, j] = d_cloud
            results_edge [label][i, j] = d_edge

            done += 2
            print(f"[{done}/{total*2}] {label} | ratio={ratio_pct}% | PR={PR}"
                  f" → Cloud={d_cloud:.2f}  Edge={d_edge:.2f}")


# ─────────────────────────────────────────────
# GRAPHE 3D INTERACTIF — une surface par workflow
# ─────────────────────────────────────────────

X = np.array(IPT_RATIOS_PCT)   # ratios en %
Y = np.array(PR_VALUES)         # délais réseau
XX, YY = np.meshgrid(X, Y)     # shape (len_PR, len_ratio)

COLORS_CLOUD = ["blues",   "teal",    "aggrnyl"]
COLORS_EDGE  = ["oranges", "reds",    "sunset"]

fig = go.Figure()

for idx, (label, instr) in enumerate(WORKFLOW_SIZES.items()):
    Z_cloud = results_cloud[label].T   # shape (len_PR, len_ratio)
    Z_edge  = results_edge [label].T

    # Surface Cloud
    fig.add_trace(go.Surface(
        x=XX, y=YY, z=Z_cloud,
        name=f"Cloud — {label}",
        colorscale=COLORS_CLOUD[idx],
        opacity=0.75,
        showscale=False,
        visible=True,
        hovertemplate=(
            "IPT ratio: %{x}%<br>"
            "Délai réseau PR: %{y} ms<br>"
            "Délai e2e Cloud: %{z:.2f}<br>"
            f"Workflow: {label}<extra></extra>"
        )
    ))

    # Surface Edge
    fig.add_trace(go.Surface(
        x=XX, y=YY, z=Z_edge,
        name=f"Edge — {label}",
        colorscale=COLORS_EDGE[idx],
        opacity=0.75,
        showscale=False,
        visible=True,
        hovertemplate=(
            "IPT ratio: %{x}%<br>"
            "Délai réseau PR: %{y} ms<br>"
            "Délai e2e Edge: %{z:.2f}<br>"
            f"Workflow: {label}<extra></extra>"
        )
    ))

# ── Boutons pour afficher/masquer par workflow ──
n_wf   = len(WORKFLOW_SIZES)
labels = list(WORKFLOW_SIZES.keys())

buttons = []

# Bouton "Tout afficher"
buttons.append(dict(
    label="Tout afficher",
    method="update",
    args=[{"visible": [True] * (n_wf * 2)}]
))

# Un bouton par workflow
for k, lbl in enumerate(labels):
    vis = [False] * (n_wf * 2)
    vis[k * 2]     = True   # surface Cloud du workflow k
    vis[k * 2 + 1] = True   # surface Edge  du workflow k
    buttons.append(dict(
        label=lbl.strip(),
        method="update",
        args=[{"visible": vis}]
    ))

fig.update_layout(
    title=dict(
        text="Délai e2e : Cloud vs Edge<br>"
             "<sup>X = Rapport IPT_cloud/IPT_edge (%)  |  "
             "Y = Délai réseau Edge↔Cloud (ms)  |  "
             "Z = Délai bout-en-bout</sup>",
        font=dict(size=16)
    ),
    scene=dict(
        xaxis_title="IPT_cloud / IPT_edge (%)",
        yaxis_title="Délai réseau PR (ms)",
        zaxis_title="Délai e2e moyen",
        xaxis=dict(ticksuffix="%"),
        camera=dict(eye=dict(x=1.8, y=-1.8, z=1.2))
    ),
    updatemenus=[dict(
        type="buttons",
        direction="right",
        x=0.0, y=1.12,
        showactive=True,
        buttons=buttons
    )],
    legend=dict(x=0.75, y=0.95),
    margin=dict(l=0, r=0, b=0, t=100),
    width=1000,
    height=750,
)

# ─────────────────────────────────────────────
# GRAPHE 2D INTERACTIF — point de basculement
# ─────────────────────────────────────────────
fig2 = go.Figure()

for label, instr in WORKFLOW_SIZES.items():
    crossover_prs = []
    for i, ratio_pct in enumerate(IPT_RATIOS_PCT):
        cp = None
        for j in range(len(PR_VALUES) - 1):
            c0 = results_cloud[label][i, j]
            c1 = results_cloud[label][i, j+1]
            e0 = results_edge [label][i, j]
            e1 = results_edge [label][i, j+1]
            if (c0 - e0) * (c1 - e1) <= 0:   # changement de signe = croisement
                # Interpolation linéaire du PR de croisement
                if abs((c1-e1) - (c0-e0)) > 1e-9:
                    frac = (e0 - c0) / ((c1 - e1) - (c0 - e0))
                    cp = PR_VALUES[j] + frac * (PR_VALUES[j+1] - PR_VALUES[j])
                else:
                    cp = PR_VALUES[j]
                break
        crossover_prs.append(cp if cp is not None else np.nan)

    fig2.add_trace(go.Scatter(
        x=IPT_RATIOS_PCT,
        y=crossover_prs,
        mode="lines+markers",
        name=label.strip(),
        marker=dict(size=8),
        hovertemplate=(
            "IPT ratio: %{x}%<br>"
            "PR basculement: %{y:.1f} ms<br>"
            f"Workflow: {label}<extra></extra>"
        )
    ))

fig2.update_layout(
    title="Point de basculement Edge→Cloud selon la taille du workflow",
    xaxis_title="Rapport IPT_cloud / IPT_edge (%)",
    yaxis_title="PR de basculement (ms)",
    xaxis=dict(ticksuffix="%"),
    legend_title="Taille workflow",
    width=900,
    height=550,
    hovermode="x unified"
)

# ─────────────────────────────────────────────
# SAUVEGARDE ET AFFICHAGE
# ─────────────────────────────────────────────
fig.write_html("results3d/surface_3D.html")
fig2.write_html("results3d/basculement_2D.html")

print("\n✓ Graphique 3D  → results3d/surface_3D.html")
print("✓ Basculement   → results3d/basculement_2D.html")

fig.show()
fig2.show()
