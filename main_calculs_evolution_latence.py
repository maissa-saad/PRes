import os
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

from yafs.core import Sim
from yafs.topology import Topology
from yafs.application import Application, Message
from yafs.placement import JSONPlacement
from yafs.path_routing import DeviceSpeedAwareRouting
from yafs.distribution import deterministic_distribution
"""
    * SCÉNARIO INVERSÉ :
        - IPT_cloud >> IPT_edge  (cloud très puissant, edge faible)
        - On fait varier le délai réseau edge-cloud (PR sur le lien 0-3)
        - On cherche à partir de quel délai réseau le edge devient meilleur

    * TOPOLOGIE :
       Node 1 (Source) --PR_src-edge--> Node 0 (EDGE) --PR_edge-cloud--> Node 3 (CLOUD)
                                             |
                                        PR_edge-sink
"""
IPT_EDGE  = 500     # Edge peu puissant
IPT_CLOUD = 10000   # Cloud très puissant

# Délais réseau à faire varier (lien Edge <-> Cloud)
# On part de 0 et on monte progressivement 
PR_values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


# -----------------------------
# TOPOLOGIE
# -----------------------------
def create_topology(PR_edge_cloud):
    """
    - PR_edge_cloud : délai de propagation (PR) sur le lien Edge <-> Cloud
    - Le lien Edge <-> Sink et Source <-> Edge restent fixes (PR=1)
    """
    t = Topology()
    G = nx.Graph()

    G.add_node(0, IPT=IPT_EDGE,  RAM=4000)   # EDGE
    G.add_node(1, IPT=10000,     RAM=2000)   # SOURCE 
    G.add_node(2, IPT=10000,     RAM=2000)   # SINK   
    G.add_node(3, IPT=IPT_CLOUD, RAM=8000)   # CLOUD

    G.add_edge(1, 0, BW=100, PR=1)                   # Source  -> Edge  (fixe)
    G.add_edge(0, 2, BW=100, PR=1)                   # Edge    -> Sink  (fixe)
    G.add_edge(0, 3, BW=100, PR=PR_edge_cloud)        # Edge    -> Cloud (variable)

    t.G = G
    return t


# -----------------------------
# APPLICATION
# -----------------------------
def create_app():
    app = Application(name="App")

    app.set_modules([
        {"Sensor":     {"Type": Application.TYPE_SOURCE}},
        {"Processing": {"RAM": 10, "Type": Application.TYPE_MODULE}},
        {"Actuator":   {"Type": Application.TYPE_SINK}}
    ])

    m1 = Message("M1", "Sensor", "Processing",
                 instructions=2000,
                 bytes=1000000)

    m2 = Message("M2", "Processing", "Actuator",
                 instructions=100,
                 bytes=500000)

    app.add_source_messages(m1)
    app.add_service_module("Processing", m1, m2, lambda: 1.0)
    return app


# -----------------------------
# PLACEMENTS
# -----------------------------
def placement_cloud():
    return JSONPlacement(name="cloud", json={
        "initialAllocation": [
            {"app": "App", "module_name": "Processing", "id_resource": 3}
        ]
    })


def placement_edge():
    return JSONPlacement(name="edge", json={
        "initialAllocation": [
            {"app": "App", "module_name": "Processing", "id_resource": 0}
        ]
    })


# -----------------------------
# CALCUL DÉLAI E2E
# -----------------------------
def compute_delay(file):
    df      = pd.read_csv(file + ".csv")
    df_link = pd.read_csv(file + "_link.csv")

    # Temps de traitement du module Processing (time_out - time_emit)
    df_comp = df[df["type"] == "COMP_M"].copy()
    delay_processing = (df_comp["time_out"] - df_comp["time_emit"]).mean()

    # Latence réseau moyenne (tous les sauts)
    latency_network = df_link["latency"].mean()

    return delay_processing + latency_network


# -----------------------------
# SIMULATION
# -----------------------------
def run(PR_edge_cloud, placement_func, filename):
    t         = create_topology(PR_edge_cloud)
    app       = create_app()
    placement = placement_func()
    routing   = DeviceSpeedAwareRouting()

    s = Sim(t, default_results_path=filename)
    s.deploy_app(app, placement, routing)
    s.deploy_sink("App", node=2, module="Actuator")

    dist = deterministic_distribution(100, name="Det")
    s.deploy_source("App", id_node=1,
                    msg=app.get_message("M1"),
                    distribution=dist)

    s.run(5000)
    return compute_delay(filename)


# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":

    os.makedirs("results2", exist_ok=True)

    cloud_delays = []
    edge_delays  = []

    print("Simulation en cours...\n")
    print(f"IPT_edge  = {IPT_EDGE}  (fixe, peu puissant)")
    print(f"IPT_cloud = {IPT_CLOUD} (fixe, très puissant)")
    print(f"PR varié  = {PR_values}\n")

    for PR in PR_values:
        print(f"PR_edge_cloud = {PR}")

        d_cloud = run(PR, placement_cloud,
                      filename=f"results2/cloud_PR{PR}")

        d_edge  = run(PR, placement_edge,
                      filename=f"results2/edge_PR{PR}")

        cloud_delays.append(d_cloud)
        edge_delays.append(d_edge)

        print(f"  -- Cloud : {d_cloud:.3f}  |  Edge : {d_edge:.3f}")

    # -----------------------------
    # TROUVER L'INTERSECTION
    # -----------------------------
    crossover_PR = None
    for i in range(len(PR_values) - 1):
        if cloud_delays[i] >= edge_delays[i] and cloud_delays[i+1] < edge_delays[i+1]:
            crossover_PR = PR_values[i+1]
            break
        if cloud_delays[i] <= edge_delays[i] and cloud_delays[i+1] > edge_delays[i+1]:
            crossover_PR = PR_values[i+1]
            break

    # -----------------------------
    # GRAPHE FINAL
    # -----------------------------
    plt.figure(figsize=(10, 6))

    plt.plot(PR_values, cloud_delays, marker='o',  color='steelblue',  label=f"Cloud (IPT={IPT_CLOUD})")
    plt.plot(PR_values, edge_delays,  marker='s',  color='darkorange', label=f"Edge  (IPT={IPT_EDGE})")

    if crossover_PR is not None:
        plt.axvline(x=crossover_PR, color='red', linestyle=':', linewidth=1.5,
                    label=f"Intersection ≈ PR={crossover_PR}")
        plt.text(crossover_PR + 2, max(max(cloud_delays), max(edge_delays)) * 0.95,
                 f"Edge devient\nintéressant\nà PR ≥ {crossover_PR}",
                 color='red', fontsize=9)

    plt.xlabel("Délai réseau Edge <-> Cloud (PR)")
    plt.ylabel("Délai de bout en bout moyen")
    plt.title("Edge vs Cloud : évolution du PR")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()

    plt.savefig("results2/evolution_PR.png")
    print("\nGraphique prêt dans : results2/evolution_PR.png")

    if crossover_PR:
        print(f"\n-- Le Edge devient meilleur que le Cloud à partir de PR ~ {crossover_PR}")

    plt.show()