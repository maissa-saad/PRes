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
sensor = {"id":1, "model":"sensor-device", "IPT":100*10**6, "RAM":4000} # un capteur 
actuator = {"id":2, "model":"actuator-device", "IPT":100*10**6, "RAM":4000} # un actionneur
edge = {"id":3, "model":"edge-server", "IPT":500*10**6, "RAM":8000} # un serveur rapide mais faible (un edge) par la suite on pourra on ajouter plus

topology_json = {"entity":[cloud,sensor,actuator, edge], # les noeuds
                 "link":[{"s":1,"d":0,"BW":1,"PR":10}, {"s":0,"d":2,"BW":1,"PR":10}]} # les liens entre noeuds

topology.load(topology_json) # charge tout dans la topologie

# -----------------------------
# Application
# -----------------------------
app = Application(name="EdgeApp")
app.set_modules([
    {"Sensor": {"Type": Application.TYPE_SOURCE}},
    {"ServiceA": {"Type": Application.TYPE_MODULE, "RAM":10}},  # traitement prioritaire Edge
    {"Actuator": {"Type": Application.TYPE_SINK}}
])
m_a = Message("M.A","Sensor","ServiceA", instructions=20*10**6, bytes=1000)
m_b = Message("M.B","ServiceA","Actuator", instructions=10*10**6, bytes=500)
app.add_source_messages(m_a)
app.add_service_module("ServiceA", m_a, m_b)

# -----------------------------
# Placement : prioritaire Edge
# -----------------------------
class EdgePrioritizedPlacement(Placement):
    def initial_allocation(self, sim, app_name):
        # essaie Edge d'abord
        sim.deploy_module(app_name, "ServiceA", 3, app.services["ServiceA"])
        # ici id = 3 donc le noeud edge
        
placement = EdgePrioritizedPlacement("EdgeFirst")
placement.scaleService({"ServiceA": 1})

# -----------------------------
# Population
# -----------------------------
pop = Statical("Statical")
dDistribution = deterministic_distribution("Deterministic", time=100)
pop.set_src_control({"model":"sensor-device","number":1,"message":app.get_message("M.A"),"distribution":dDistribution})
pop.set_sink_control({"model":"actuator-device","number":1,"module":app.get_sink_modules()})
# Simulation
s = Sim(topology)
s.deploy_app2(app, placement, pop)
s.run(1000)