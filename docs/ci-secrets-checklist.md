# CI Secrets Checklist

## Secrets Requis par Environnement

### Tests Basiques (Local/CI)

Aucun secret requis.

### Environnement Staging

| Secret | Description | Requis |
|--------|-------------|--------|
| `BASE_URL_STAGING` | URL staging | Optionnel |
| `API_URL_STAGING` | API staging | Optionnel |

### Environnement Production

| Secret | Description | Requis |
|--------|-------------|--------|
| `BASE_URL_PRODUCTION` | URL production | Optionnel |
| `API_URL_PRODUCTION` | API production | Optionnel |

---

## Configuration GitHub Actions

### Ajouter un Secret

1. Repository → Settings → Secrets and variables → Actions
2. Click **New repository secret**
3. Nommer et définir la valeur
4. Cliquer **Add secret**

### Utilisation dans le Workflow

```yaml
- name: Run tests
  env:
    BASE_URL: ${{ secrets.BASE_URL_STAGING }}
  run: npm run test:e2e
```

---

## Vérification

- [ ] Aucune donnée sensible dans le code
- [ ] Secrets utilisent `${{ secrets.XXX }}`
- [ ] Variables d'env pour les URLs
- [ ] Pas de credentials dans les logs
