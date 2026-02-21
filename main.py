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

from yafs.core import Sim
from yafs.application import create_applications_from_json
from yafs.topology import Topology

from yafs.placement import JSONPlacement
from yafs.path_routing import DeviceSpeedAwareRouting
from yafs.distribution import deterministic_distribution

with open("topo.json") as f:
    topology_json = json.load(f)

# Création de la topologie
t = Topology()
t.load(topology_json)

print("Nodes:", t.G.nodes(data=True))
print("Edges:", t.G.edges(data=True))