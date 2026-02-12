# React Query Patterns Guide

**Version** : 1.0  
**Date** : 2026-02-14  
**Owner** : Elena (Junior Dev)  
**Review** : Charlie (Senior Dev)  
**Source** : RETRO-2-003 - Epic 2 Rétrospective

---

## 🎯 Objectif

Ce document définit les patterns React Query établis lors des Stories 2.1 à 2.4. Il garantit une gestion cohérente du state serveur dans Epic 3 et au-delà.

---

## 📋 Philosophy

### Server State vs Client State

```
┌─────────────────────────────────────────┐
│           SERVER STATE                  │
│  (React Query - useQuery/useMutation)   │
│                                         │
│  - Données externes (API, DB)           │
│  - Cache async                          │
│  - Invalidation manuelle                │
│  - Dédoublonnage requêtes               │
└─────────────────────────────────────────┘
           vs
┌─────────────────────────────────────────┐
│           CLIENT STATE                  │
│        (Zustand - useStore)             │
│                                         │
│  - État UI local                        │
│  - Synchrone                            │
│  - Pas de cache persisté                │
│  - Mise à jour immédiate                │
└─────────────────────────────────────────┘
```

**Règle d'or** :
- ✅ Données serveur → React Query
- ✅ État UI → Zustand
- ❌ Jamais de fetch manuel (useEffect + fetch)

---

## 🏗️ Pattern 1 : Query Keys Convention

### Structure

```typescript
// Convention : [entity, id?, filters?, options?]
const queryKeys = {
  // Liste
  all: ['decisions'] as const,
  
  // Liste filtrée
  list: (filters: DecisionFilters) => 
    ['decisions', 'list', filters] as const,
  
  // Détail
  detail: (id: string) => 
    ['decisions', id] as const,
  
  // Relation
  gates: (decisionId: string) => 
    ['decisions', decisionId, 'gates'] as const,
  
  // Infinite query (pagination)
  infinite: (filters: DecisionFilters) => 
    ['decisions', 'infinite', filters] as const,
};
```

### Usage

```typescript
// ✅ Bon - Query keys typées et cohérentes
import { queryKeys } from '@/lib/queries/keys';

// Liste
const { data } = useQuery({
  queryKey: queryKeys.list({ status: 'pick' }),
  queryFn: () => fetchDecisions({ status: 'pick' }),
});

// Détail
const { data } = useQuery({
  queryKey: queryKeys.detail(decisionId),
  queryFn: () => fetchDecision(decisionId),
});

// Relation
const { data } = useQuery({
  queryKey: queryKeys.gates(decisionId),
  queryFn: () => fetchDecisionGates(decisionId),
});
```

### Pourquoi c'est important

- **Invalidation ciblée** : `queryClient.invalidateQueries(['decisions'])`
- **Dédoublonnage** : Même query key = même requête
- **Caching efficace** : Invalidation sélective possible

---

## 🏗️ Pattern 2 : Custom Hooks

### Structure Standard

```typescript
// src/features/decisions/hooks/useDecisions.ts

interface UseDecisionsOptions {
  filters?: DecisionFilters;
  enabled?: boolean;
}

export function useDecisions(options: UseDecisionsOptions = {}) {
  const { filters = {}, enabled = true } = options;
  
  return useQuery({
    queryKey: queryKeys.list(filters),
    queryFn: () => decisionsApi.getAll(filters),
    
    // Configuration standard
    staleTime: 60 * 1000,        // 1 minute
    gcTime: 5 * 60 * 1000,       // 5 minutes (garbage collection)
    refetchOnWindowFocus: false, // Pas de refetch au retour onglet
    placeholderData: keepPreviousData, // Garder anciennes données pendant fetch
    
    // Conditions
    enabled,
    
    // Gestion erreurs
    retry: (failureCount, error) => {
      if (error.status === 404) return false; // Pas de retry sur 404
      return failureCount < 2; // Max 2 retries
    },
  });
}
```

### Hook avec Pagination

```typescript
// src/features/decisions/hooks/useDecisionsInfinite.ts

export function useDecisionsInfinite(filters: DecisionFilters) {
  return useInfiniteQuery({
    queryKey: queryKeys.infinite(filters),
    queryFn: ({ pageParam = 0 }) =>
      decisionsApi.getAll({ ...filters, page: pageParam }),
    getNextPageParam: (lastPage, pages) => {
      if (lastPage.data.length < PAGE_SIZE) return undefined;
      return pages.length;
    },
    initialPageParam: 0,
  });
}
```

### Hook avec Mutation

