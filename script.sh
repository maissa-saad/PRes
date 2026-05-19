#!/bin/bash
# =============================================================================
#  PROJET YAFS - Algorithme de sélection MinimumLatenceNBd
#  Edge / Fog / Cloud avec placement hybride et routage intelligent
#
#  IMPORTANT : Ce script suppose que script.sh (dossier PROJET_13_tests/)
#  a déjà été exécuté. YAFS et toutes les dépendances sont donc déjà installés.
#  L'environnement virtuel commun est réutilisé directement.
# =============================================================================

set -e  # stoppe le script si une commande échoue

echo "=============================================="
echo "  YAFS - Algorithme de Sélection Intelligent"
echo "  Edge / Fog / Cloud"
echo "=============================================="
echo ""

# ------------------------------------------------------------------------------
# 1. Activation de l'environnement virtuel commun
# ------------------------------------------------------------------------------
echo "[1/3] Activation de l'environnement virtuel..."

# On cherche le venv dans le dossier courant ou dans le dossier parent (simulations/)
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "  OK : environnement virtuel local activé"
elif [ -d "../simulations/venv" ]; then
    source ../simulations/venv/bin/activate
    echo "  OK : environnement virtuel de simulations/ activé"
else
    echo "  ERREUR : aucun environnement virtuel trouvé."
    echo "  Veuillez d'abord exécuter setup_and_run.sh dans le dossier simulations/"
    exit 1
fi
echo ""

# ------------------------------------------------------------------------------
# 2. Vérification des fichiers sources
# ------------------------------------------------------------------------------
echo "[2/3] Vérification des fichiers sources..."

REQUIRED_FILES=(
    "main.py"
    "simpleSelection.py"
    "topo.json"
)

ALL_OK=true
for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "$f" ]; then
        echo "  ✓ $f"
    else
        echo "  ✗ MANQUANT : $f"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = false ]; then
    echo ""
    echo "ERREUR : certains fichiers sont manquants. Placez-les dans le même dossier que ce script."
    exit 1
fi

# topotest.json est optionnel
if [ -f "topotest.json" ]; then
    echo "  ✓ topotest.json (optionnel)"
else
    echo "  - topotest.json absent (non bloquant)"
fi
echo ""

# ------------------------------------------------------------------------------
# 3. Lancement de la simulation
# ------------------------------------------------------------------------------
echo "[3/3] Lancement de la simulation principale..."
echo ""
echo "----------------------------------------------------------------------"
echo "  main.py  —  Simulation avec algorithme de sélection MinimumLatenceNBd"
echo "----------------------------------------------------------------------"
echo "  Topologie : 17 noeuds (1 sensor + 1 actuator + 5 edge + 5 fog + 5 cloud)"
echo "  Placement : module ServiceA deploye sur tous les noeuds edge, fog et cloud"
echo "  Routage   : score = latence reseau + delai calcul + alpha x consommation energie"
echo "  Resultats : sim_trace_algo.csv  et  sim_trace_algo_link.csv"
echo "----------------------------------------------------------------------"
echo ""

python3 main.py

echo ""
echo "  DONE - simulation terminee"
echo ""

# ------------------------------------------------------------------------------
# Analyse et courbes des résultats
# ------------------------------------------------------------------------------
echo "----------------------------------------------------------------------"
echo "  Generation des courbes d'analyse..."
echo "----------------------------------------------------------------------"
echo ""

python3 - <<'PYEOF'
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

os.makedirs("results_algo", exist_ok=True)

# Chargement des données
try:
    df      = pd.read_csv("sim_trace_algo.csv")
    df_link = pd.read_csv("sim_trace_algo_link.csv")
except FileNotFoundError as e:
    print(f"  ERREUR : fichier introuvable : {e}")
    exit(1)

df_comp = df[df["type"] == "COMP_M"].copy()
df_comp["e2e_delay"] = df_comp["time_out"] - df_comp["time_emit"]

# Mapping noeud -> niveau
NODE_LEVEL = {}
for n in range(2, 7):  NODE_LEVEL[n] = "Edge"
for n in range(7, 12): NODE_LEVEL[n] = "Fog"
for n in range(12, 17):NODE_LEVEL[n] = "Cloud"

df_comp["level"] = df_comp["TOPO.dst"].map(NODE_LEVEL)
COLORS = {"Edge": "steelblue", "Fog": "orange", "Cloud": "tomato"}

# Courbe 1 : délai e2e au fil du temps, coloré par niveau
fig, ax = plt.subplots(figsize=(13, 5))
for level, color in COLORS.items():
    sub = df_comp[df_comp["level"] == level]
    ax.scatter(sub["time_emit"], sub["e2e_delay"],
               label=level, color=color, s=12, alpha=0.7)
ax.set_xlabel("Temps de simulation")
ax.set_ylabel("Delai bout-en-bout (ms)")
ax.set_title("Delai e2e au fil du temps — par niveau de traitement\n"
             "(algorithme MinimumLatenceNBd : score = latence + calcul + alpha x energie)")
ax.legend()
ax.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig("results_algo/01_e2e_par_temps.png", dpi=150)
plt.close()
print("  OK results_algo/01_e2e_par_temps.png")

# Courbe 2 : répartition des messages par noeud
node_counts = df_comp["TOPO.dst"].value_counts().sort_index()
node_labels = [f"N{n}\n({NODE_LEVEL.get(n,'?')})" for n in node_counts.index]
node_colors = [COLORS.get(NODE_LEVEL.get(n, "?"), "grey") for n in node_counts.index]

fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(node_labels, node_counts.values, color=node_colors, edgecolor="white")
ax.set_xlabel("Noeud de traitement")
ax.set_ylabel("Nombre de messages traites")
ax.set_title("Repartition des messages par noeud\n"
             "(l'algorithme equilibre la charge selon score energie/latence/calcul)")
patches = [mpatches.Patch(color=c, label=l) for l, c in COLORS.items()]
ax.legend(handles=patches)
ax.grid(True, linestyle="--", alpha=0.4, axis="y")
plt.tight_layout()
plt.savefig("results_algo/02_repartition_noeuds.png", dpi=150)
plt.close()
print("  OK results_algo/02_repartition_noeuds.png")

# Courbe 3 : délai moyen par niveau
means = df_comp.groupby("level")["e2e_delay"].mean().reindex(["Edge","Fog","Cloud"])
stds  = df_comp.groupby("level")["e2e_delay"].std().reindex(["Edge","Fog","Cloud"])

fig, ax = plt.subplots(figsize=(7, 5))
ax.bar(means.index, means.values,
       yerr=stds.values, capsize=6,
       color=[COLORS[l] for l in means.index],
       edgecolor="white")
ax.set_ylabel("Delai moyen bout-en-bout (ms)")
ax.set_title("Delai moyen par niveau (Edge / Fog / Cloud)\navec ecart-type")
ax.grid(True, linestyle="--", alpha=0.4, axis="y")
plt.tight_layout()
plt.savefig("results_algo/03_delai_moyen_niveau.png", dpi=150)
plt.close()
print("  OK results_algo/03_delai_moyen_niveau.png")

# Courbe 4 : heatmap latence réseau par lien
link_mean = df_link.groupby(["src","dst"])["latency"].mean().reset_index()
pivot = link_mean.pivot(index="src", columns="dst", values="latency")

fig, ax = plt.subplots(figsize=(10, 7))
im = ax.imshow(pivot.values, cmap="YlOrRd", aspect="auto")
ax.set_xticks(range(len(pivot.columns)))
ax.set_yticks(range(len(pivot.index)))
ax.set_xticklabels([f"N{c}" for c in pivot.columns], fontsize=8)
ax.set_yticklabels([f"N{r}" for r in pivot.index], fontsize=8)
plt.colorbar(im, ax=ax, label="Latence moyenne (ms)")
ax.set_title("Latence reseau moyenne par lien (src -> dst)")
plt.tight_layout()
plt.savefig("results_algo/04_latence_liens.png", dpi=150)
plt.close()
print("  OK results_algo/04_latence_liens.png")

# Courbe 5 : charge cumulée par noeud
fig, ax = plt.subplots(figsize=(13, 5))
for node_id in sorted(df_comp["TOPO.dst"].unique()):
    sub = df_comp[df_comp["TOPO.dst"] == node_id].copy().sort_values("time_emit")
    sub["cumul"] = range(1, len(sub)+1)
    level = NODE_LEVEL.get(node_id, "?")
    ax.plot(sub["time_emit"], sub["cumul"],
            label=f"N{node_id} ({level})",
            color=COLORS.get(level, "grey"),
            linewidth=1.2, alpha=0.8)
ax.set_xlabel("Temps de simulation")
ax.set_ylabel("Nombre cumule de messages traites")
ax.set_title("Evolution de la charge cumulee par noeud\n"
             "(equilibrage dynamique par l'algorithme de selection)")
ax.legend(fontsize=7, ncol=3, loc="upper left")
ax.grid(True, linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig("results_algo/05_charge_cumulee.png", dpi=150)
plt.close()
print("  OK results_algo/05_charge_cumulee.png")

# Récapitulatif texte
print("")
print("  === Statistiques globales ===")
print(f"  Messages traites (COMP_M) : {len(df_comp)}")
print(f"  Delai e2e moyen global    : {df_comp['e2e_delay'].mean():.3f} ms")
print(f"  Delai e2e min             : {df_comp['e2e_delay'].min():.3f} ms")
print(f"  Delai e2e max             : {df_comp['e2e_delay'].max():.3f} ms")
print("")
for level in ["Edge","Fog","Cloud"]:
    sub = df_comp[df_comp["level"]==level]
    if not sub.empty:
        pct = len(sub)/len(df_comp)*100
        print(f"  {level:5s} : {len(sub):4d} messages ({pct:.1f}%)  |  delai moy = {sub['e2e_delay'].mean():.3f} ms")
PYEOF

echo ""
echo "=============================================="
echo "  Simulation et analyse terminees !"
echo "=============================================="
echo ""
echo "  Fichiers de trace :"
echo "    sim_trace_algo.csv         (evenements de calcul)"
echo "    sim_trace_algo_link.csv    (evenements reseau)"
echo ""
echo "  Courbes generees dans results_algo/ :"
echo "    01_e2e_par_temps.png       delai bout-en-bout au fil du temps"
echo "    02_repartition_noeuds.png  nombre de messages traites par noeud"
echo "    03_delai_moyen_niveau.png  delai moyen Edge / Fog / Cloud"
echo "    04_latence_liens.png       heatmap des latences reseau"
echo "    05_charge_cumulee.png      evolution de la charge par noeud"
echo ""