from yafs.core import Sim
from yafs.topology import Topology
from yafs.application import Application, Message
from yafs.placement import Placement
from yafs.population import Statical
from yafs.distribution import deterministic_distribution

# -----------------------------
# Topologie
# -----------------------------
topology = Topology()
cloud = {"id":0, "model":"cloud", "IPT":5000*10**6, "RAM":40000} # un serveur distant, puissant mais long (le cloud)
sensor = {"id":1, "model":"sensor-device", "IPT":100*10**6, "RAM":4000} # un objet IoT (un capteur pr exemple)
actuator = {"id":2, "model":"actuator-device", "IPT":100*10**6, "RAM":4000} # un actionneur (un appareil qui agit)

topology_json = {"entity":[cloud,sensor,actuator], # les noeuds
                 "link":[{"s":1,"d":0,"BW":1,"PR":10}, {"s":0,"d":2,"BW":1,"PR":10}]} # les liens entre noeuds
topology.load(topology_json) # charge tout dans la topologie

# -----------------------------
# Application
# -----------------------------
app = Application(name="CloudApp")
app.set_modules([
    {"Sensor": {"Type": Application.TYPE_SOURCE}},
    {"ServiceA": {"Type": Application.TYPE_MODULE, "RAM":10}},  # traitement dans le Cloud
    # ServiceA : nom du module
    # Type ici : module de traitement
    # RAM      : la quantite de RAM requise pour exécuter ce module
    #----
    # ServiceA est un module de calcul, il consomme 10 unités de RAM, il peut être placé sur un noeud qui a suffisamment de RAM
    #----
    
    {"Actuator": {"Type": Application.TYPE_SINK}}
])

m_a = Message("M.A","Sensor","ServiceA", instructions=20*10**6, bytes=1000)
m_b = Message("M.B","ServiceA","Actuator", instructions=10*10**6, bytes=500)
app.add_source_messages(m_a)
app.add_service_module("ServiceA", m_a, m_b) # ServiceA est le module qui va traiter le message, m_a est le message entrant, et m_b est le message sortant (le résultat)

# -----------------------------
# Placement : tout sur le Cloud
# -----------------------------
class CloudPlacement(Placement):
    def initial_allocation(self, sim, app_name):
        sim.deploy_module(app_name, "ServiceA", 0, app.services["ServiceA"])
        # ici serviceA est le module à déployer, 0 est l'id du noeud (dans ma structure c'est cloud)
        # donc c'est qu'on décide de déployer un module donné sur le cloud (c'est ce qu'on va changer pour le edge et pour le hybride)

placement = CloudPlacement("onCloud")
placement.scaleService({"ServiceA": 1})

# -----------------------------
# Population
# -----------------------------
pop = Statical("Statical") # pour l'instant chaque utilisateur est fixé sur un noeud donné dès le départ (on va le changer ensuite car les utilisateurs sont tout le temps en train de bouger)
dDistribution = deterministic_distribution("Deterministic", time=100)

pop.set_src_control({"model":"sensor-device","number":1,"message":app.get_message("M.A"),"distribution":dDistribution})
pop.set_sink_control({"model":"actuator-device","number":1,"module":app.get_sink_modules()})

# -----------------------------
# Simulation
# -----------------------------
s = Sim(topology)
s.deploy_app2(app, placement, pop)
# une methode de la classe Sim dans YAFS,
# utilisee pour deployer une application complete

s.run(1000)
# lance la simulation pendant 1000 unites de temps