# RBAC Patterns Guide

**Version** : 1.0  
**Date** : 2026-02-14  
**Owner** : Charlie (Senior Dev)  
**Source** : RETRO-2-002 - Epic 2 Rétrospective  
**Scope** : MVP Roles - user, ops_admin, support, observer

---

## 🎯 Objectif

Ce document définit les patterns d'authentification et d'autorisation (RBAC) établis lors des Stories 2.3 et 2.4. Il garantit une implémentation cohérente de la sécurité dans Epic 3 et au-delà.

---

## 📋 Architecture RBAC

### Modèle de Rôles (MVP)

```
┌─────────────────────────────────────────┐
│           AUTHENTIFICATION              │
│         (NextAuth + JWT)                │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│            RBAC MIDDLEWARE              │
│       (withRBAC HOC / Middleware)       │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌────────┐   ┌──────────┐   ┌──────────┐
│  USER  │   │OPS_ADMIN │   │ SUPPORT  │
│(default│   │(operator)│   │ (helpdesk│
│  role) │   │          │   │   role)  │
└────────┘   └──────────┘   └──────────┘
    │
    ▼
┌──────────┐
│ OBSERVER │
│(readonly │
│   role)  │
└──────────┘
```

### Hiérarchie des Rôles

| Rôle | Niveau | Description | Permissions |
|------|--------|-------------|-------------|
| `observer` | 0 | Lecture seule anonymisée | Voir décisions (anonymisé), audits |
| `user` | 1 | Utilisateur standard | Voir ses propres décisions, historique |
| `support` | 2 | Support client | Voir toutes les décisions, timelines |
| `ops_admin` | 3 | Opérateur système | + Gestion runs, qualité data, fallback |
| `admin` | 4 | Administrateur | + Gestion policy, utilisateurs (futur) |

**Règle** : Un rôle hérite des permissions des rôles inférieurs.

---

## 🔐 Pattern 1 : withRBAC Middleware

**Fichier** : `src/lib/auth/withRBAC.ts`

### Interface

```typescript
type Role = 'user' | 'ops_admin' | 'support' | 'observer';

interface WithRBACOptions {
  allowedRoles: Role[];
  requireOwnership?: boolean;
  resourceType?: 'decision' | 'user' | 'system';
}

function withRBAC<T extends ApiHandler>(
  handler: T,
  options: WithRBACOptions
): T;
```

### Usage API Routes

```typescript
// ✅ Bon - Protection API avec RBAC
import { withRBAC } from '@/lib/auth/withRBAC';

// Route accessible aux ops_admin uniquement
export const GET = withRBAC(
  async (req: NextRequest) => {
    const runs = await getRuns();
    return Response.json({ data: runs });
  },
  {
    allowedRoles: ['ops_admin'],
    resourceType: 'system',
  }
);

// Route accessible à user ET ops_admin
export const POST = withRBAC(
  async (req: NextRequest) => {
    const decision = await createDecision(req.body);
    return Response.json({ data: decision });
  },
  {
    allowedRoles: ['user', 'ops_admin'],
    requireOwnership: true,
    resourceType: 'decision',
  }
);
```

### Implémentation

```typescript
// src/lib/auth/withRBAC.ts
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth/auth-options';

export function withRBAC<T extends ApiHandler>(
  handler: T,
  options: WithRBACOptions
) {
  return async (req: NextRequest, ...args: any[]) => {
    // 1. Authentification
    const session = await getServerSession(authOptions);
    
    if (!session?.user) {
      return NextResponse.json(
        { error: { code: 'UNAUTHORIZED', message: 'Authentication required' } },
        { status: 401 }
      );
    }
    
    // 2. Vérification rôle
    const userRole = session.user.role as Role;
    
    if (!options.allowedRoles.includes(userRole)) {
      // Audit log
      auditLog({
        action: 'ACCESS_DENIED',
        userId: session.user.id,
        resource: req.url,
        requiredRoles: options.allowedRoles,
        userRole,
        traceId: req.headers.get('x-trace-id'),
      });
      
      return NextResponse.json(
        { error: { code: 'FORBIDDEN', message: 'Insufficient permissions' } },
        { status: 403 }
      );
    }
    
    // 3. Vérification ownership (si requis)
    if (options.requireOwnership && options.resourceType) {
      const hasOwnership = await checkOwnership(
        req,
        session.user.id,
        options.resourceType
      );
      
      if (!hasOwnership) {
        auditLog({
          action: 'OWNERSHIP_DENIED',
          userId: session.user.id,
          resource: req.url,
          traceId: req.headers.get('x-trace-id'),
        });
        
        return NextResponse.json(
          { error: { code: 'FORBIDDEN', message: 'Resource access denied' } },
          { status: 403 }
        );
      }
    }
    
    // 4. Injection user dans la requête
    (req as any).user = session.user;
    
    // 5. Exécution handler
    return handler(req, ...args);
  };
}

async function checkOwnership(
  req: NextRequest,
  userId: string,
  resourceType: string
): Promise<boolean> {
  // Logique de vérification ownership selon resourceType
  // Exemple pour decisions : vérifier que la décision appartient à l'user
  const decisionId = req.nextUrl.searchParams.get('id');
  if (!decisionId) return false;
  
  const decision = await getDecisionById(decisionId);
  return decision?.userId === userId;
}
```