```typescript
// src/features/decisions/hooks/useCreateDecision.ts

export function useCreateDecision() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: decisionsApi.create,
    
    // Optimistic update
    onMutate: async (newDecision) => {
      // Annuler requêtes en cours
      await queryClient.cancelQueries({ queryKey: queryKeys.all });
      
      // Sauvegarder état précédent
      const previousDecisions = queryClient.getQueryData(
        queryKeys.list({})
      );
      
      // Optimistic update
      queryClient.setQueryData(
        queryKeys.list({}),
        (old) => ({
          ...old,
          data: [newDecision, ...old.data],
        })
      );
      
      return { previousDecisions };
    },
    
    // Rollback en cas d'erreur
    onError: (err, newDecision, context) => {
      queryClient.setQueryData(
        queryKeys.list({}),
        context?.previousDecisions
      );
    },
    
    // Invalidation après succès
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.all });
    },
  });
}
```

---

## 🏗️ Pattern 3 : Cache Strategy

### staleTime vs gcTime

```
┌────────────────────────────────────────────────────────┐
│                    TIMELINE                            │
├────────────────────────────────────────────────────────┤
│  T0      T+1min     T+2min     T+5min     T+6min      │
│  │         │          │          │          │          │
│  ▼         ▼          ▼          ▼          ▼          │
│ FETCH   STALE      STALE    GARBAGE    REFETCH        │
│         TIME       TIME     COLLECT    IF NEEDED      │
│                                                      │
│  [==========FRESH==========][====STALE====][GONE]   │
│                                                      │
│  staleTime: 1 minute                                 │
│  gcTime: 5 minutes                                   │
└────────────────────────────────────────────────────────┘
```

### Configuration par Type de Donnée

```typescript
// Données fréquemment modifiées
const decisionsConfig = {
  staleTime: 60 * 1000,   // 1 minute
  gcTime: 5 * 60 * 1000,  // 5 minutes
};

// Données rarement modifiées
const userConfig = {
  staleTime: 5 * 60 * 1000,   // 5 minutes
  gcTime: 30 * 60 * 1000,     // 30 minutes
};

// Données statiques (config, etc.)
const staticConfig = {
  staleTime: Infinity,        // Jamais stale
  gcTime: 24 * 60 * 60 * 1000, // 24 heures
};

// Données temps réel
const realTimeConfig = {
  staleTime: 0,               // Toujours stale
  refetchInterval: 30 * 1000, // Refetch auto toutes les 30s
};
```

### Exemple Story 2.1 (Historique)

```typescript
// src/features/history/hooks/useHistoryQuery.ts

export function useHistoryQuery(filters: HistoryFilters) {
  return useQuery({
    queryKey: ['history', filters],
    queryFn: () => fetchHistory(filters),
    
    // Historique : données stables
    staleTime: 2 * 60 * 1000,  // 2 minutes
    gcTime: 10 * 60 * 1000,    // 10 minutes
    
    // Conserver données précédentes pendant le fetch
    placeholderData: keepPreviousData,
    
    // Pas de refetch automatique
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}
```

---

## 🏗️ Pattern 4 : URL State Synchronization

### Synchronisation Filtres ↔ URL

```typescript
// src/features/hooks/useFilterQuery.ts

import { useRouter, useSearchParams } from 'next/navigation';

interface UseFilterQueryOptions<T> {
  key: string;
  defaultValue: T;
  serialize?: (value: T) => string;
  deserialize?: (value: string) => T;
}

export function useFilterQuery<T>(options: UseFilterQueryOptions<T>) {
  const { key, defaultValue, serialize, deserialize } = options;
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const value = useMemo(() => {
    const param = searchParams.get(key);
    if (!param) return defaultValue;
    return deserialize ? deserialize(param) : (param as unknown as T);
  }, [searchParams, key, defaultValue, deserialize]);
  
  const setValue = useCallback((newValue: T) => {
    const params = new URLSearchParams(searchParams);
    
    if (newValue === defaultValue || newValue === undefined) {
      params.delete(key);
    } else {
      params.set(key, serialize ? serialize(newValue) : String(newValue));
    }
    
    router.push(`?${params.toString()}`, { shallow: true });
  }, [key, defaultValue, router, searchParams, serialize]);
  
  return [value, setValue] as const;
}

// Usage
function HistoryFilters() {
  const [period, setPeriod] = useFilterQuery({
    key: 'period',
    defaultValue: '30d',
  });
  
  const [status, setStatus] = useFilterQuery({
    key: 'status',
    defaultValue: 'all',
  });
  
  return (
    <div>
      <Select value={period} onChange={setPeriod}>
        <option value="7d">7 jours</option>
        <option value="30d">30 jours</option>
        <option value="90d">90 jours</option>
      </Select>
    </div>
  );
}
```

### Conservation Contexte Navigation

