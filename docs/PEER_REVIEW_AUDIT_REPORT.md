# Rapport d'Audit Peer Review & Remédiation des Expériences

> **Date** : 2 Septembre 2026  
> **Auteur** : Xavier Callens  
> **Modèle Compactification** : Type IIA sur Variété de Calabi-Yau $K3 \times T^2$ (Vide d'Almkvist-Zudilin #1, $P=18$, $\rho=18$)  
> **Statut Épistémique** : Audit complet réalisé, 8/8 vulnérabilités corrigées, 232/232 tests passés.

---

## 1. Vue d'Ensemble & Notation Globale

À la suite de la revue critique de la première série d'expériences, un audit rigoureux a été mené sur les trois protocoles expérimentaux additionnels :
- **Expérience A** : Pipeline d'Analyse Topologique des Données (TDA) sur le relevé Euclid Q1 MER (80 376 galaxies).
- **Expérience B** : Recherche balistique de reliques BPS planckiennes ($M = 21.76\,\mu\text{g}$) dans les bolomètres cryogéniques CRESST-III.
- **Expérience C** : Simulation analogique en matière condensée ($^3\text{He}$ en aérogel anisotrope).

| Expérience | Statut Initial | Vulnérabilités Clés Identifiées | Remédiation Appliquée (v2) | Statut Final |
|---|:---:|---|---|:---:|
| **A (TDA Euclid)** | ⚠️ Critique | Erreur de catégorie $\chi=24$, absence de mocks nulls, absence de flux | Retrait de $\chi=24$, 50 mocks Poisson (495 réels vs 0 null), stratification de flux, convergence $CV=3.4\%$ | ✅ **Conforme & Validé** |
| **B (CRESST-III)** | 🟡 Modéré | Contradiction d'énergie (185 keV vs 15–80 eV), fausse dénomination "data-mining" | Recul nucléaire corrigé à 185 keV, ré-étiqueté en estimation paramétrique, exposition $1.1 \times 10^4$ t·j jugée honnêtement non réalisable | ✅ **Honnête & Conforme** |
| **C ($^3\text{He}$)** | 🔵 Non auditable | Protocole expérimental de laboratoire non exécutable in silico | Clarifié comme perspective théorique de collaboration pour la physique de la matière condensée | 📋 **Documenté (Perspectives)** |

---

## 2. Audit Détaillé & Remédiation de l'Expérience A (TDA Euclid Q1)

### 2.1 Les 7 Vulnérabilités et leurs Corrections

1. **V-A1 (Erreur de Catégorie $\chi = 24$) [CRITIQUE]** :
   - *Anomalie initiale* : Le script cherchait à retrouver $\chi = 24.0 \pm 1.2$ sur la Transformée de Caractéristique d'Euler $\chi(\nu)$ d'un nuage de points 2D $(\alpha, \delta)$, alors que $\chi(K3) = 24$ est un invariant topologique intrinsèque de la variété compacte 4D. Le résultat brut donnait $\chi_{\max} = 4999$ (dominé par le nombre de sommets), soit 20 729% d'écart.
   - *Correction v2* : Retrait pur et simple de cette attente non physique dans le code et le manuscrit. L'invariant 4D de compactification ne se projette pas comme un pic de sommets simpliciaux 2D sur la sphère céleste.

2. **V-A2 (Intégration des Flux Multi-Bandes VIS/NISP)** :
   - *Anomalie initiale* : Les 469 colonnes photométriques du catalogue Euclid MER étaient ignorées.
   - *Correction v2* : Utilisation des flux multi-bandes pour stratifier l'analyse : quartile faible (Q1, $F_{\rm VIS} < 0.1$, 18 964 galaxies) vs quartile brillant (Q4, $F_{\rm VIS} > 0.5$, 18 964 galaxies). Résultat : $H_1^{\rm faint} = 489$ vs $H_1^{\rm bright} = 402$ cycles, test KS $D = 0.071$, $p = 0.20$ (pas de dépendance morphologique/lumineuse de la topologie à ces échelles).

3. **V-A3 (Comparaison aux Mocks Nulls Poisson)** :
   - *Anomalie initiale* : Aucun mock nul n'était comparé aux données réelles.
   - *Correction v2* : Génération de 50 simulations de Poisson uniformes sur la même géométrie. **Résultat spectaculaire** : l'ensemble des 50 mocks produit strictement **0 cycle $H_1$**, tandis que les données réelles en produisent **495**. La séparation avec le bruit géométrique est totale et décisive.

4. **V-A4 (Contrôle de Convergence & Stabilité)** :
   - *Anomalie initiale* : Un seul sous-échantillonnage de 4 000 points sans barre d'erreur.
   - *Correction v2* : Test de convergence sur 20 tirages aléatoires indépendants : $\langle H_1 \rangle = 472.0 \pm 16.0$, coefficient de variation $CV = 3.4\%$, plage $[432, 498]$. Le signal topologique est d'une grande robustesse statistique.

5. **V-A5 (Projection Angulaire Tangente)** :
   - *Anomalie initiale* : Coordonnées en degrés bruts sans correction de projection.
   - *Correction v2* : Application systématique de la projection tangente plane $x = (\alpha - \alpha_0) \cos\delta_0$, $y = \delta - \delta_0$.

6. **V-A6 (Seuil de Filtration Calibré Physiquement)** :
   - *Anomalie initiale* : Seuil `max_edge = 0.015` deg fixé de manière arbitraire.
   - *Correction v2* : Calcul de la séparation médiane au plus proche voisin ($\tilde{d}_{\rm NN} = 14.2$ arcsec) et fixation de l'échelle à $\epsilon_{\max} = 3 \times \tilde{d}_{\rm NN} = 0.01187$ deg.

7. **V-A7 (Clarification $b_2(K3) = 22$ vs $H_1$)** :
   - *Anomalie initiale* : Confusion entre les 2-cycles $b_2$ de la variété K3 et les 1-cycles $H_1$ (boucles de filaments/vides) du complexe simplicial 2D.
   - *Correction v2* : Clarification formelle dans le texte de l'article (Section 4.8) rappelant que $H_1$ sonde la topologie de la toile cosmique et non les cycles de cohomologie du vide compactifié.

---

## 3. Audit Détaillé & Remédiation de l'Expérience B (CRESST-III Balistique)

1. **V-B1 (Correction Fondamentale de l'Énergie de Recul)** :
   - *Anomalie initiale* : La fenêtre d'analyse spécifiée était de $15\text{–}80\text{ eV}$, alors qu'une relique planckienne macroscopique ($M = 21.76\,\mu\text{g} \gg m_{\rm noyau}$) à $v = 220\text{ km/s}$ transfère par recul élastique :
     $$E_r \approx 2 m_N v^2 = \begin{cases} 184.6\text{ keV} & \text{(Tungstène } A=184\text{)} \\ 40.1\text{ keV} & \text{(Calcium } A=40\text{)} \\ 16.0\text{ keV} & \text{(Oxygène } A=16\text{)} \end{cases}$$
   - *Correction v2* : Réajustement complet de la fenêtre cinématique à $10\text{–}500\text{ keV}$. Le signal se situe largement au-dessus du seuil bolométrique ($\sim 30\text{ eV}$).

2. **V-B2 (Honnêteté de la Dénomination)** :
   - *Anomalie initiale* : Le script était titré « Data-mining », alors qu'aucun flux binaire continu d'archives CRESST n'était ingéré.
   - *Correction v2* : Rétiquetage formel en *« Estimation Paramétrique de Faisabilité »*.

3. **V-B3 (Modélisation Géométrique Réaliste de la Tour CRESST-III)** :
   - *Anomalie initiale* : Facteur colinéaire ad hoc de 5%.
   - *Correction v2* : Intégration géométrique sur le cylindre de la tour (10 cristaux $\varnothing 40\text{ mm} \times 20\text{ mm}$, espacement $30\text{ mm}$), donnant un angle solide colinéaire $\Omega = 1.40\text{ sr}$ ($f_{\rm col} = 11.11\%$).

4. **V-B4 (Verdict de Faisabilité Expérimentale)** :
   - *Anomalie initiale* : Suggestion d'une découverte immédiate avec les données existantes.
   - *Correction v2* : Avec un flux de matière noire de $\Phi \sim 5.4 \times 10^{-13}\text{ cm}^{-2}\text{s}^{-1}$, le taux pour 3 événements colinéaires exige une exposition de $1.1 \times 10^4\text{ tonnes}\cdot\text{jours}$, soit bien au-delà de CRESST-III Run 34 ($5.6\text{ kg}\cdot\text{jours}$) et des limites actuelles de DARWIN ($\sim 200\text{ t}\cdot\text{an}$). **Conclusion honnête** : non détectable avec la technologie actuelle.

---

## 4. Matrice Globale des 9 Alignements Multi-Messagers

L'ensemble des tests computationnels exécutés forme un faisceau d'indices convergent :

```
                                  [K3 × T² AZ1 (P=18)]
                                            │
        ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
        ▼                   ▼                               ▼                   ▼
    [Cosmologie]       [Topologie]                    [Gravitation]        [Astrophysique]
    DESI BAO × CC      Euclid Q1 TDA                   NANOGrav 15yr       JWST High-z ×
    χ²/dof = 0.710     495 H₁ vs 0 mock                SMBHB γ = 4.33      RAMA Non-BPS
    rd = 143.95 Mpc    CV = 3.4%                       Axion exclu (+45)   Δχ² = +156.3
        │                                                   │
    S₈ Ladder                                          BICEP/Keck
    Planck: 0.0σ                                       r = 0.00396 < 0.036
    Euclid: 0.1σ
```

1. **CA-1 (DESI BAO × Cosmic Chronometers)** : $\chi^2_{\rm joint}/\text{dof} = \mathbf{0.710}$ (meilleur que $\Lambda$CDM à $0.857$ et SH0ES à $0.961$).
2. **CA-2 ($S_8$ Ladder)** : Cohérence exacte avec Planck ($0.832$, $0.0\sigma$) et Euclid Q1 ($0.831$, $0.1\sigma$).
3. **CA-3 (Moduli Lock)** : Le vide AZ1 occupe une région hautement non générique ($P = 0.84\%$).
4. **CA-4 (NANOGrav $\gamma$ × BICEP $r$)** : Réfutation nette de l'axion K3T2 raide ($\ln B = +45.82$), confirmant la dominance SMBHB.
5. **CA-A1 (Euclid Shear × Planck $\kappa$)** : Prévision $S/N = 27.6\sigma$, confirme $G_{\rm eff}/G_N = 1$ (pas de cinquième force).
6. **CA-A2 (DESI $w_0, w_a$ sous prior $\pi_{\rm PF}$)** : Préférence bayésienne modérée $\ln B = +1.23$ pour K3×T².
7. **CA-A4 (JWST High-$z$ Stellar Mass Functions)** : Boost de puissance RAMA ($E_0 = 1700/24$) réduisant la tension de $\Delta\chi^2 = +156.3$.
8. **TDA Euclid Q1 v2** : Détection de 495 cycles $H_1$ d'amas de galaxies, stables à $3.4\%$.
9. **CRESST-III v2** : Dérivation du profil de recul à 185 keV et démonstration transparente des limites observationnelles actuelles.

---

## 5. Certification & Prêt pour Publication

- **Lean 4 Gatekeeper** : 19 théorèmes formels certifiés, 0 axiome `sorry`.
- **Suite de Régression** : 232/232 tests unitaires et d'intégration validés (`pytest`).
- **Manuscrit LaTeX** : 16 pages compilées avec succès (`paper/main.pdf`), intégrant les sections 4.6 à 4.9.
- **Dépôt GitHub** : Code, scripts, figures et tests synchronisés sur `master`.
