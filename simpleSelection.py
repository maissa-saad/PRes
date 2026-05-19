from yafs.selection import Selection
import networkx as nx
import numpy as np
import time

class MinimumLatenceNBd(Selection):


    def __init__(self, node_load):
        super().__init__()
        self.node_load = node_load


    def get_path(self, sim, app_name, message, topology_src, alloc_DES, alloc_module, traffic,from_des):
        if (message.name=="M.A"): 
            alpha = 5#consommation énergétique

            node_src = topology_src
            DES_dst = alloc_module[app_name][message.dst] 

            bestScore = float("inf")
            bestPath = []
            bestDES = []
                    
            #initialisation des poids du graphe
            for _, _, data in sim.topology.G.edges(data=True):
                data['poids'] = (message.bytes/data["BW"])+data["PR"]                
            dist, paths = nx.single_source_dijkstra(sim.topology.G, source=node_src, weight='poids')
            for des in DES_dst: 
                dst_node = alloc_DES[des]
                path = paths[dst_node]

                latence_somme = sum([sim.topology.G.edges[(path[i], path[i+1])]["poids"] for i in range(len(path)-1)])
                energie=sim.topology.G.nodes[dst_node]["WATT"]

                ipt=sim.topology.G.nodes[dst_node]["IPT"]
                ipt_utilise=self.node_load[dst_node]
                ipt_effectif = max(ipt - ipt_utilise, 800000)
                score = latence_somme + message.inst/(ipt_effectif) + alpha*energie

                if score < bestScore:
                    bestScore = score
                    bestPath = [path]   
                    bestDES = [des]            
            print("best:",bestPath[-1][-1],"  ",bestScore)
            self.node_load[bestPath[-1][-1]]+=800000000
            return bestPath, bestDES
        
        else:
            node_src = topology_src
            self.node_load[node_src]-=800000000
            DES_dst = alloc_module[app_name][message.dst] 

            bestScore = float("inf")
            bestPath = []
            bestDES = []
                    
            #initialisation des poids du graphe
            for _, _, data in sim.topology.G.edges(data=True):
                data['poids'] = (message.bytes/data["BW"])+data["PR"]
                
            dist, paths = nx.single_source_dijkstra(sim.topology.G, source=node_src, weight='poids')

            for des in DES_dst: 
                dst_node = alloc_DES[des]
                path = paths[dst_node]
                latence_somme = sum([sim.topology.G.edges[(path[i], path[i+1])]["poids"] for i in range(len(path)-1)])

                score = latence_somme

                if score < bestScore:
                    bestScore = score
                    bestPath = [path]   
                    bestDES = [des]

            return bestPath, bestDES