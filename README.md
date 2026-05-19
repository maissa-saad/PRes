# Algorithme de sélection — Edge / Fog / Cloud

> **Avant de lancer quoi que ce soit ici**, assurez-vous d'avoir déjà exécuté `script.sh` dans le dossier `PROJET_13_tests/`. C'est lui qui installe tout.

---

## Lancer la simulation

```bash
chmod +x script.sh
./script.sh
```

C'est tout. Le script réutilise ce qui a déjà été installé et génère les résultats automatiquement.

---

## Ce que fait cette simulation

On simule une architecture avec **17 nœuds** et un algorithme intelligent qui décide, pour chaque message, sur quel nœud le traiter. Il ne choisit pas au hasard — il calcule un score pour chaque candidat :

```
score = latence réseau + temps de calcul + α × consommation énergie
```

Le nœud avec le meilleur score (le plus bas) reçoit le message. L'algorithme tient aussi compte de la charge actuelle de chaque nœud pour éviter de tout envoyer au même endroit.

---

## Fichiers du dossier

| Fichier | Rôle |
|---|---|
| `main.py` | Lance la simulation |
| `simpleSelection.py` | L'algorithme de sélection lui-même |
| `topo.json` | La topologie réseau (17 nœuds) |
| `topotest.json` | Une topologie simplifiée à 4 nœuds pour tester rapidement |

---

## Résultats générés

Les courbes sont sauvegardées dans `results_algo/` :

| Fichier | Ce qu'on voit |
|---|---|
| `01_e2e_par_temps.png` | Le délai de chaque message au fil du temps, coloré par niveau (Edge / Fog / Cloud) |
| `02_repartition_noeuds.png` | Combien de messages chaque nœud a traité |
| `03_delai_moyen_niveau.png` | Le délai moyen par niveau, avec l'écart-type |
| `04_latence_liens.png` | Une heatmap des latences réseau entre les nœuds |
| `05_charge_cumulee.png` | L'évolution de la charge sur chaque nœud au fil du temps |

Les données brutes sont dans `sim_trace_algo.csv` (événements de calcul) et `sim_trace_algo_link.csv` (événements réseau).
=======
# PRes
Placement et orchestration de services dans le Edge–Fog–Cloud avec le simulateur YAFS
>>>>>>> 9fcf0810492c9798e137297828c8e976edb6d240
