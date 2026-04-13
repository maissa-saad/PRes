from yafs.selection import Selection
import networkx as nx
import numpy as np

class MinimumLatenceNBd(Selection):

    def get_path(self, sim, app_name, message, topology_src, alloc_DES, alloc_module, traffic,from_des):
        if (message.name=="M.A"):       
            alpha = 0.2 #consommation énergétique

            node_src = topology_src
            DES_dst = alloc_module[app_name][message.dst] 

            bestScore = float("inf")
            bestPath = []
            bestDES = []
                    
            #initialisation des poids du graphe
            for _, _, data in sim.topology.G.edges(data=True):
                data['poids'] = (message.bytes/data["BW"])+data["PR"]
                #print(data['poids'])
                
            dist, paths = nx.single_source_dijkstra(sim.topology.G, source=node_src, weight='poids')
            for des in DES_dst: 
                dst_node = alloc_DES[des]
                path = paths[dst_node]

                latence_somme = sum([sim.topology.G.edges[(path[i], path[i+1])]["PR"] for i in range(len(path)-1)])
                bande_passante_min = min([sim.topology.G.edges[(path[i], path[i+1])]["BW"] for i in range(len(path)-1)]) 
                energie=sim.topology.G.nodes[dst_node]["WATT"]
                ipt=sim.topology.G.nodes[dst_node]["IPT"]
                #nombre_liens = len(path) - 1

                score = latence_somme + message.bytes/bande_passante_min + message.inst/ipt + alpha*energie

                print("score:",score)
                if score < bestScore:
                    bestScore = score
                    bestPath = [path]   
                    bestDES = [des]

            return bestPath, bestDES
        
        else:
            node_src = topology_src
            DES_dst = alloc_module[app_name][message.dst] 

            bestScore = float("inf")
            bestPath = []
            bestDES = []
                    
            #initialisation des poids du graphe
            for _, _, data in sim.topology.G.edges(data=True):
                data['poids'] = (message.bytes/data["BW"])+data["PR"]
                #print(data['poids'])
                
            dist, paths = nx.single_source_dijkstra(sim.topology.G, source=node_src, weight='poids')

            for des in DES_dst: 
                dst_node = alloc_DES[des]
                path = paths[dst_node]
                latence_somme = sum([sim.topology.G.edges[(path[i], path[i+1])]["PR"] for i in range(len(path)-1)])
                bande_passante_min = min([sim.topology.G.edges[(path[i], path[i+1])]["BW"] for i in range(len(path)-1)]) 
                #nombre_liens = len(path) - 1

                score = latence_somme + message.bytes/bande_passante_min

                #print("score:",score)
                if score < bestScore:
                    bestScore = score
                    bestPath = [path]   
                    bestDES = [des]

            return bestPath, bestDES


class MinimumLatenceNBd_v2(Selection):

    def get_path(self, sim, app_name, message, topology_src, alloc_DES, alloc_module, traffic,from_des):
        if (message.name=="M.A"):       
            alpha=1 #latence
            beta=1 #bande passante
            gamma=1 # instruction par seconde (IPT)
            delta = 1 #consommation énergétique
            epsilon = 1
            zeta = 1

            node_src = topology_src
            DES_dst = alloc_module[app_name][message.dst] 

            bestScore = float("inf")
            bestPath = []
            bestDES = []

            ipt_max = max([sim.topology.G.nodes[alloc_DES[des]]["IPT"] for des in DES_dst])
            energie_max = max([sim.topology.G.nodes[alloc_DES[des]]["WATT"] for des in DES_dst])
            bd_min_global = float("inf")
            latence_max = -1
            taille_message_max=2000

            for _, _, data in sim.topology.G.edges(data=True):
                if data["BW"]<bd_min_global:
                    bd_min_global=data["BW"]
                if data["PR"]>latence_max:
                    latence_max=data["PR"]
                    
            #initialisation des poids du graphe
            #for _, _, data in sim.topology.G.edges(data=True):
            #    data['poids'] = alpha * (data["PR"]/latence_max) + beta * (1-(data["BW"]/bd_max))
                #print(data['poids'])
                
                

            for des in DES_dst: 

                dst_node = alloc_DES[des]
                path = list(nx.dijkstra_path(sim.topology.G, source=node_src, target=dst_node, weight='PR'))

                latence_moyenne = np.mean([sim.topology.G.edges[(path[i], path[i+1])]["PR"] for i in range(len(path)-1)])
                bande_passante_min = min([sim.topology.G.edges[(path[i], path[i+1])]["BW"] for i in range(len(path)-1)]) 
                energie=sim.topology.G.nodes[dst_node]["WATT"]
                ipt=sim.topology.G.nodes[dst_node]["IPT"]
                #nombre_liens = len(path) - 1

                score = (latence_moyenne/latence_max)*alpha + ((message.bytes/bande_passante_min)/(taille_message_max/bd_min_global))*beta
                + (ipt/ipt_max)*gamma + (1-(energie/energie_max))*delta

                print("score:",score)
                #print("\n")
                if score < bestScore:
                    bestScore = score
                    bestPath = [path]   
                    bestDES = [des]

            return bestPath, bestDES
        else:
            alpha=1 #latence
            beta=1 #bande passante
            gamma=1 # instruction par seconde (IPT)
            delta = 1 #consommation énergétique
            epsilon = 1
            zeta = 1

            node_src = topology_src
            DES_dst = alloc_module[app_name][message.dst] 

            bestScore = float("inf")
            bestPath = []
            bestDES = []

            bd_min_global = float("inf")
            latence_max = -1
            taille_message_max=2000

            for _, _, data in sim.topology.G.edges(data=True):
                if data["BW"]<bd_min_global:
                    bd_min_global=data["BW"]
                if data["PR"]>latence_max:
                    latence_max=data["PR"]
                    


            for des in DES_dst: 

                dst_node = alloc_DES[des]
                path = list(nx.dijkstra_path(sim.topology.G, source=node_src, target=dst_node, weight='PR'))

                latence_moyenne = np.mean([sim.topology.G.edges[(path[i], path[i+1])]["PR"] for i in range(len(path)-1)])
                bande_passante_min = min([sim.topology.G.edges[(path[i], path[i+1])]["BW"] for i in range(len(path)-1)]) 
                #nombre_liens = len(path) - 1

                score = (latence_moyenne/latence_max)*alpha + ((message.bytes/bande_passante_min)/(taille_message_max/bd_min_global))*beta

                #print(score)
                #print("\n")
                if score < bestScore:
                    bestScore = score
                    bestPath = [path]   
                    bestDES = [des]

            return bestPath, bestDES
