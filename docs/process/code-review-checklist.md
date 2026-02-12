# Code Review Checklist

**Version** : 1.0  
**Date** : 2026-02-13  
**Owner** : Dana (QA Engineer)  
**Source** : RETRO-2-004 - Epic 2 Rétrospective

---

## 🎯 Objectif

Standardiser les critères de code review pour garantir la qualité, la sécurité et la maintenabilité du code. Cette checklist doit être utilisée pour **chaque** pull request.

---

## 📋 Checklist Globale

### Avant de commencer la review

- [ ] Comprendre le contexte (story, objectif métier)
- [ ] Lire les critères d'acceptance (AC)
- [ ] Vérifier que les tests automatisés passent
- [ ] S'assurer que la PR est de taille raisonnable (< 400 lignes)

---

## 🔒 Sécurité (Security Checks)

### Input Validation

- [ ] Tous les inputs utilisateur sont validés (Zod/Yup)
- [ ] Pas de SQL injection possible (paramétrage requêtes)
- [ ] Pas de XSS (échappement des outputs HTML)
- [ ] Pas de NoSQL injection (validation ObjectId, filtres)

```typescript
// ✅ Bon - Validation Zod
const schema = z.object({
  email: z.string().email(),
  amount: z.number().positive(),
});

// ❌ Mauvais - Pas de validation
const data = req.body;
```

### Authentification & Autorisation

- [ ] Routes protégées avec middleware auth
- [ ] RBAC vérifié (user/ops_admin/support/observer)
- [ ] Pas de données sensibles exposées (mot de passe, tokens)
- [ ] Vérification ownership ressources (userId match)

```typescript
// ✅ Bon - RBAC check
export const withRBAC = (allowedRoles: Role[]) => {
  return (handler: ApiHandler) => async (req, res) => {
    if (!allowedRoles.includes(req.user.role)) {
      return res.status(403).json({ error: 'Forbidden' });
    }
    return handler(req, res);
  };
};
```

### Secrets & Configuration

- [ ] Pas de secrets en dur dans le code
- [ ] Variables d'environnement utilisées (.env.local)
- [ ] Pas de clés API exposées côté client
- [ ] Configuration sensible dans server-side uniquement

```bash
# ✅ Bon - .env.local
DATABASE_URL=postgresql://...
JWT_SECRET=xxx

# ❌ Mauvais - En dur dans le code
const API_KEY = "sk-1234567890abcdef";
```

### Audit & Logging

- [ ] Actions critiques loggées avec traceId
- [ ] Pas de données sensibles dans les logs
- [ ] Logs structurés (JSON) pour parsing

```typescript
// ✅ Bon
logger.info({
  action: 'decision_created',
  decisionId: decision.id,
  userId: user.id,
  traceId: req.traceId,
});

// ❌ Mauvais
console.log(`Created decision ${decision} for user ${user}`);
```

---

## ⚡ Performance (Performance Checks)

### Requêtes Database

- [ ] Pas de N+1 queries (utiliser eager loading)
- [ ] Indexes utilisés pour les requêtes fréquentes
- [ ] Pagination pour les listes (> 20 items)
- [ ] Pas de SELECT * (sélectionner colonnes nécessaires)

```typescript
// ✅ Bon - Avec relations
const decisions = await db.query.decisions.findMany({
  with: {
    gates: true,
    match: true,
  },
  limit: 20,
  offset: page * 20,
});

// ❌ Mauvais - N+1
const decisions = await db.query.decisions.findMany();
for (const d of decisions) {
  d.gates = await db.query.gates.findMany({ where: { decisionId: d.id } });
}
```

### Caching

- [ ] React Query avec staleTime approprié
- [ ] Cache Redis pour données fréquemment accédées
- [ ] Invalidation cache cohérente
- [ ] Pas de cache pour données temps réel critiques

```typescript
// ✅ Bon - Cache configuration
const useDecisions = () => {
  return useQuery({
    queryKey: ['decisions'],
    queryFn: fetchDecisions,
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 10 * 60 * 1000,
  });
};
```

### Bundle Size

- [ ] Pas d'import de librairies entières (tree-shaking)
- [ ] Lazy loading pour routes/pages lourdes
- [ ] Images optimisées (WebP, lazy loading)

```typescript
// ✅ Bon - Import sélectif
import { Button, Card } from '@mui/material';

// ❌ Mauvais - Import complet
import MUI from '@mui/material';
```

### Temps de réponse

- [ ] API < 2s (NFR1)
- [ ] Pas de calculs lourds en synchrone
- [ ] Utilisation de workers pour traitements lourds

