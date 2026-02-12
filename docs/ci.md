# CI/CD Pipeline Documentation

## Pipeline de Test Automatisé

Généré par **BMad TEA Agent** - Test Architect Module  
Date: 2026-02-12

---

## Vue d'Ensemble

Ce pipeline CI/CD exécute des tests E2E avec Playwright, incluant :

| Stage | Description | Durée Estimée |
|-------|-------------|---------------|
| **Lint** | Vérification qualité du code | ~2 min |
| **Test** | 4 shards parallèles Playwright | ~10 min/shard |
| **Burn-In** | 10 itérations détection flaky | ~30 min |
| **Report** | Agrégation résultats | ~1 min |

---

## Configuration

### Fichiers Générés

```
.github/workflows/test.yml     # Pipeline principal
scripts/
  ├── burn-in.sh              # Script burn-in local
  ├── ci-local.sh             # Simulation CI locale
  └── test-changed.sh         # Tests sélectifs
docs/
  ├── ci.md                   # Cette documentation
  └── ci-secrets-checklist.md # Checklist secrets
```

### Déclencheurs

- **Push** sur `main`, `master`, `develop`
- **Pull Request** vers `main`, `master`, `develop`
- **Planifié** : Dimanche 2h UTC (burn-in hebdomadaire)

---

## Utilisation

### Exécution Locale

```bash
# Simuler CI localement
./scripts/ci-local.sh

# Tester les fichiers modifiés
./scripts/test-changed.sh

# Burn-in sur 10 itérations
./scripts/burn-in.sh 10

# Burn-in avec branche custom
./scripts/burn-in.sh 10 develop
```

### Exécution Sélective

Le script `test-changed.sh` détecte automatiquement :

| Type de Changement | Action |
|-------------------|--------|
| Config critique (`package.json`, workflows) | Tous les tests |
| Auth/Security | Tests `@auth` + `@smoke` |
| API | Tests API + smoke |
| Fichiers de test | Tests spécifiques modifiés |
| Documentation | Smoke tests uniquement |

---

## Structure du Pipeline

### 1. Lint Stage

- Installe Node.js (version `.nvmrc`)
- Cache des dépendances npm
- Exécute `npm run lint`

### 2. Test Stage (Sharded)

- **4 shards parallèles** (`fail-fast: false`)
- Cache des browsers Playwright
- Exécute : `npm run test:e2e -- --shard=X/4`
- Upload artifacts sur échec

### 3. Burn-In Stage

- **10 itérations** consécutives
- Détecte les tests flaky
- Échec immédiat si une itération échoue
- Upload artifacts de debug

### 4. Report Stage

- Agrège tous les résultats
- Génère résumé GitHub Actions
- Upload rapport consolidé

---

## Quality Gates

### Seuils de Qualité

| Priorité | Exigence |
|----------|----------|
| **P0** | 100% de réussite requis |
| **P1** | ≥ 95% de réussite |
| **Burn-In** | 10/10 itérations réussies |

### Artifact Retention

- Rapports Playwright : **30 jours**
- Résultats tests : **30 jours**
- Burn-in failures : **30 jours**

---

## Dépannage

### Tests Échouent en CI mais Passent Localement

1. Utiliser `ci-local.sh` pour reproduire
2. Vérifier les variables d'environnement
3. Vérifier les versions Node (`.nvmrc`)

### Cache Non Fonctionnel

```bash
# Vider le cache GitHub Actions
# Settings → Actions → Cache → Manage → Delete
```

### Tests Flaky Détectés

- Consulter artifacts `burn-in-failures/`
- Vérifier logs par itération
- Ajouter retries ou stabiliser tests

---

## Secrets Requis

Aucun secret supplémentaire requis pour les tests de base.

Pour les environnements staging/production, voir `ci-secrets-checklist.md`.

---

## Intégrations

### Badges (à ajouter au README.md)

```markdown
![Tests](https://github.com/OWNER/REPO/workflows/Test%20Pipeline/badge.svg)
```

### Notifications

Le pipeline génère des résumés dans l'onglet **Actions** → **Summary**.

---

## Maintenance

### Mise à Jour Playwright

```bash
cd nba-prono
npm update @playwright/test
npx playwright install
```

### Ajouter un Shard

Modifier `.github/workflows/test.yml` :
```yaml
matrix:
  shard: [1, 2, 3, 4, 5]  # Ajouter 5
```

---

**Documentation générée automatiquement par BMad TEA Agent**
