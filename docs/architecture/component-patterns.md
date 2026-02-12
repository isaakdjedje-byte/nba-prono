# Component Patterns Guide

**Version** : 1.0  
**Date** : 2026-02-13  
**Owner** : Elena (Junior Dev)  
**Review** : Charlie (Senior Dev)  
**Source** : RETRO-2-001 - Epic 2 Rétrospective

---

## 🎯 Objectif

Ce document définit les patterns de composants réutilisables établis lors des Stories 2.1 à 2.4. Il sert de référence pour garantir la cohérence UI dans Epic 3 et au-delà.

---

## 📋 Pattern Catalog

### 1. DecisionCard Pattern

**Fichier** : `src/features/decisions/components/DecisionCard.tsx`

**Usage** : Affichage résumé d'une décision (Pick/No-Bet) dans les listes

```typescript
// Interface DecisionCard
interface DecisionCardProps {
  decision: DecisionViewItem;
  variant?: 'default' | 'compact' | 'detailed';
  onClick?: (decision: DecisionViewItem) => void;
  showRationale?: boolean;
}
```

**Structure** :
```
┌─────────────────────────────────────┐
│ [StatusBadge]  Match Date           │
├─────────────────────────────────────┤
│ Home Team vs Away Team              │
│ [Conf: 75%] [Edge: +12%]            │
├─────────────────────────────────────┤
│ Rationale courte (optionnel)        │
│ "Edge value sur favori défaitiste"  │
└─────────────────────────────────────┘
```

**Variants** :
- `default` : Vue standard (utilisée dans Picks/No-Bet)
- `compact` : Vue réduite (utilisée dans historique dense)
- `detailed` : Vue enrichie (utilisée dans dashboard)

**Exemple d'utilisation** :
```tsx
<DecisionCard
  decision={decision}
  variant="compact"
  onClick={handleDecisionClick}
  showRationale={false}
/>
```

**Bonnes pratiques** :
- ✅ Toujours utiliser `DecisionCard` plutôt que créer un composant similaire
- ✅ Utiliser la prop `variant` pour adapter le contexte
- ✅ Propager `onClick` pour navigation vers détail
- ❌ Ne pas modifier la structure interne (utiliser variant)
- ❌ Ne pas dupliquer le style (utiliser le composant)

---

### 2. StatusBadge Pattern

**Fichier** : `src/features/decisions/components/StatusBadge.tsx`

**Usage** : Indicateur visuel du statut d'une décision

```typescript
interface StatusBadgeProps {
  status: 'pick' | 'no_bet' | 'blocked' | 'pending';
  size?: 'small' | 'medium' | 'large';
  showIcon?: boolean;
}
```

**Mapping statut → UI** :

| Statut | Couleur | Icône | Usage |
|--------|---------|-------|-------|
| pick | Vert (success) | CheckCircle | Signal exploitable |
| no_bet | Orange (warning) | Block | Signal non exploitable |
| blocked | Rouge (error) | Cancel | Hard-stop activé |
| pending | Gris (default) | Hourglass | En attente de résultat |

**Exemple** :
```tsx
<StatusBadge status="pick" size="medium" showIcon />
```

**Accessibilité** :
- Ajouter `aria-label` descriptif
- Ne pas dépendre uniquement de la couleur

```tsx
<StatusBadge 
  status="pick" 
  aria-label="Décision pick - recommandée"
/>
```

---

### 3. RationalePanel Pattern

**Fichier** : `src/features/decisions/components/RationalePanel.tsx`

**Usage** : Affichage détaillé de la justification d'une décision

```typescript
interface RationalePanelProps {
  decision: DecisionDetail;
  gates: GateResult[];
  showDisclaimer?: boolean;
  variant?: 'default' | 'audit';
}
```

