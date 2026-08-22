# RepairMyBike Backend Fix Log

**Date:** 2026-08-22

---

## Step 0: Branch Setup & Working Tree Verification
- Verified `git status` on base branch `scale_rmb_main`.
- Stashed temporary logs and untracked diagnostic scripts (`git stash --include-untracked`) to ensure clean working tree.
- Created and checked out new branch: `fix/security-permissions`.
- Active branch confirmed: `fix/security-permissions`.

---

## Step 1: Fix Subscriptions PlanViewSet (P0)
- File modified: `subscriptions/views.py`.
- Removed class-level `permission_classes = [permissions.AllowAny]`.
- Implemented `get_permissions(self)` override in `PlanViewSet`:
  - `list`, `retrieve` (read actions) return `[permissions.AllowAny()]`.
  - All write actions (`create`, `update`, `partial_update`, `destroy`, `add_benefit`, `remove_benefit`, `update_benefit`) return `[permissions.IsAuthenticated(), permissions.IsAdminUser()]`.

---

## Step 2: Fix Payments Razorpay Endpoints (P0)
- File modified: `payments/views.py`.
- Updated `PaymentViewSet.get_permissions(self)`:
  - `list`, `retrieve` actions remain `[permissions.IsAuthenticated(), permissions.IsAdminUser()]`.
  - `create_razorpay_order` and `verify_razorpay_payment` now return `[permissions.IsAuthenticated()]` instead of unauthenticated `[]`.
- Security note: UNCLEAR — needs manual check on whether Razorpay order creation should enforce explicit booking ownership check (`booking.customer.phone == user.phone_number`) when gateway is enabled in production. Currently defaulted to `IsAuthenticated`.

---

## Step 3: Impact Check
- **Subscriptions `PlanViewSet` (`/api/subscriptions/plans/`)**:
  - `getPlans()` in Flutter (`repairmybike_frontend/lib/data/subscription_api.dart`) and Next.js Admin Panel (`repairmybike-admin/hooks/usePlans.ts`) uses `GET`, which maps to `list`/`retrieve` actions (`permissions.AllowAny()`). Public browsing remains functional.
  - Admin panel write operations (`create`, `update`, `destroy`, `add_benefit`, `update_benefit`, `remove_benefit`) send `Authorization: Bearer <token>` headers via `api-client.ts`, matching `[permissions.IsAuthenticated(), permissions.IsAdminUser()]`.
- **Payments Razorpay Endpoints (`/api/payments/payments/razorpay/`)**:
  - `create_razorpay_order` and `verify_razorpay_payment` require `IsAuthenticated`.
  - In `repairmybike_frontend/lib/data/booking_api.dart`, client code comments document attaching Bearer session tokens for payment requests.
  - Next.js Admin Panel queries `/api/payments/payments/` via `usePayments.ts` with admin session headers.
- **Django System Verification**:
  - Executed `python -X utf8 manage.py check`: `System check identified no issues (0 silenced)`.

---

## Step 4: Summary of Changes
- **Target Branch**: `fix/security-permissions` (derived from `scale_rmb_main`).
- **File 1 (`subscriptions/views.py`)**:
  - Removed class-level `permission_classes = [permissions.AllowAny]`.
  - Added `get_permissions(self)` to enforce `AllowAny` for read operations (`list`, `retrieve`) while restricting all write operations (`create`, `update`, `partial_update`, `destroy`, `add_benefit`, `update_benefit`, `remove_benefit`) to authenticated admin users (`[permissions.IsAuthenticated(), permissions.IsAdminUser()]`).
- **File 2 (`payments/views.py`)**:
  - Updated `PaymentViewSet.get_permissions(self)` fallback from `return []` to `return [permissions.IsAuthenticated()]` so `create_razorpay_order` and `verify_razorpay_payment` endpoints are protected from unauthenticated access.
- **Commit Status**: Changes are left uncommitted and unstaged pending user review.




