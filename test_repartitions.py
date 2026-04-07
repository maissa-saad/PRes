import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx

from yafs.core import Sim
from yafs.topology import Topology
from yafs.application import Application, Message
from yafs.placement import JSONPlacement
from yafs.distribution import deterministic_distribution
from yafs.selection import Selection

IPT_EDGE = 200
IPT_CLOUD = 1000
PR_EDGE_CLOUD = 20
#WORKFLOW_SIZE = 20000
#WORKFLOW_SIZE = 2000
#WORKFLOW_SIZE = 10000
WORKFLOW_SIZE = 5000


class CustomSelection(Selection):
    def __init__(self, edge_ratio):
        self.edge_ratio = edge_ratio
        super(CustomSelection, self).__init__()

    def get_path(self, sim, app_name, message, topology_src,
                 alloc_DES, alloc_module, state_zone, **kwargs):

        # récupérer les DES du module cible
        module_name = message.dst
        des_list = alloc_module[app_name][module_name]

        # transformer en noeuds topo
        candidates = [(des, alloc_DES[des]) for des in des_list]

        if message.name == "M1":
            edge_nodes = [c for c in candidates if c[1] == 0]
            cloud_nodes = [c for c in candidates if c[1] == 3]

            if np.random.rand() < self.edge_ratio and edge_nodes:
                target_des, target_node = edge_nodes[0]
            elif cloud_nodes:
                target_des, target_node = cloud_nodes[0]
            else:
                target_des, target_node = candidates[0]
        else:
            target_des, target_node = candidates[0]

        path = nx.shortest_path(sim.topology.G,
                                source=topology_src,
                                target=target_node)

        return [path], [target_des]


def run_split_simulation(edge_ratio, filename):
    t = Topology()
    g = nx.Graph()

    g.add_node(0, IPT=IPT_EDGE, RAM=4000)
    g.add_node(1, IPT=10000, RAM=2000)
    g.add_node(2, IPT=10000, RAM=2000)
    g.add_node(3, IPT=IPT_CLOUD, RAM=8000)

    g.add_edge(1, 0, BW=10, PR=2)
    g.add_edge(0, 2, BW=10, PR=2)
    g.add_edge(0, 3, BW=5, PR=PR_EDGE_CLOUD)

    t.G = g

    app = Application(name="App")

    app.set_modules([
        {"Sensor": {"Type": Application.TYPE_SOURCE}},
        {"Proc_Module": {"RAM": 10, "Type": Application.TYPE_MODULE}},
        {"Actuator": {"Type": Application.TYPE_SINK}}
    ])

    m1 = Message("M1", "Sensor", "Proc_Module",
                 instructions=WORKFLOW_SIZE,
                 bytes=1000000)

    m2 = Message("M2", "Proc_Module", "Actuator",
                 instructions=100,
                 bytes=500000)

    app.add_source_messages(m1)
    app.add_service_module("Proc_Module", m1, m2, lambda: 1.0)

    placement = JSONPlacement(name="Hybrid", json={
        "initialAllocation": [
            {"app": "App", "module_name": "Proc_Module", "id_resource": 0},
            {"app": "App", "module_name": "Proc_Module", "id_resource": 3}
        ]
    })

    s = Sim(t, default_results_path=filename)
    s.deploy_app(app, placement, CustomSelection(edge_ratio))
    s.deploy_sink("App", node=2, module="Actuator")

    dist = deterministic_distribution(100, name="Det")
    s.deploy_source("App", id_node=1,
                    msg=app.get_message("M1"),
                    distribution=dist)

    s.run(10000)

    df = pd.read_csv(filename + ".csv")
    df_comp = df[df["type"] == "COMP_M"]

    if df_comp.empty:
        return None

    return (df_comp["time_out"] - df_comp["time_emit"]).mean()


if __name__ == "__main__":
    os.makedirs("results", exist_ok=True)

    ratios = np.linspace(0, 1, 11)
    results = []
    valid_ratios = []

    print("Démarrage de l'étude de répartition...")

    for r in ratios:
        print(f"{int(r*100)}% Edge")

        res = run_split_simulation(r, f"results/split_{int(r*100)}")

        if res is not None:
            results.append(res)
            valid_ratios.append(r * 100)
            print(f" -> {res:.2f}")

    if results:
        plt.figure(figsize=(10, 6))
        plt.plot(valid_ratios, results, marker='o')
        plt.xlabel("% Edge")
        plt.ylabel("Délai moyen")
        plt.title("Répartition Edge/Cloud")
        plt.grid(True)
#        plt.savefig("results/final_repartition1.png")
#        plt.savefig("results/final_repartition2.png")
#        plt.savefig("results/final_repartition3.png")
        plt.savefig("results/final_repartition4.png")
        plt.show()