---

## 🔐 Pattern 2 : Client-Side Role Check

**Fichier** : `src/lib/auth/useRole.ts`

### Hook useRole

```typescript
// src/lib/auth/useRole.ts
import { useSession } from 'next-auth/react';

export function useRole() {
  const { data: session } = useSession();
  
  return {
    role: session?.user?.role as Role | undefined,
    isAuthenticated: !!session?.user,
    isRole: (roles: Role[]) => roles.includes(session?.user?.role as Role),
    hasMinRole: (minRole: Role) => {
      const roleHierarchy = ['observer', 'user', 'support', 'ops_admin'];
      const userLevel = roleHierarchy.indexOf(session?.user?.role as Role);
      const minLevel = roleHierarchy.indexOf(minRole);
      return userLevel >= minLevel;
    },
  };
}
```

### Usage Composants

```typescript
// ✅ Bon - Conditionnel basé sur le rôle
import { useRole } from '@/lib/auth/useRole';

function DecisionCard({ decision }: { decision: Decision }) {
  const { isRole } = useRole();
  
  return (
    <Card>
      <CardContent>
        <Typography>{decision.matchName}</Typography>
        
        {/* Visible uniquement pour support/ops_admin */}
        {isRole(['support', 'ops_admin']) && (
          <AuditInfo decision={decision} />
        )}
        
        {/* Visible uniquement pour ops_admin */}
        {isRole(['ops_admin']) && (
          <AdminActions decision={decision} />
        )}
      </CardContent>
    </Card>
  );
}
```

### Composant Protected

```typescript
// src/components/auth/Protected.tsx
import { useRole } from '@/lib/auth/useRole';
import { Alert } from '@mui/material';

interface ProtectedProps {
  allowedRoles: Role[];
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function Protected({ allowedRoles, children, fallback }: ProtectedProps) {
  const { isRole, isAuthenticated } = useRole();
  
  if (!isAuthenticated) {
    return fallback || (
      <Alert severity="warning">Connexion requise</Alert>
    );
  }
  
  if (!isRole(allowedRoles)) {
    return fallback || (
      <Alert severity="error">Permissions insuffisantes</Alert>
    );
  }
  
  return <>{children}</>;
}

// Usage
<Protected allowedRoles={['ops_admin']}>
  <OperationsDashboard />
</Protected>
```

---

## 🔐 Pattern 3 : Data Isolation

### Principe

**Règle d'or** : Le backend doit TOUJOURS filtrer par `userId` pour les requêtes des rôles `user` et `observer`.

### Repository Pattern

```typescript
// src/lib/db/repositories/decisions.repository.ts

interface GetDecisionsOptions {
  userId?: string;
  role: Role;
  filters?: DecisionFilters;
  pagination?: PaginationParams;
}

export async function getDecisions(options: GetDecisionsOptions) {
  const { userId, role, filters, pagination } = options;
  
  let query = db.select().from(decisions);
  
  // Data isolation selon le rôle
  switch (role) {
    case 'user':
      // User ne voit que SES propres décisions
      query = query.where(eq(decisions.userId, userId!));
      break;
      
    case 'observer':
      // Observer voit tout mais ANONYMISÉ
      // Pas de filtre userId, mais sélection champs limitée
      break;
      
    case 'support':
    case 'ops_admin':
      // Support et ops voient tout (mais pas anonymisé)
      // Optionnel : filtre userId si spécifié dans filters
      if (filters?.userId) {
        query = query.where(eq(decisions.userId, filters.userId));
      }
      break;
  }
  
  // Application autres filtres
  if (filters?.status) {
    query = query.where(eq(decisions.status, filters.status));
  }
  
  // Pagination
  if (pagination) {
    query = query
      .limit(pagination.limit)
      .offset(pagination.offset);
  }
  
  const results = await query;
  
  // Anonymisation pour observer
  if (role === 'observer') {
    return results.map(anonymizeDecision);
  }
  
  return results;
}

function anonymizeDecision(decision: Decision): AnonymizedDecision {
  return {
    id: decision.id,
    matchId: decision.matchId,
    status: decision.status,
    confidence: decision.confidence,
    createdAt: decision.createdAt,
    // Pas de userId, pas de détails personnels
  };
}
```

