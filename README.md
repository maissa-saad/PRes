# Placement et orchestration de services dans le Edge–Fog–Cloud avec le simulateur YAFS


## Prérequis

- Python **3.9 ou supérieur** (pour utiliser YAFS)
- pip
- **Git** (pour installer YAFS depuis GitHub)
- Un terminal Bash (Linux / macOS / WSL sur Windows)

---

## Installation de YAFS

```bash
pip install -e "git+https://github.com/acsicuib/YAFS@YAFS3#egg=yafs"
```

Cette commande clone le dépôt officiel et installe YAFS en mode éditable depuis la branche `YAFS3`, la seule compatible avec Python 3.9+. Elle est **exécutée automatiquement** par le script `script.sh`

> Git doit être installé
> Vérification : `git --version`. Si vous ne l'avez pas, installer sur : [https://git-scm.com/downloads](https://git-scm.com/downloads)

---

## Installation et lancement (tout-en-un)

```bash
# 1. Cloner / déposer tous les fichiers dans un même dossier
# 2. Rendre le script exécutable
chmod +x script.sh

# 3. Lancer toutes les simulations
./script.sh
```

Le script :
1. vérifie que Python 3 est présent
2. crée un environnement virtuel `venv/`
3. installe automatiquement YAFS et toutes les dépendances (`networkx`, `pandas`, `matplotlib`, `numpy`, `plotly`)
4. exécute les 8 simulations dans l'ordre
5. affiche un récapitulatif de toutes les courbes générées

---

## Lancer une simulation individuelle

Si vous avez déjà installé les dépendances, vous pouvez lancer chaque script séparément :

```bash
source venv/bin/activate # pour activer l'environnement virtuel
python3 <nom_du_fichier>.py
```

---

## Description des fichiers

### Fichiers de référence (architecture de base)

| Fichier | Description | Courbe générée |
|---|---|---|
| `cloud_centric.py` | Architecture **tout-Cloud** : le module de traitement est déployé uniquement sur le serveur Cloud distant. Sert de référence pour mesurer l'impact du délai réseau élevé. | aucune (simulation de base) |
| `edge_prioritized.py` | Architecture **Edge-first** : le module est déployé sur le serveur Edge, proche de la source. Sert de référence pour mesurer le gain de proximité. | aucune (simulation de base) |

---

### Simulations avec courbes

#### [1] `sim_ipt_proche.py` — Comparaison Edge vs Fog vs Cloud selon l'IPT

**Question :** À IPT comparables entre les niveaux, quel niveau offre le meilleur délai bout-en-bout ?

- Topologie en étoile avec trois niveaux (Edge, Fog, Cloud) à des distances croissantes
- Population de type **Poisson** 
- Trois configurations testées (IPT Edge/Fog/Cloud croissants)
- Résultat : histogramme comparatif des délais moyens pour les trois niveaux

**Courbe :** `results_ipt/comparaison_niveaux.png`

---

#### [2] `sim_congestion.py` — Saturation et congestion du nœud Edge

**Question :** Que se passe-t-il quand le taux d'arrivée dépasse la capacité de traitement du Edge ?

- Résultat 1 : délai moyen en fonction du taux de charge ρ
- Résultat 2 : nombre de messages traités en fonction de l'inter-arrivée 

**Courbe :** `results_congestion2/congestion.png`

---

#### [3] `sim_contradiction.py` — Contradiction entre IPT et délai aller-retour

**Question :** Augmenter la puissance de calcul du Cloud compense-t-il son éloignement réseau ?

- IPT Cloud augmente progressivement (de 200 à 12 000 MIPS)
- Le délai réseau Edge <-> Cloud reste fixe (PR = 50 ms)
- Résultat : deux courbes sur axes Y séparés — le délai de calcul diminue tandis que le délai réseau reste constant. Le délai total Cloud reste supérieur au seuil Edge tant que la distance est grande.

**Courbe :** `results_contradiction/contradiction_ipt_aller_retour.png`

---

#### [4] `main_calculs_evolution_ipt.py` — Seuil de basculement Edge -> Cloud selon l'IPT

**Question :** À partir de quel IPT Cloud le Cloud devient-il meilleur que le Edge ?

- IPT Edge fixé à 200 MIPS
- IPT Cloud varie de 200 à 500 MIPS
- Intersection détectée automatiquement et annotée sur le graphique

**Courbe :** `results/evolution_IPT.png`

---

#### [5] `main_calculs_evolution_latence.py` — Seuil de basculement selon la latence réseau

**Question :** À partir de quel délai réseau Edge <-> Cloud le Edge devient-il meilleur que le Cloud ?

- Scénario inverse du [4] : le Cloud est très puissant (IPT = 10 000), le Edge est faible (IPT = 500)
- Le délai réseau PR varie de 0 à 10 ms
- Intersection détectée automatiquement et annotée

**Courbe :** `results2/evolution_PR.png`

---

#### [6] `test_repartitions.py` — Répartition optimale de charge Edge / Cloud

**Question :** Quel ratio de messages Edge/Cloud minimise le délai moyen ?

- Le module de traitement est déployé à la fois sur le Edge et sur le Cloud
- Un routeur personnalisé (`CustomSelection`) distribue les messages selon un ratio Edge allant de 0 % à 100 %
- Résultat : courbe du délai moyen en fonction du pourcentage de tâches traitées par le Edge

**Courbe :** `results/final_repartition4.png`

---

#### [7] `test_3D.py` — Surface 3D interactive (IPT × Latence × Délai)

**Question :** Comment le délai évolue-t-il conjointement selon la puissance du Cloud et la latence réseau ?

- Grille de simulation complète : 6 ratios IPT × 8 valeurs de PR × 3 tailles de workflow
- Deux surfaces par taille de workflow : Cloud (bleus) et Edge (oranges)
- Graphique 3D interactif avec boutons pour filtrer par workflow
- Second graphique 2D : PR de basculement Edge -> Cloud en fonction du ratio IPT

**Fichiers :**
- `results3d/surface_3D.html` — à ouvrir dans un navigateur web
- `results3d/basculement_2D.html` — à ouvrir dans un navigateur web

> Cette simulation est la plus longue : elle lance environ 288 runs.

---

## Structure des dossiers générés

```
results/                    # évolution IPT, répartition hybride
results2/                   # évolution latence réseau
results_ipt/                # comparaison Edge/Fog/Cloud
results_congestion2/        # congestion M/M/1
results_contradiction/      # contradiction IPT vs aller-retour
results3d/                  # surfaces 3D interactives (HTML)
venv/                       # environnement Python (créé par script.sh)
```