**Structure** :
```
┌─────────────────────────────────────┐
│ RATIONALE PANEL                     │
├─────────────────────────────────────┤
│ 🎯 Contexte match                   │
│    Équipes, date, statistiques      │
├─────────────────────────────────────┤
│ 📊 Gates Evaluation                 │
│    ✓ Edge: +12% (PASS)              │
│    ✓ Confiance: 78% (PASS)          │
│    ⚠ Drift: 8% (WARNING)            │
├─────────────────────────────────────┤
│ 📝 Conclusion                       │
│    Classification Pick/No-Bet       │
├─────────────────────────────────────┤
│ ℹ️ Disclaimer (Story 2.4)           │
│    "Cette analyse est fournie..."   │
└─────────────────────────────────────┘
```

**Variant `audit`** : Ajoute métadonnées pour vue observateur
- Timestamp de génération
- Version du modèle
- Trace ID

**Extension** : Story 2.4 a ajouté `DecisionDisclaimer`
```tsx
<RationalePanel
  decision={decision}
  gates={gates}
  showDisclaimer={true}  // Active le disclaimer Story 2.4
/>
```

---

### 4. GateResultsList Pattern

**Fichier** : `src/features/decisions/components/GateResultsList.tsx`

**Usage** : Affichage structuré des résultats de gates

```typescript
interface GateResultsListProps {
  gates: GateResult[];
  showDetails?: boolean;
  variant?: 'compact' | 'detailed';
}
```

**Mapping Gate → Affichage** :

| Gate | Icône | Indicateur | Info affichée |
|------|-------|------------|---------------|
| Edge | TrendingUp | Pourcentage | Valeur + Seuil |
| Confiance | Psychology | Pourcentage | Score + Niveau |
| Drift | SyncProblem | Pourcentage | Écart + Seuil |

**Exemple** :
```tsx
<GateResultsList
  gates={[
    { name: 'edge', value: 12.5, threshold: 5.0, status: 'pass' },
    { name: 'confidence', value: 0.78, threshold: 0.60, status: 'pass' },
  ]}
  showDetails={true}
/>
```

---

### 5. HistoryFilterBar Pattern

**Fichier** : `src/features/history/components/HistoryFilterBar.tsx`

**Usage** : Barre de filtres temporels pour les vues historiques

```typescript
interface HistoryFilterBarProps {
  filters: HistoryFilters;
  onChange: (filters: HistoryFilters) => void;
  availablePeriods?: PeriodOption[];
}
```

**Fonctionnalités** :
- Sélection période prédéfinie (7j, 30j, 3m, 6m, 12m)
- Sélection dates personnalisées
- Filtre par type de signal
- Conservation dans URL (shallow routing)

**Pattern URL State** :
```typescript
// Synchronisation filtres ↔ URL
const updateFilter = (key: string, value: string) => {
  const params = new URLSearchParams(searchParams);
  params.set(key, value);
  router.push(`/history?${params.toString()}`, { shallow: true });
};
```

**Réutilisation pour Epic 3** :
- Vue Performance utilisera le même pattern
- Adapter les périodes selon besoin analytics

---

### 6. DecisionGuardrail Pattern

**Fichier** : `src/features/decisions/components/DecisionGuardrail.tsx`

**Usage** : Bandeau de rappel éthique/légal (Story 2.4)

```typescript
interface DecisionGuardrailProps {
  variant?: 'info' | 'compact';
  dismissible?: boolean;
  persistent?: boolean;
  messageKey?: string;
}
```

**Message par défaut** :
> "Cet outil est une aide à la décision. Aucun pari n'est placé automatiquement."

**Accessibilité** :
```tsx
<Alert
  role="note"
  aria-label="Information sur la nature de l'outil"
>
```

**Intégration** :
```tsx
// Dans Picks, No-Bet, Historique
<DecisionGuardrail dismissible persistent />
```

---

## 🎨 Design System Integration

### Tokens MUI à utiliser

