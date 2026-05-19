#!/bin/bash
# =============================================================================
#  PROJET YAFS - Edge / Fog / Cloud
#  Script d'installation et d'exécution de toutes les simulations
# =============================================================================

set -e  # stoppe le script si une commande échoue

echo "=============================================="
echo "  YAFS - Edge/Fog/Cloud Simulation Project"
echo "=============================================="
echo ""

# ------------------------------------------------------------------------------
# 1. Vérification Python
# ------------------------------------------------------------------------------
echo "[1/5] Vérification de Python et Git..."
if ! command -v python3 &> /dev/null; then
    echo "ERREUR : Python 3 n'est pas installé."
    echo "Installez-le via : https://www.python.org/downloads/"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo "  OK : $PYTHON_VERSION détecté"

if ! command -v git &> /dev/null; then
    echo "ERREUR : Git n'est pas installé (requis pour installer YAFS depuis GitHub)."
    echo "Installez-le via : https://git-scm.com/downloads"
    exit 1
fi
echo "  OK : $(git --version) détecté"
echo ""

# ------------------------------------------------------------------------------
# 2. Création de l'environnement virtuel
# ------------------------------------------------------------------------------
echo "[2/5] Création de l'environnement virtuel Python..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  OK : environnement virtuel créé dans ./venv"
else
    echo "  INFO : environnement virtuel déjà existant, on le réutilise"
fi
echo ""

# Activation de l'environnement virtuel
source venv/bin/activate
echo "  OK : environnement virtuel activé"
echo ""

# ------------------------------------------------------------------------------
# 3. Installation des dépendances
# ------------------------------------------------------------------------------
echo "[3/5] Installation des dépendances Python..."
pip install --upgrade pip --quiet

# Dépendances tierces
pip install networkx pandas matplotlib numpy plotly simpy tqdm --quiet

# YAFS - installation depuis GitHub (branche YAFS3, compatible Python 3)
echo "  Installation de YAFS depuis GitHub (branche YAFS3)..."
pip install -e "git+https://github.com/acsicuib/YAFS@YAFS3#egg=yafs" --quiet

echo "  OK : toutes les dépendances sont installées"
echo ""

# ------------------------------------------------------------------------------
# 4. Vérification des fichiers sources
# ------------------------------------------------------------------------------
echo "[4/5] Vérification des fichiers sources..."

REQUIRED_FILES=(
    "cloud_centric.py"
    "edge_prioritized.py"
    "sim_ipt_proche.py"
    "sim_congestion.py"
    "sim_contradiction.py"
    "main_calculs_evolution_ipt.py"
    "main_calculs_evolution_latence.py"
    "test_repartitions.py"
    "test_3D.py"
)

ALL_OK=true
for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "$f" ]; then
        echo "  OK $f"
    else
        echo "  X MANQUANT : $f"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = false ]; then
    echo ""
    echo "ERREUR : certains fichiers sont manquants. Placez-les dans le même dossier que ce script."
    exit 1
fi
echo ""

# ------------------------------------------------------------------------------
# 5. Lancement des simulations
# ------------------------------------------------------------------------------
echo "[5/5] Lancement des simulations..."
echo ""
echo "  NOTE : certaines simulations peuvent prendre plusieurs minutes."
echo "  Les courbes sont sauvegardées automatiquement dans les dossiers results*/"
echo ""

# ── Simulation 0a : Cloud Centric (basique) ──────────────────────────────────
echo "----------------------------------------------------------------------"
echo "  [0a] cloud_centric.py  —  Architecture tout-Cloud (référence)"
echo "----------------------------------------------------------------------"
python3 cloud_centric.py
echo "  DONE"
echo ""

# ── Simulation 0b : Edge Prioritized (basique) ───────────────────────────────
echo "----------------------------------------------------------------------"
echo "  [0b] edge_prioritized.py  —  Architecture Edge-first (référence)"
echo "----------------------------------------------------------------------"
python3 edge_prioritized.py
echo "  DONE"
echo ""

