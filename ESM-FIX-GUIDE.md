# Guide de Résolution - Configuration ESM Tests

**Date:** 2026-02-12  
**Problème:** Tests npm échouent à cause d'incompatibilité ESM  
**Solution:** Downgrade jsdom vers v24.0.0 (CommonJS compatible)

---

## ✅ Configuration Déjà Appliquée

Le fichier `nba-prono/package.json` a été modifié avec :

```json
{
  "devDependencies": {
    "jsdom": "24.0.0"
  },
  "overrides": {
    "vite": "6.4.1",
    "jsdom": "24.0.0",
    "@exodus/bytes": "1.12.0",
    "html-encoding-sniffer": "3.0.0",
    "data-urls": "4.0.0",
    "whatwg-url": "12.0.0"
  }
}
```

---

## 🚀 Instructions d'Installation

### Option 1: Script Automatique (Windows)

Double-cliquez sur le fichier `install-jsdom-fix.bat` à la racine du projet.

### Option 2: Commandes Manuelles

Ouvrez un terminal et exécutez :

```bash
# 1. Nettoyage complet
rm -rf node_modules package-lock.json nba-prono/node_modules nba-prono/package-lock.json

# 2. Nettoyage cache npm
npm cache clean --force

# 3. Installation fraîche
npm install --legacy-peer-deps

# 4. Vérification
npm ls jsdom
# Doit afficher: jsdom@24.0.0
```

### Option 3: Installation directe dans nba-prono

```bash
cd nba-prono
npm install jsdom@24.0.0 --save-dev --legacy-peer-deps
```

---

## 🧪 Validation

Après installation, testez avec :

```bash
# Test unitaire
npm test

# Vérification spécifique ESM
npm test 2>&1 | grep -E "(ESM|html-encoding-sniffer|@exodus/bytes)" || echo "✅ Aucune erreur ESM"
```

**Succès attendu:**
- ✅ Tests qui passent
- ✅ Aucune erreur liée à ESM
- ✅ jsdom@24.0.0 installé

---

## ⚠️ Note sur la Version Node.js

L'environnement actuel utilise Node.js v20.11.0.  
Les packages récents (jsdom@28+, etc.) nécessitent Node.js >=20.19.0.

**Solution choisie:** Downgrade jsdom vers v24.0.0 qui est compatible avec Node.js v20.11.0.

Si vous souhaitez utiliser des versions plus récentes de jsdom, vous devrez mettre à jour Node.js vers >=20.19.0.

---

## 📁 Fichiers Modifiés

- `nba-prono/package.json` - Modifié (jsdom@24.0.0 + overrides)
- `install-jsdom-fix.bat` - Créé (script d'installation Windows)
- `ESM-FIX-GUIDE.md` - Ce fichier

---

## 🆘 En Cas de Problème

Si l'installation échoue :

1. **Vérifiez la version de Node.js:**
   ```bash
   node --version
   # Devrait afficher: v20.11.0 ou supérieur
   ```

2. **Utilisez --force si nécessaire:**
   ```bash
   npm install --force
   ```

3. **Alternative avec pnpm (si installé):**
   ```bash
   pnpm install
   ```

4. **Alternative avec yarn (si installé):**
   ```bash
   yarn install
   ```

---

## ✅ Checklist de Validation

- [ ] jsdom@24.0.0 installé (`npm ls jsdom`)
- [ ] `npm test` s'exécute sans erreur
- [ ] Aucune erreur ESM dans la sortie des tests
- [ ] Package-lock.json régénéré
- [ ] Tests existants toujours passants

---

**Workflow Correct Course - BMAD Method**  
**Statut:** Configuration appliquée, installation en attente d'exécution manuelle