---

## ♿ Accessibilité (Accessibility Checks)

### Sémantique HTML

- [ ] Utilisation des balises sémantiques (nav, main, article)
- [ ] Hiérarchie de titres cohérente (h1 → h2 → h3)
- [ ] Pas de div/button confusion

```tsx
// ✅ Bon
<nav aria-label="Navigation principale">
  <ul>
    <li><a href="/picks">Picks</a></li>
  </ul>
</nav>

// ❌ Mauvais
<div className="nav">
  <div onClick={...}>Picks</div>
</div>
```

### Attributs ARIA

- [ ] Rôles appropriés (button, link, navigation)
- [ ] Labels descriptifs (aria-label, aria-labelledby)
- [ ] États accessibles (aria-expanded, aria-selected)
- [ ] Messages d'erreur associés (aria-describedby)

```tsx
// ✅ Bon
<button
  aria-label="Fermer le panneau"
  aria-expanded={isOpen}
  onClick={toggle}
>
  <CloseIcon />
</button>
```

### Navigation Clavier

- [ ] Tous les éléments interactifs focusables
- [ ] Ordre de tabulation logique
- [ ] Gestion de l'échappement (Escape pour fermer)
- [ ] Pas de piège à focus

### Contrastes & Lisibilité

- [ ] Ratio contraste >= 4.5:1 pour texte normal
- [ ] Ratio contraste >= 3:1 pour texte large
- [ ] Pas d'information uniquement par couleur
- [ ] Focus visible sur tous les éléments interactifs

```typescript
// ✅ Bon - Information via icône + couleur
<StatusBadge 
  status="pick" 
  icon={<CheckCircle />}
  label="Validé"
/>

// ❌ Mauvais - Couleur seule
<span className="text-green">Pick</span>
```

### Screen Readers

- [ ] Messages de statut annoncés (aria-live)
- [ ] Pas de contenu caché aux AT (aria-hidden abusif)
- [ ] Textes alternatifs pour images
- [ ] Tableaux avec headers et scopes

---

## 🔤 TypeScript Strictness

### Types

- [ ] Pas de `any` (utiliser `unknown` si nécessaire)
- [ ] Interfaces complètes (pas de propriétés optionnelles abusives)
- [ ] Types de retour explicites pour fonctions publiques
- [ ] Enums pour valeurs finies

```typescript
// ✅ Bon
type DecisionStatus = 'pick' | 'no_bet' | 'blocked';
interface Decision {
  id: string;
  status: DecisionStatus;
  confidence: number;
}

// ❌ Mauvais
const processDecision = (data: any) => { ... };
```

### Null Safety

- [ ] Pas de `!` non justifié (non-null assertion)
- [ ] Gestion des cas null/undefined
- [ ] Optionnal chaining utilisé correctement

```typescript
// ✅ Bon
const userName = user?.profile?.name ?? 'Anonyme';

// ❌ Mauvais
const userName = user!.name;
```

### Généricité

- [ ] Utilisation de génériques pour composants réutilisables
- [ ] Contraintes de types appropriées

---

## 🧪 Tests

### Couverture

- [ ] Tests unitaires pour logique métier
- [ ] Tests d'intégration pour API/DB
- [ ] Tests E2E pour parcours critiques
- [ ] Couverture > 80% pour code métier

### Qualité des tests