```typescript
// src/features/history/hooks/useHistoryNavigation.ts

export function useHistoryNavigation() {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  // Sauvegarder filtres avant navigation
  const navigateToDetail = (decisionId: string) => {
    // Stocker filtres actuels
    sessionStorage.setItem(
      'history-filters',
      JSON.stringify(Object.fromEntries(searchParams))
    );
    
    router.push(`/history/${decisionId}`);
  };
  
  // Restaurer filtres au retour
  const restoreFilters = () => {
    const saved = sessionStorage.getItem('history-filters');
    if (saved) {
      const filters = JSON.parse(saved);
      const params = new URLSearchParams(filters);
      router.push(`/history?${params.toString()}`);
    }
  };
  
  return { navigateToDetail, restoreFilters };
}
```

---

## 🏗️ Pattern 5 : Error Handling

### Stratégie de Retry

```typescript
// Configuration globale dans QueryClient
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        // Pas de retry sur erreurs client
        if (error.status >= 400 && error.status < 500) {
          return false;
        }
        // Max 3 retries sur erreurs serveur
        return failureCount < 3;
      },
      retryDelay: (attemptIndex) => 
        Math.min(1000 * 2 ** attemptIndex, 30000), // Exponential backoff
    },
  },
});
```

### Gestion Erreurs dans Composants

```typescript
// src/components/query/QueryErrorBoundary.tsx

import { QueryErrorResetBoundary } from '@tanstack/react-query';
import { ErrorBoundary } from 'react-error-boundary';

export function QueryErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary
          onReset={reset}
          fallbackRender={({ resetErrorBoundary, error }) => (
            <Alert severity="error">
              <AlertTitle>Erreur de chargement</AlertTitle>
              {error.message}
              <Button onClick={resetErrorBoundary}>
                Réessayer
              </Button>
            </Alert>
          )}
        >
          {children}
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}
```

### Hook avec Gestion Erreur

```typescript
// src/features/decisions/hooks/useDecision.ts

export function useDecision(id: string) {
  const { enqueueSnackbar } = useSnackbar();
  
  return useQuery({
    queryKey: queryKeys.detail(id),
    queryFn: () => decisionsApi.getById(id),
    
    meta: {
      // Message personnalisé par type d'erreur
      errorMessage: {
        404: 'Décision non trouvée',
        403: 'Accès non autorisé',
        default: 'Erreur lors du chargement',
      },
    },
    
    // Gestion erreur globale
    onError: (error: any) => {
      const message = 
        error.status === 404 
          ? 'Décision non trouvée'
          : 'Erreur lors du chargement';
      
      enqueueSnackbar(message, { variant: 'error' });
    },
  });
}
```

---

## 🏗️ Pattern 6 : Prefetching

### Prefetch au Hover

```typescript
// src/features/decisions/components/DecisionList.tsx

export function DecisionList() {
  const queryClient = useQueryClient();
  const { data: decisions } = useDecisions();
  
  const prefetchDecision = (id: string) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.detail(id),
      queryFn: () => decisionsApi.getById(id),
      staleTime: 60 * 1000,
    });
  };
  
  return (
    <List>
      {decisions?.map(decision => (
        <ListItem
          key={decision.id}
          onMouseEnter={() => prefetchDecision(decision.id)}
        >
          <DecisionCard decision={decision} />
        </ListItem>
      ))}
    </List>
  );
}
```

### Prefetch au Focus

```typescript
// Prefetch quand l'utilisateur revient sur l'app
function usePrefetchOnFocus() {
  const queryClient = useQueryClient();
  
  useEffect(() => {
    const handleFocus = () => {
      // Prefetch données importantes
      queryClient.prefetchQuery({
        queryKey: queryKeys.list({ status: 'pick' }),
        queryFn: () => decisionsApi.getAll({ status: 'pick' }),
      });
    };
    
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [queryClient]);
}
```

---

## 🏗️ Pattern 7 : Dependent Queries

### Query Dépendante

```typescript
// Query B dépend de Query A

function useDecisionWithGates(decisionId: string) {
  // Query 1 : Décision
  const { data: decision, isSuccess } = useQuery({
    queryKey: queryKeys.detail(decisionId),
    queryFn: () => decisionsApi.getById(decisionId),
  });
  
  // Query 2 : Gates (dépend de la décision)
  const { data: gates } = useQuery({
    queryKey: queryKeys.gates(decisionId),
    queryFn: () => gatesApi.getByDecisionId(decisionId),
    enabled: isSuccess, // Dépend de query 1
  });
  
  return { decision, gates };
}
```

### Parallel Queries

