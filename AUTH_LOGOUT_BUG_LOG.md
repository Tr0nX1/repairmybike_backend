# Auth Logout & Refresh Token Investigation Log
Date: 2026-08-31
Scope: repairmybike_backend · repairmybike-admin · repairmybike_frontend
Status: Investigation complete & Proposed Fix ready (no code committed yet).

---

## TASK A — Production FCM Status Check

**Command:** `railway logs --lines 200`
**Log Output:**
```
WARNING FCM: Firebase app not initialized. Skipping.
```

**Status:** **NO**, Firebase is NOT initialized in the current production deployment.
**Reason:** The `FIREBASE_CREDENTIALS_JSON` environment variable has not yet been set in Railway's environment dashboard. Once added, Railway will redeploy and initializing log `[OK] Firebase Admin SDK initialized` will appear.

---

## TASK B — Auth Refresh & Logout Bug Investigation

### STEP 1 — Auth & Token Architecture Analysis

1. **Authentication Backend:**
   - System does **NOT** use Django REST Framework `Simple JWT`.
   - Primary auth is **Descope OTP / JWT** for users, staff, and admins.
   - Secondary auth is **PasswordSessionAuthentication** for local staff/admin password logins (`UserSession` table in DB with UUID session tokens).
   - In `settings.py`, `REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES']` includes:
     - `PasswordSessionAuthentication`
     - `DescopeAuthentication`
     - `DescopeSessionAuthentication`
     - `GuestAuthentication`

2. **Token Lifetimes:**
   - Descope handles JWT issuance. Default Descope JWT access tokens expire in 1 hour.
   - In `UserSession` model, session token records default to `expires_at = now + 8 hours`.
   - Token refresh endpoint: `POST /api/auth/token/refresh/` (`RefreshTokenView` in `authentication/views.py`).

---

### STEP 2 — Root Cause Analysis & Empirical Evidence

The repeating 401 log pattern seen in Railway production logs:
```
WARNING Unauthorized: /api/auth/token/refresh/  (x10 in a row)
WARNING Unauthorized: /api/subscriptions/plans/
WARNING Unauthorized: /api/services/services/
WARNING Unauthorized: /api/cms/banners/
WARNING Unauthorized: /api/spare-parts/cart/
WARNING Unauthorized: /api/services/service-categories/
```

**Root Cause 1: Parameter Key Mismatch in Admin Panel (`repairmybike-admin`)**
- **File:** `repairmybike-admin/lib/api-client.ts` (lines 43-45)
  ```typescript
  const response = await axios.post(`${baseURL}/api/auth/token/refresh/`, {
    refresh: refreshToken, // <--- ERROR: key is 'refresh'
  });
  ```
- **File:** `repairmybike_backend/authentication/views.py` (line 602)
  ```python
  refresh_token = request.data.get('refresh_token') # <--- Backend expects 'refresh_token'
  if not refresh_token:
      return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
  ```
- **Evidence:** `repairmybike-admin` sends `{ refresh: refreshToken }` (SimpleJWT style), but the Django backend `RefreshTokenView` strictly looks for `request.data.get('refresh_token')`. Because `refresh_token` is `None`, the backend rejects every refresh attempt from the admin panel with a `400/401` error.

**Root Cause 2: Un-deduplicated Concurrent Refresh Calls in Admin Interceptor**
- **File:** `repairmybike-admin/lib/api-client.ts` (lines 36-60)
- When a page loads or tab gains focus, React Query fires multiple parallel API requests (`/api/subscriptions/plans/`, `/api/services/`, etc.).
- When the session expires, ALL parallel requests receive a `401` at the exact same moment.
- `api-client.ts` lacks a shared in-flight refresh promise or mutex lock. As a result, 5 to 10 parallel `POST /api/auth/token/refresh/` requests are dispatched simultaneously.
- Even when the payload key is fixed, Descope rotates refresh tokens upon use. Race condition: Request #1 succeeds and invalidates `refresh_token_1`; Request #2 (sent in parallel) submits `refresh_token_1`, which Descope rejects as already-used. This causes a hard 401 logout.

---

### STEP 3 — Proposed Minimal Fix

#### Fix Part 1: Backend `authentication/views.py`
Make `RefreshTokenView` accept both `refresh_token` and `refresh` keys for backwards/frontend compatibility.

```python
# repairmybike_backend/authentication/views.py
class RefreshTokenView(APIView):
    """Handle token refresh using Descope refresh token"""
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        refresh_token = request.data.get('refresh_token') or request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
```

#### Fix Part 2: Admin Panel `repairmybike-admin/lib/api-client.ts`
1. Fix payload key to `{ refresh_token: refreshToken }`.
2. Implement single in-flight `refreshTokenPromise` to lock and deduplicate concurrent refresh requests.

```typescript
// repairmybike-admin/lib/api-client.ts
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Inside response interceptor:
if (error.response?.status === 401 && !originalRequest._retry) {
  if (isRefreshing) {
    return new Promise((resolve, reject) => {
      failedQueue.push({ resolve, reject });
    })
      .then((token) => {
        originalRequest.headers['Authorization'] = `Bearer ${token}`;
        originalRequest.headers['X-Session-Token'] = token;
        return apiClient(originalRequest);
      })
      .catch((err) => Promise.reject(err));
  }

  originalRequest._retry = true;
  isRefreshing = true;
  const refreshToken = localStorage.getItem('rmb_refresh');

  if (refreshToken && refreshToken !== 'null') {
    try {
      const response = await axios.post(`${baseURL}/api/auth/token/refresh/`, {
        refresh_token: refreshToken, // Fixed key name
      });

      const token = response.data.data?.token || response.data.token || response.data.session_token;
      const newRefreshToken = response.data.data?.refresh_token || response.data.refresh_token;

      if (token) {
        localStorage.setItem('rmb_token', token);
        if (newRefreshToken) {
          localStorage.setItem('rmb_refresh', newRefreshToken);
        }
        document.cookie = `rmb_token=${token}; path=/; max-age=86400; SameSite=Lax`;
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;

        processQueue(null, token);
        isRefreshing = false;

        originalRequest.headers['Authorization'] = `Bearer ${token}`;
        return apiClient(originalRequest);
      }
    } catch (refreshError) {
      processQueue(refreshError, null);
      isRefreshing = false;
    }
  } else {
    isRefreshing = false;
  }
  // Logout cleanup...
}
```

---

## STEP 4 — Summary & Next Steps

- **Branch Created:** `fix/auth-logout-bug` in both `repairmybike_backend` and `repairmybike-admin`.
- **Files to modify:**
  1. `repairmybike_backend/authentication/views.py`
  2. `repairmybike-admin/lib/api-client.ts`
- **Awaiting User Review:** Ready to apply diff once approved.