- [ ] Tests indépendants (pas d'ordre de dépendance)
- [ ] Mocks appropriés (pas de mocks excessifs)
- [ ] Cas limites testés (edge cases)
- [ ] Pas de tests tautologiques (tester la logique, pas l'implémentation)

```typescript
// ✅ Bon - Teste le comportement
it('should classify as no_bet when confidence < threshold', () => {
  const result = classifyDecision({ confidence: 0.5, threshold: 0.6 });
  expect(result).toBe('no_bet');
});

// ❌ Mauvais - Teste l'implémentation
it('should call classifyDecision with correct params', () => {
  const spy = jest.spyOn(classifier, 'classify');
  classifyDecision(data);
  expect(spy).toHaveBeenCalledWith(data);
});
```

### Assertions claires

- [ ] Messages d'erreur explicites
- [ ] Utilisation de matchers appropriés
- [ ] Pas de assertions complexes

---

## 📖 Code Quality

### Clean Code

- [ ] Fonctions petites (< 20 lignes idéalement)
- [ ] Noms descriptifs (pas de `data`, `item`, `process`)
- [ ] Pas de duplication (DRY)
- [ ] Séparation des préoccupations (SRP)

```typescript
// ✅ Bon
const calculateWinRate = (wins: number, total: number): number => {
  if (total === 0) return 0;
  return (wins / total) * 100;
};

// ❌ Mauvais
const calc = (a: number, b: number) => a / b;
```

### Commentaires

- [ ] Commentaires pour le "pourquoi", pas le "quoi"
- [ ] Pas de code commenté mort
- [ ] Documentation JSDoc pour fonctions publiques

```typescript
// ✅ Bon - Pourquoi, pas quoi
// Arrondir à 2 décimales pour affichage monétaire
const roi = Math.round(rawRoi * 100) / 100;

// ❌ Mauvais - Redondant
// Calculer le ROI
const roi = (gains - costs) / costs;
```

### Gestion d'erreurs

- [ ] Erreurs typées (pas de `throw 'message'`)
- [ ] Messages d'erreur actionnables
- [ ] Pas de catch silencieux (empty catch)
- [ ] Error boundaries pour erreurs React

```typescript
// ✅ Bon
class ValidationError extends Error {
  constructor(message: string, public field: string) {
    super(message);
  }
}

try {
  await saveDecision(data);
} catch (error) {
  if (error instanceof ValidationError) {
    showFieldError(error.field, error.message);
  } else {
    logger.error('Unexpected error', error);
    showGenericError();
  }
}
```

---

## 🏗️ Architecture

### Structure

- [ ] Code métier dans `src/features/`
- [ ] Composants réutilisables bien placés
- [ ] Pas de dépendances circulaires
- [ ] Séparation UI / Logique / Data

### Patterns

- [ ] Patterns établis respectés (voir component-patterns.md)
- [ ] Pas de réinvention de la roue
- [ ] Composants existants réutilisés

### API Design

- [ ] Response envelope standard (`{data, meta, error}`)
- [ ] Codes HTTP appropriés
- [ ] Validation Zod des inputs/outputs
- [ ] Rate limiting si nécessaire

```typescript
// ✅ Bon
Response.json({
  data: decisions,
  meta: { total, page, traceId },
  error: null,
});

// ❌ Mauvais
Response.json(decisions);
```

---

## 📝 Documentation

### Code

- [ ] README mis à jour si nécessaire
- [ ] Changelog pour features majeures
- [ ] Commentaires complexes expliqués

### Story Handoff

- [ ] Template handoff complété (si story terminée)
- [ ] Dépendances documentées
- [ ] Pièges identifiés notés

---

## ✅ Approval Process

### Niveaux de Review

| Type de changement | Reviewers requis |
|-------------------|------------------|
| Fix bug mineur | 1 dev |
| Feature standard | 1 dev + 1 senior |
| Feature critique | 2 seniors + QA |
| Changement architecture | Tech Lead + équipe |

### Checklist finale avant merge

- [ ] Tous les checks CI verts
- [ ] Tous les commentaires résolus
- [ ] Approbations requises obtenues
- [ ] Rebase sur branche principale fait
- [ ] Pas de conflits
- [ ] Description PR à jour

---

## 🚨 Red Flags (Bloquant)

Ces éléments doivent **toujours** bloquer le merge :

1. ❌ **Sécurité** : SQL injection, XSS, secrets exposés
2. ❌ **Performance** : N+1 queries, pas de pagination
3. ❌ **Accessibilité** : Navigation clavier impossible
4. ❌ **Tests** : Tests qui échouent, pas de tests pour logique métier
5. ❌ **TypeScript** : `any` non justifié, erreurs de type
6. ❌ **Qualité** : Code dupliqué, fonctions > 50 lignes

---

## 📊 Métriques de Review

### KPIs à suivre

| Métrique | Cible | Mesure |
|----------|-------|--------|
| Temps moyen de review | < 24h | GitHub metrics |
| Issues de sécurité détectées | > 95% avant prod | Security audit |
| Bugs en prod | < 2/sprint | Bug tracker |
| Satisfaction équipe | > 4/5 | Survey |

---

## 📚 Références

- [Component Patterns](../architecture/component-patterns.md)
- [RBAC Patterns](../architecture/rbac-patterns.md)
- [React Query Patterns](../frontend/react-query-patterns.md)
- [Security Guidelines](../../docs/security/security-guidelines.md)
- [Performance NFRs](../../docs/requirements/nfrs.md)

---

*Checklist créée par Dana - 2026-02-13*  
*Basée sur les learnings des Stories 2.1-2.4*  
*À utiliser pour chaque Pull Request*