```typescript
// Queries indépendantes en parallèle

function useDashboardData() {
  const decisionsQuery = useQuery({
    queryKey: ['decisions', 'recent'],
    queryFn: () => decisionsApi.getRecent(),
  });
  
  const statsQuery = useQuery({
    queryKey: ['stats', 'summary'],
    queryFn: () => statsApi.getSummary(),
  });
  
  const userQuery = useQuery({
    queryKey: ['user', 'profile'],
    queryFn: () => userApi.getProfile(),
  });
  
  // Toutes en parallèle automatiquement
  return {
    decisions: decisionsQuery.data,
    stats: statsQuery.data,
    user: userQuery.data,
    isLoading: decisionsQuery.isLoading || 
               statsQuery.isLoading || 
               userQuery.isLoading,
  };
}
```

---

## 🧪 Testing Patterns

### Mock Service Worker (MSW)

```typescript
// tests/mocks/handlers.ts

import { rest } from 'msw';

export const handlers = [
  rest.get('/api/decisions', (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        data: mockDecisions,
        meta: { total: mockDecisions.length },
      })
    );
  }),
  
  rest.get('/api/decisions/:id', (req, res, ctx) => {
    const decision = mockDecisions.find(d => d.id === req.params.id);
    
    if (!decision) {
      return res(ctx.status(404));
    }
    
    return res(ctx.status(200), ctx.json({ data: decision }));
  }),
];
```

### Test Hook

```typescript
// src/features/decisions/hooks/useDecisions.test.ts

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe('useDecisions', () => {
  it('fetches decisions', async () => {
    const { result } = renderHook(
      () => useDecisions(),
      { wrapper: createWrapper() }
    );
    
    // État initial
    expect(result.current.isLoading).toBe(true);
    
    // Attendre résultat
    await waitFor(() => 
      expect(result.current.isSuccess).toBe(true)
    );
    
    // Vérifier données
    expect(result.current.data).toBeDefined();
  });
  
  it('caches results', async () => {
    const queryClient = new QueryClient();
    
    // Premier render
    const { result, rerender } = renderHook(
      () => useDecisions(),
      { wrapper: createWrapperWithClient(queryClient) }
    );
    
    await waitFor(() => 
      expect(result.current.isSuccess).toBe(true)
    );
    
    // Rerender (doit utiliser cache)
    rerender();
    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeDefined();
  });
});
```

---

## ⚠️ Anti-Patterns à Éviter

### ❌ Mauvais : Pas de query key stable

```typescript
// ❌ Query key change à chaque render
useQuery({
  queryKey: ['decisions', { filters }], // Objet non stable
  queryFn: fetchDecisions,
});
```

### ✅ Bon : Query key stable

```typescript
// ✅ Query key stable
useQuery({
  queryKey: ['decisions', filters.status, filters.date], // Valeurs primitives
  queryFn: () => fetchDecisions(filters),
});
```

### ❌ Mauvais : Fetch dans useEffect

```typescript
// ❌ Pas de cache, pas de gestion erreur
function Component() {
  const [data, setData] = useState();
  
  useEffect(() => {
    fetch('/api/data')
      .then(r => r.json())
      .then(setData);
  }, []);
}
```

### ✅ Bon : React Query

```typescript
// ✅ Cache, retry, error handling intégrés
function Component() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['data'],
    queryFn: () => fetch('/api/data').then(r => r.json()),
  });
}
```

### ❌ Mauvais : Invalidation trop large

```typescript
// ❌ Invalide TOUT
queryClient.invalidateQueries();
```

### ✅ Bon : Invalidation ciblée

```typescript
// ✅ Invalide uniquement les decisions
queryClient.invalidateQueries({ queryKey: ['decisions'] });

// ✅ Invalide liste mais pas détail
queryClient.invalidateQueries({ 
  queryKey: ['decisions', 'list'] 
});
```

---

## 📊 Performance Checklist

- [ ] `staleTime` configuré selon fréquence changement données
- [ ] `gcTime` > `staleTime` pour éviter garbage collection prématurée
- [ ] `placeholderData: keepPreviousData` pour UX fluide
- [ ] `refetchOnWindowFocus: false` pour données stables
- [ ] `select` pour transformer données (éviter re-renders)
- [ ] Pagination pour listes > 50 items
- [ ] Prefetch pour navigation prévisible

---

## 📚 Références

- **Story 2.1** : Historique avec pagination et filtres
- **Story 2.2** : Détail avec dependent queries
- **Story 2.3** : Vue observateur avec cache
- **React Query Docs** : https://tanstack.com/query/latest
- **Code Review** : `docs/process/code-review-checklist.md#performance`

---

*Document créé par Elena - 2026-02-14*  
*Review par Charlie - 2026-02-14*  
*Basé sur les learnings des Stories 2.1-2.4*
