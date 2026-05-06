import os
import time
import json
import random
import logging.config

import networkx as nx
from pathlib import Path
import matplotlib.pyplot as plt

import pandas as pd
import numpy as np

import random

from yafs.core import Sim
from yafs.application import create_applications_from_json
from yafs.topology import Topology

from yafs.placement import JSONPlacement
from yafs.path_routing import DeviceSpeedAwareRouting

from yafs.application import Application
from yafs.application import Message

from yafs.population import Statical

from yafs.placement import Placement
from yafs.path_routing import DeviceSpeedAwareRouting
from yafs.distribution import deterministic_distribution
from yafs.distribution import exponential_distribution
from yafs.application import fractional_selectivity
from simpleSelection import MinimumLatenceNBd
from yafs.population import Population

class EdgeCloudPlacement(Placement):
    def initial_allocation(self, sim, app_name):
        app = sim.apps[app_name]
        services = app.services
        cloud_nodes = sim.topology.find_IDs({"mytag": "cloud"})
        edge_nodes = sim.topology.find_IDs({"mytag": "edge"})
        fog_nodes = sim.topology.find_IDs({"mytag": "fog"})


        for module in services:
            if module in self.scaleServices:
                for node in cloud_nodes:
                    sim.deploy_module(app_name, module, services[module], [node])
                for node in edge_nodes:
                    sim.deploy_module(app_name, module, services[module], [node])
                for node in fog_nodes:
                    sim.deploy_module(app_name, module, services[module], [node])


with open("topo.json") as f:
    topology_json = json.load(f)

    
# Création de la topologie
t = Topology()
t.load_all_node_attr(topology_json)
    
node_load = {}
for n in t.G.nodes():
    node_load[n] = 0
    
def create_application():
    # APLICATION
    a = Application(name="SimpleCase")

    # (S) --> (ServiceA) --> (A)
    a.set_modules([{"Sensor":{"Type":Application.TYPE_SOURCE}},
                   {"ServiceA": {"RAM": 10, "Type": Application.TYPE_MODULE}},
                   {"Actuator": {"Type": Application.TYPE_SINK}}
                   ])
    
    m_a = Message("M.A", "Sensor", "ServiceA", instructions=600000000, bytes=1000)
    m_b = Message("M.B", "ServiceA", "Actuator", instructions=10000000, bytes=500)

    a.add_source_messages(m_a)
    
    # MODULE SERVICES
    a.add_service_module(
        "ServiceA",
        m_a,
        m_b,
        fractional_selectivity,  
        threshold=1.0
    )
    return a

#création de l'application
app = create_application()

pop = Statical("Statical")

# Source
seed = random.randint(0, 10**9)
dDistribution = exponential_distribution(name="poisson",lambd=1,seed=seed)
pop.set_src_control({
    "model": "sensor-device",
    "number": 1,
    "message": app.get_message("M.A"),
    "distribution": dDistribution
})

# Sink
pop.set_sink_control({
    "model": "actuator-device",
    "number": 1,
    "module": app.get_sink_modules()
})  


#Placement
placement = EdgeCloudPlacement("edgecloud")
placement.scaleService({"ServiceA": 1})


selectorPath = MinimumLatenceNBd(node_load)
s = Sim(t,default_results_path="sim_trace_algo")
simulation_time = 1000
s.deploy_app2(app, placement, pop, selectorPath)

s.run(simulation_time,show_progress_monitor=False)
s.print_debug_assignaments()