### Service Layer

```typescript
// src/server/services/decisions.service.ts

export async function getDecisionsForUser(
  userId: string,
  role: Role,
  filters?: DecisionFilters
) {
  // Logging pour audit
  logger.info({
    action: 'GET_DECISIONS',
    userId,
    role,
    filters,
  });
  
  return getDecisions({
    userId,
    role,
    filters,
    pagination: { limit: 50, offset: 0 },
  });
}
```

---

## 🔐 Pattern 4 : Observer Role Spécifique

### Vue Anonymisée

L'observer a un accès spécial : lecture de toutes les décisions mais **sans identification utilisateur**.

```typescript
// src/features/observer/components/ObserverView.tsx

export function ObserverView() {
  const { role } = useRole();
  
  // Vérification rôle
  if (role !== 'observer') {
    return <AccessDenied />;
  }
  
  const { data: decisions } = useObserverDecisions();
  
  return (
    <DecisionList>
      {decisions?.map(decision => (
        <DecisionCard
          key={decision.id}
          decision={decision}
          // Pas d'info utilisateur affichée
          showUserInfo={false}
        />
      ))}
    </DecisionList>
  );
}

// Hook spécifique observer
function useObserverDecisions() {
  return useQuery({
    queryKey: ['observer', 'decisions'],
    queryFn: () => fetch('/api/observer/decisions').then(r => r.json()),
    // Pas de cache agressif pour données sensibles
    staleTime: 5 * 60 * 1000,
  });
}
```

### API Route Observer

```typescript
// src/app/api/observer/decisions/route.ts
import { withRBAC } from '@/lib/auth/withRBAC';

export const GET = withRBAC(
  async (req) => {
    // Retourne TOUTES les décisions mais anonymisées
    const decisions = await getDecisions({
      role: 'observer',
    });
    
    return Response.json({ data: decisions });
  },
  {
    allowedRoles: ['observer', 'support', 'ops_admin'],
    // Observer peut accéder, mais aussi support/ops
    resourceType: 'system',
  }
);
```

---

## 🛡️ Pattern 5 : Audit Logging

### Configuration

Toutes les actions RBAC critiques doivent être loggées :

```typescript
// src/lib/observability/audit.ts

interface AuditEvent {
  action: 'ACCESS_GRANTED' | 'ACCESS_DENIED' | 'OWNERSHIP_DENIED';
  userId: string;
  resource: string;
  method?: string;
  userRole: Role;
  requiredRoles?: Role[];
  traceId: string | null;
  timestamp: string;
}

export function auditLog(event: Omit<AuditEvent, 'timestamp'>) {
  const fullEvent: AuditEvent = {
    ...event,
    timestamp: new Date().toISOString(),
  };
  
  // Log structuré
  logger.info({
    type: 'AUDIT',
    ...fullEvent,
  });
  
  // Stockage en base pour reporting
  storeAuditEvent(fullEvent).catch(console.error);
}
```

### Événements à Logger

| Événement | Quand | Données |
|-----------|-------|---------|
| `ACCESS_GRANTED` | Accès autorisé | userId, resource, role |
| `ACCESS_DENIED` | Accès refusé (403) | userId, resource, requiredRoles, userRole |
| `OWNERSHIP_DENIED` | Ownership check fail | userId, resource, resourceId |
| `ROLE_CHANGED` | Changement rôle | userId, oldRole, newRole |

---

## ⚠️ Anti-Patterns à Éviter

### ❌ Mauvais : Vérification côté client uniquement

```typescript
// ❌ DANGERUX - Facilement contournable
function AdminPanel() {
  const { role } = useRole();
  
  if (role !== 'ops_admin') {
    return null; // Contournable en modifiant le state
  }
  
  return <SensitiveData />;
}
```

### ✅ Bon : Vérification côté serveur

```typescript
// ✅ SÉCURISÉ - Impossible à contourner
export const GET = withRBAC(
  async (req) => {
    return Response.json({ data: sensitiveData });
  },
  { allowedRoles: ['ops_admin'] }
);
```

### ❌ Mauvais : Pas de data isolation

```typescript
// ❌ FUITE DE DONNÉES
export async function getDecisions() {
  return db.select().from(decisions); // Tout le monde voit tout !
}
```

### ✅ Bon : Data isolation explicite

```typescript
// ✅ SÉCURISÉ
export async function getDecisions(options: GetDecisionsOptions) {
  if (options.role === 'user') {
    return db.select()
      .from(decisions)
      .where(eq(decisions.userId, options.userId));
  }
  // ... autres cas
}
```