```typescript
// Colors from theme
const colors = {
  pick: theme.palette.success.main,      // #4CAF50
  noBet: theme.palette.warning.main,     // #FF9800
  blocked: theme.palette.error.main,     // #F44336
  info: theme.palette.info.main,         // #2196F3
};

// Spacing
const spacing = {
  xs: theme.spacing(0.5),  // 4px
  sm: theme.spacing(1),    // 8px
  md: theme.spacing(2),    // 16px
  lg: theme.spacing(3),    // 24px
  xl: theme.spacing(4),    // 32px
};

// Typography
const typography = {
  cardTitle: theme.typography.h6,
  body: theme.typography.body2,
  caption: theme.typography.caption,
};
```

### Responsive Design

**Breakpoints** :
```typescript
const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
const isTablet = useMediaQuery(theme.breakpoints.between('sm', 'md'));
const isDesktop = useMediaQuery(theme.breakpoints.up('md'));
```

**Adaptation composants** :
- Mobile : `DecisionCard` en mode `compact`
- Desktop : `DecisionCard` en mode `default` ou `detailed`

---

## 🧪 Testing Patterns

### Tests unitaires

**Structure test** :
```typescript
describe('DecisionCard', () => {
  it('renders with correct status', () => {
    render(<DecisionCard decision={mockDecision} />);
    expect(screen.getByText('Pick')).toBeInTheDocument();
  });
  
  it('calls onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<DecisionCard decision={mockDecision} onClick={handleClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalled();
  });
});
```

### Tests d'intégration

**Pattern** : Tester la composition de composants
```typescript
it('filters update DecisionCard list', async () => {
  render(<HistoryPage />);
  
  // Changer filtre
  fireEvent.click(screen.getByText('7 derniers jours'));
  
  // Vérifier mise à jour liste
  await waitFor(() => {
    expect(screen.getAllByTestId('decision-card')).toHaveLength(3);
  });
});
```

---

## 📦 Export et Réutilisation

### Index des composants

**Fichier** : `src/features/decisions/components/index.ts`

```typescript
export { DecisionCard } from './DecisionCard';
export { StatusBadge } from './StatusBadge';
export { RationalePanel } from './RationalePanel';
export { GateResultsList } from './GateResultsList';
export { DecisionGuardrail } from './DecisionGuardrail';
```

### Import standardisé

```typescript
// ✅ Bon
import { DecisionCard, StatusBadge } from '@/features/decisions/components';

// ❌ Mauvais - import direct du fichier
import { DecisionCard } from '@/features/decisions/components/DecisionCard';
```

---

## 🔧 Extension Guidelines

### Pour Epic 3 (Performance)

**Nouveau composant : PerformanceCard**

S'inspirer de `DecisionCard` avec adaptation :
```typescript
interface PerformanceCardProps {
  metric: PerformanceMetric;
  trend: 'up' | 'down' | 'stable';
  period: string;
}
```

**Réutiliser** :
- Structure de layout
- Pattern de variants
- Gestion du onClick
- Tests structure

**Adapter** :
- Contenu (métriques vs décisions)
- Icônes (TrendingUp vs SportsBasketball)
- Couleurs (tendance vs statut)

---

## ✅ Checklist Création Composant

Avant de créer un nouveau composant, vérifier :

- [ ] Un composant existant ne couvre pas déjà le besoin (utiliser `variant`)
- [ ] L'interface est cohérente avec les patterns établis
- [ ] Les props suivent la convention (optional → required)
- [ ] Les tests suivent le pattern (render → interact → assert)
- [ ] L'accessibilité est prise en compte (ARIA, contraste)
- [ ] Le composant est exporté dans l'index
- [ ] La documentation est mise à jour

---

## 📚 Références

- **Stories sources** : 2.1, 2.2, 2.3, 2.4
- **Composants référence** : `src/features/decisions/components/*`
- **Design System** : `src/styles/theme.ts`
- **Tests exemples** : `src/features/decisions/components/*.test.tsx`

---

*Document créé par Elena - 2026-02-13*  
*Review par Charlie - 2026-02-13*  
*Basé sur les learnings des Stories 2.1-2.4*