# ── Simulation 1 : Comparaison Edge vs Fog vs Cloud (IPT proches) ────────────
echo "----------------------------------------------------------------------"
echo "  [1] sim_ipt_proche.py  —  Edge vs Fog vs Cloud, IPT variables"
echo "      Courbe sauvegardée : results_ipt/comparaison_niveaux.png"
echo "----------------------------------------------------------------------"
python3 sim_ipt_proche.py
echo "  DONE"
echo ""

# ── Simulation 2 : Congestion et file d'attente ──────────────────────────────
echo "----------------------------------------------------------------------"
echo "  [2] sim_congestion.py  —  Saturation du nœud Edge (congestion)"
echo "      Courbes sauvegardées : results_congestion2/congestion.png"
echo "----------------------------------------------------------------------"
python3 sim_congestion.py
echo "  DONE"
echo ""

# ── Simulation 3 : Contradiction IPT vs Aller-retour ────────────────────────
echo "----------------------------------------------------------------------"
echo "  [3] sim_contradiction.py  —  Trade-off IPT <-> délai aller-retour"
echo "      Courbe sauvegardée : results_contradiction/contradiction_ipt_aller_retour.png"
echo "----------------------------------------------------------------------"
python3 sim_contradiction.py
echo "  DONE"
echo ""

# ── Simulation 4 : Évolution du délai selon l'IPT Cloud ─────────────────────
echo "----------------------------------------------------------------------"
echo "  [4] main_calculs_evolution_ipt.py  —  Seuil de basculement Edge→Cloud"
echo "      Courbe sauvegardée : results/evolution_IPT.png"
echo "----------------------------------------------------------------------"
python3 main_calculs_evolution_ipt.py
echo "  DONE"
echo ""

# ── Simulation 5 : Évolution du délai selon la latence réseau ───────────────
echo "----------------------------------------------------------------------"
echo "  [5] main_calculs_evolution_latence.py  —  Seuil selon la latence réseau"
echo "      Courbe sauvegardée : results2/evolution_PR.png"
echo "----------------------------------------------------------------------"
python3 main_calculs_evolution_latence.py
echo "  DONE"
echo ""

# ── Simulation 6 : Répartition hybride Edge/Cloud ───────────────────────────
echo "----------------------------------------------------------------------"
echo "  [6] test_repartitions.py  —  Répartition optimale de charge Edge/Cloud"
echo "      Courbe sauvegardée : results/final_repartition4.png"
echo "----------------------------------------------------------------------"
python3 test_repartitions.py
echo "  DONE"
echo ""

# ── Simulation 7 : Visualisation 3D interactive ──────────────────────────────
echo "----------------------------------------------------------------------"
echo "  [7] test_3D.py  —  Surface 3D interactive (IPT x Latence x Délai)"
echo "      Fichiers sauvegardés : results3d/surface_3D.html"
echo "                             results3d/basculement_2D.html"
echo "  NOTE : cette simulation est la plus longue (~100 runs)"
echo "----------------------------------------------------------------------"
python3 test_3D.py
echo "  DONE"
echo ""

# ------------------------------------------------------------------------------
# Récapitulatif
# ------------------------------------------------------------------------------
echo "=============================================="
echo "  Toutes les simulations sont terminées !"
echo "=============================================="
echo ""
echo "  Courbes générées :"
echo "    results/evolution_IPT.png"
echo "    results/final_repartition4.png"
echo "    results2/evolution_PR.png"
echo "    results_ipt/comparaison_niveaux.png"
echo "    results_congestion2/congestion.png"
echo "    results_contradiction/contradiction_ipt_aller_retour.png"
echo "    results3d/surface_3D.html        (ouvrir dans un navigateur)"
echo "    results3d/basculement_2D.html    (ouvrir dans un navigateur)"
echo ""