### ❌ Mauvais : Information leakage dans erreurs

```typescript
// ❌ FUITE D'INFO
return Response.json(
  { error: `User ${userId} not found in database` },
  { status: 404 }
);
```

### ✅ Bon : Messages génériques

```typescript
// ✅ SÉCURISÉ
return Response.json(
  { error: { code: 'NOT_FOUND', message: 'Resource not found' } },
  { status: 404 }
);
```

---

## 🧪 Testing RBAC

### Tests Unitaires

```typescript
// src/lib/auth/withRBAC.test.ts

describe('withRBAC', () => {
  it('allows access for authorized role', async () => {
    const handler = jest.fn(() => Response.json({ success: true }));
    const protectedHandler = withRBAC(handler, {
      allowedRoles: ['user'],
    });
    
    const req = createMockRequest({ role: 'user' });
    const res = await protectedHandler(req);
    
    expect(handler).toHaveBeenCalled();
    expect(res.status).toBe(200);
  });
  
  it('denies access for unauthorized role', async () => {
    const handler = jest.fn();
    const protectedHandler = withRBAC(handler, {
      allowedRoles: ['ops_admin'],
    });
    
    const req = createMockRequest({ role: 'user' });
    const res = await protectedHandler(req);
    
    expect(handler).not.toHaveBeenCalled();
    expect(res.status).toBe(403);
  });
  
  it('denies access for unauthenticated user', async () => {
    const handler = jest.fn();
    const protectedHandler = withRBAC(handler, {
      allowedRoles: ['user'],
    });
    
    const req = createMockRequest(null); // Pas de session
    const res = await protectedHandler(req);
    
    expect(res.status).toBe(401);
  });
});
```

### Tests E2E

```typescript
// tests/e2e/rbac.spec.ts

test('observer cannot see user info', async ({ page }) => {
  // Login as observer
  await login(page, 'observer');
  
  // Navigate to decisions
  await page.goto('/observer/decisions');
  
  // Verify no user info visible
  await expect(page.locator('[data-testid="user-info"]')).toHaveCount(0);
});

test('user cannot access admin routes', async ({ page }) => {
  await login(page, 'user');
  
  // Try to access admin route
  const response = await page.goto('/api/admin/runs');
  
  expect(response?.status()).toBe(403);
});
```

---

## 📊 Matrice des Permissions

| Resource | Action | user | observer | support | ops_admin |
|----------|--------|------|----------|---------|-----------|
| **Decisions** | Read own | ✅ | ❌ | ✅ | ✅ |
| | Read all | ❌ | ✅ (anonymized) | ✅ | ✅ |
| | Create | ✅ | ❌ | ❌ | ✅ |
| | Update | ❌ | ❌ | ❌ | ✅ |
| **User Profile** | Read own | ✅ | ❌ | ❌ | ✅ |
| | Read others | ❌ | ❌ | ❌ | ✅ |
| **Runs** | Read | ❌ | ❌ | ✅ | ✅ |
| | Execute | ❌ | ❌ | ❌ | ✅ |
| **Audit Logs** | Read | ❌ | ✅ | ✅ | ✅ |
| **Policy** | Read | ✅ | ❌ | ✅ | ✅ |
| | Update | ❌ | ❌ | ❌ | ✅ |

---

## 🔧 Configuration NextAuth

```typescript
// src/lib/auth/auth-options.ts

export const authOptions: NextAuthOptions = {
  // ... autres config
  
  callbacks: {
    async session({ session, token }) {
      if (token.sub && session.user) {
        session.user.id = token.sub;
        
        // Récupération rôle depuis DB
        const dbUser = await getUserById(token.sub);
        session.user.role = dbUser?.role || 'user';
      }
      return session;
    },
    
    async jwt({ token, user }) {
      if (user) {
        token.role = user.role;
      }
      return token;
    },
  },
  
  events: {
    async signIn({ user }) {
      auditLog({
        action: 'SIGN_IN',
        userId: user.id,
        resource: '/auth/signin',
        userRole: user.role as Role,
        traceId: null,
      });
    },
  },
};
```

---

## 📚 Références

- **Story 2.3** : Vue observateur avec RBAC
- **Story 2.4** : Garde-fou et permissions
- **Architecture** : `docs/architecture/architecture.md#authentication`
- **Code Review** : `docs/process/code-review-checklist.md#security`

---

*Document créé par Charlie - 2026-02-14*  
*Basé sur les learnings des Stories 2.3-2.4*  
*À jour avec l'implémentation NextAuth + RBAC*
