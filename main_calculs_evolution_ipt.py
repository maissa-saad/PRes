import os
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

from yafs.metrics import Metrics
from yafs.core import Sim
from yafs.topology import Topology
from yafs.application import Application, Message
from yafs.placement import JSONPlacement
from yafs.path_routing import DeviceSpeedAwareRouting
from yafs.distribution import deterministic_distribution
from yafs.stats import Stats

# -----------------------------
# TOPOLOGIE
# -----------------------------
def create_topology(IPT_edge, IPT_cloud):
    t = Topology()
    G = nx.Graph()

    G.add_node(0, IPT=IPT_edge, RAM=4000)
    G.add_node(1, IPT=10000, RAM=2000)   #  SOURCE 
    G.add_node(2, IPT=10000, RAM=2000)   #  SINK 
    G.add_node(3, IPT=IPT_cloud, RAM=8000)

    G.add_edge(1, 0, BW=5, PR=2)
    G.add_edge(0, 2, BW=5, PR=2)
    G.add_edge(0, 3, BW=5, PR=3)

    t.G = G
    return t



# -----------------------------
# APPLICATION (gros message)
# -----------------------------
def create_app():
    app = Application(name="App")

    app.set_modules([
        {"Sensor":     {"Type": Application.TYPE_SOURCE}},
        {"Processing": {"RAM": 10, "Type": Application.TYPE_MODULE}},
        {"Actuator":   {"Type": Application.TYPE_SINK}}  # TYPE_SINK
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
# CALCUL DELAI
# -----------------------------
def compute_delay(file):
    df = pd.read_csv(file + ".csv")
    df_link = pd.read_csv(file + "_link.csv")

    df_comp = df[df["type"] == "COMP_M"].copy()
    delay_processing = (df_comp["time_out"] - df_comp["time_emit"]).mean()
    latency_last_hop = df_link["latency"].mean()

    return delay_processing + latency_last_hop

# -----------------------------
# SIMULATION
# -----------------------------
def run(IPT_edge, IPT_cloud, placement_func, filename):
    t = create_topology(IPT_edge, IPT_cloud)
    app = create_app()
    placement = placement_func()
    routing = DeviceSpeedAwareRouting()

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

    os.makedirs("results", exist_ok=True)

    IPT_edge = 200  # FIXE
    IPT_cloud_values = [200, 225, 250, 275, 300, 325, 350, 375, 400, 425, 450, 475, 500]

    cloud_delays = []
    edge_delays = []

    print("Simulation en cours...\n")

    # EDGE (UNE SEULE FOIS car constant)
    d_edge = run(IPT_edge, IPT_cloud=1000,
                 placement_func=placement_edge,
                 filename="results/edge")

    for IPT_cloud in IPT_cloud_values:
        print(f"IPT_cloud = {IPT_cloud}")

        d_cloud = run(IPT_edge, IPT_cloud,
                      placement_func=placement_cloud,
                      filename=f"results/cloud_{IPT_cloud}")

        cloud_delays.append(d_cloud)
        edge_delays.append(d_edge)  # constante

    # -----------------------------
    # GRAPHE FINAL
    # -----------------------------
    plt.figure(figsize=(10, 6))

    plt.plot(IPT_cloud_values, cloud_delays, marker='o', label="Cloud")
    plt.plot(IPT_cloud_values, edge_delays, linestyle='--', label="Edge (constant)")

    # -----------------------------
    # TROUVER L'INTERSECTION
    # -----------------------------
    crossover_IPT = None
    for i in range(len(IPT_cloud_values) - 1):
        e1, e2 = edge_delays[i], edge_delays[i+1]
        c1, c2 = cloud_delays[i], cloud_delays[i+1]

        if (e1 - c1) * (e2 - c2) < 0:  # il y a un croisement entre i et i+1
            crossover_IPT = IPT_cloud_values[i] + (IPT_cloud_values[i+1] - IPT_cloud_values[i]) * abs(e1 - c1) / (abs((e1 - c1) - (e2 - c2)))
            break

    if crossover_IPT is not None:
        plt.axvline(x=crossover_IPT, color='red', linestyle=':', linewidth=1.5,
                    label=f"Intersection ≈ IPT={crossover_IPT:.1f}")
        plt.text(crossover_IPT + 5,
                max(max(cloud_delays), max(edge_delays)) * 0.95,
                f"Cloud devient\nintéressant\nà IPT ≈ {crossover_IPT:.1f}",
                color='red', fontsize=10)

    plt.xlabel("IPT Cloud")
    plt.ylabel("Délai de bout en bout")
    plt.title("Edge vs Cloud : évolution de IPT")
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()

    plt.savefig("results/evolution_IPT.png")
    print("\nGraphique prêt dans : results/evolution_IPT.png")

    if crossover_IPT:
        print(f"\n-- Le Cloud devient meilleur que le Edge à partir de IPT ~ {crossover_IPT}")

    plt.show()