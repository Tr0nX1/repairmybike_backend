# RepairMyBike Backend Feature Log - Add Service to Booking

**Date:** 2026-08-22
**Branch:** `feat/booking-add-service`

---

## Step 0: Branch Verification
- Branch verified: `feat/booking-add-service`.
- Working tree confirmed clean.

---

## Step 1: add-part Pattern Analysis

- **Location**: `StaffBookingViewSet` in `staff/views.py` (`@action(detail=True, methods=['post'], url_path='add-part')`).
- **URL Route**: `POST /api/staff/bookings/{id}/add-part/` (Registered under `staff-booking` router).
- **Permissions**: Class-level `permission_classes = [permissions.IsAuthenticated, IsStaffAuthenticated]` (requires staff or manager/admin authentication).
- **State Validation**:
  - Uses `@transaction.atomic` and `Booking.objects.select_for_update().get(pk=pk)`.
  - Checks if `booking.booking_status in ['completed', 'cancelled']`. If terminal, returns 400 Bad Request with code `'BOOKING_TERMINAL'`.
- **Item & Pricing Validation**:
  - Validates `spare_part_id` / `part_id` existence (`SparePart.DoesNotExist` returns 404).
  - Checks `part.in_stock` and `part.stock_qty >= quantity` (returns 400 if out of stock).
  - Locks unit price from `part.sale_price`.
- **Data Mutation & Total Calculation**:
  - Creates `BookingPart(booking=booking, spare_part=part, unit_price=locked_price, quantity=quantity, approval_status='pending')`.
  - Increments `booking.total_amount += booking_part.total_price`.
  - Saves booking with `update_fields=['total_amount', 'updated_at']`.
- **Activity Logging & Response**:
  - Creates `ActivityLog` entries (`part_added` and `price_locked`).
  - Returns `Response({'error': False, 'message': '...', 'data': BookingDetailSerializer(booking).data})`.
- **Service Data Shape & Pricing Context**:
  - `BookingService` model (`bookings/models.py`) links `booking`, `service`, and `price`.
  - Service price is determined by `ServicePricing` model (`services/models.py`) for the specific `(service_id, booking.vehicle_model_id)` combination.

---

## Step 2: Proposed Design

- **Method**: `POST`
- **URL Path**: `/api/staff/bookings/{id}/add-service/`
- **Decorator**: `@action(detail=True, methods=['post'], url_path='add-service')` on `StaffBookingViewSet` in `staff/views.py`.
- **Permissions**: Inherited from `StaffBookingViewSet` (`[permissions.IsAuthenticated, IsStaffAuthenticated]`).
- **Request Body**:
  ```json
  {
    "service_id": 5,
    "custom_price": 500.00
  }
  ```
  *(Note: `service_id` is required; `custom_price` is optional to allow staff price override if necessary, defaulting to model-specific `ServicePricing` lookup).*

- **Execution Flow**:
  1. Wrap action in `@transaction.atomic`.
  2. Perform `Booking.objects.select_for_update().get(pk=pk)`.
  3. Validate booking terminal state (`booking_status in ['completed', 'cancelled']`). Return 400 `BOOKING_TERMINAL` if terminal.
  4. Lookup `Service.objects.get(id=service_id)`. Return 404 if service does not exist.
  5. Check if service is already attached to this booking (`BookingService.objects.filter(booking=booking, service=service).exists()`). If so, return 400 `SERVICE_ALREADY_ADDED`.
  6. Determine pricing:
     - If `custom_price` passed, validate & use it.
     - Else, lookup `ServicePricing.objects.get(service=service, vehicle_model=booking.vehicle_model)`.
     - If pricing record not found, return 400 `'Service pricing not found for this vehicle model'`.
  7. Create `BookingService.objects.create(booking=booking, service=service, price=service_price)`.
  8. Increment `booking.total_amount += service_price` and save booking.
  9. Record `ActivityLog` (`action_type='service_added'`).
  10. Return `Response({'error': False, 'message': 'Service added successfully', 'data': BookingDetailSerializer(booking).data})`.

---

## Step 3 & Step 4: Implementation & Impact Check
- **Implementation**:
  - Implemented `add_service` action in `StaffBookingViewSet` (`staff/views.py`).
  - Added imports for `BookingService`, `Service`, `ServicePricing`, and `InvalidOperation`.
  - Added dedicated unit tests in `bookings/tests/test_services_add.py`.
- **Impact Assessment**:
  - Purely additive endpoint (`POST /api/staff/bookings/{id}/add-service/`).
  - Zero breaking changes to existing endpoints or mobile/admin callers.
  - Django system check: `System check identified no issues (0 silenced)`.

---

## Step 5: Summary
- **Branch**: `feat/booking-add-service`.
- **New Endpoint**: `POST /api/staff/bookings/{id}/add-service/`.
- **Files Modified/Created**:
  - `staff/views.py` (Added `add_service` action method).
  - `bookings/tests/test_services_add.py` (New unit test suite).
  - `FIX_LOG.md` (Execution step log).
- **Commit Status**: Changes left uncommitted and unstaged pending user review.

---

## Staff Role Investigation

### 1. Custom User Model & Role Fields (`authentication/models.py`)
The custom `User` model inherits from `AbstractUser` (`class User(AbstractUser):`). It does **not** use a `role` CharField with choices. Instead, user roles are defined via Boolean flags:

```python
# Inherited from AbstractUser:
is_staff = models.BooleanField(default=False)
is_superuser = models.BooleanField(default=False)
is_active = models.BooleanField(default=True)

# Custom field added on User:
is_manager = models.BooleanField(default=False)
```

No enum/choices array exists on the `User` model; roles are evaluated by checking these boolean flags (e.g., `is_staff`, `is_manager`, `is_superuser`).

### 2. `IsStaffAuthenticated` Permission (`staff/permissions.py`)
Definition verbatim:

```python
class IsStaffAuthenticated(permissions.BasePermission):
    """
    Authenticated user must be staff or superuser.
    Replaces API-key gate with identity-based authorization.
    """

    message = 'Staff access requires an authenticated staff/admin user'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(
            user 
            and user.is_authenticated 
            and (user.is_staff or user.is_superuser or getattr(user, 'is_manager', False))
        )
```

- **Behavior**: `IsStaffAuthenticated` grants access if the authenticated user has `is_staff=True`, `is_superuser=True`, or `is_manager=True`. It treats all staff levels equally at the gate.
- **Role Differentiation**: Specific distinction between mechanic-level staff and manager/admin is handled inside viewsets (e.g., `StaffBookingViewSet.get_queryset()`), where `is_superuser` or `is_manager` yields all bookings while regular staff are filtered to `qs.filter(mechanic=user)`.

### 3. `StaffDirectory` Model (`authentication/models.py`)
The project includes a separate pre-provisioning model `StaffDirectory`:

```python
class StaffDirectory(models.Model):
    """Pre-provisioned staff directory to allow login without manual registration."""
    identifier = models.CharField(max_length=255, unique=True)  # email or phone
    name = models.CharField(max_length=255, blank=True, null=True)
    employee_id = models.CharField(max_length=100, blank=True, null=True)
    role = models.CharField(max_length=100, blank=True, null=True)
    photo = models.ImageField(
        upload_to='staff/photos/',
        null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
```

- Has a `role` field: `role = models.CharField(max_length=100, blank=True, null=True)`.
- It is an open unconstrained `CharField` without explicit DB choices.

---

## Step 6: Price Override Restriction

- **File Modified**: `staff/views.py` (`StaffBookingViewSet.add_service` action).
- **Rule Added**:
  - When `custom_price` is passed in the request body, the view checks: `not (getattr(user, 'is_superuser', False) or getattr(user, 'is_manager', False))`.
  - If a regular staff-only user (`is_staff=True` but `is_manager=False` and `is_superuser=False`) attempts to provide a `custom_price` override, the API returns **HTTP 403 Forbidden**:
    ```json
    {
      "error": true,
      "message": "Only managers or admins can override service price"
    }
    ```
  - Regular staff members can still call `add-service` without `custom_price`, which automatically resolves price via model-specific `ServicePricing` lookup.
- **Unit Tests Added**:
  - `test_regular_staff_cannot_override_custom_price`: Asserts regular staff user gets 403 when passing `custom_price`.
  - `test_manager_can_override_custom_price`: Asserts manager user (`is_manager=True`) successfully overrides service price.

---

## Step 7: Manual Verification Results (Automated via Antigravity)

End-to-end programmatic verification executed against Django backend using session token authentication and database fixtures.

### Fixture Setup
- **Target Booking**: Booking #25 (Status: `pending`, Vehicle Model: `Model B`).
- **Staff User**: `staff@repairmybike.in` (ID: 24, `is_staff=True`, `is_manager=False`, `is_superuser=False`).
- **Manager User**: `admin@repairmybike.in` (ID: 23, `is_staff=True`, `is_manager=True`, `is_superuser=True`).
- **Services Prepared**:
  - Service 1: `E2E Oil Check` (ID: 24, Default `ServicePricing`: ₹150.00)
  - Service 2: `E2E Brake Tune` (ID: 25, Default `ServicePricing`: ₹200.00)
  - Service 3: `E2E General Clean` (ID: 26, Default `ServicePricing`: ₹300.00)

### Test Scenarios Execution

#### Scenario 1: Regular staff, no `custom_price`
- **Request**: `POST /api/staff/bookings/25/add-service/`
- **Header**: `Authorization: Bearer test_staff_token_8fa7c04b08f3`
- **Payload**: `{"service_id": 24}`
- **Actual HTTP Status**: `200 OK`
- **Actual Response Body**:
  ```json
  {
    "error": false,
    "message": "Service added successfully",
    "data": {
      "id": 25,
      "total_amount": "250.00",
      "booking_services": [
        {
          "id": 9,
          "service": 24,
          "service_name": "E2E Oil Check",
          "price": "150.00"
        }
      ]
    }
  }
  ```
- **Outcome**: **PASS** (Service added with `ServicePricing`-based price of ₹150.00).

#### Scenario 2: Regular staff, WITH `custom_price`
- **Request**: `POST /api/staff/bookings/25/add-service/`
- **Header**: `Authorization: Bearer test_staff_token_8fa7c04b08f3`
- **Payload**: `{"service_id": 25, "custom_price": 100.0}`
- **Actual HTTP Status**: `403 Forbidden`
- **Actual Response Body**:
  ```json
  {
    "error": true,
    "message": "Only managers or admins can override service price"
  }
  ```
- **Outcome**: **PASS** (Price override properly blocked for non-manager staff).

#### Scenario 3: Manager, WITH `custom_price`
- **Request**: `POST /api/staff/bookings/25/add-service/`
- **Header**: `Authorization: Bearer test_manager_token_ab68c3bf43f4`
- **Payload**: `{"service_id": 26, "custom_price": 250.0}`
- **Actual HTTP Status**: `200 OK`
- **Actual Response Body**:
  ```json
  {
    "error": false,
    "message": "Service added successfully",
    "data": {
      "id": 25,
      "total_amount": "500.00",
      "booking_services": [
        {
          "id": 9,
          "service": 24,
          "service_name": "E2E Oil Check",
          "price": "150.00"
        },
        {
          "id": 10,
          "service": 26,
          "service_name": "E2E General Clean",
          "price": "250.00"
        }
      ]
    }
  }
  ```
- **Outcome**: **PASS** (Manager successfully added service with custom price override ₹250.00).

### Cleanup Report
- **Cleaned Up**: Deleted 2 test `BookingService` entries created on Booking #25 during execution; deleted temporary test `UserSession` tokens.
- **Retained**: Master data fixtures (`Booking #25`, `Service #24`, `Service #25`, `Service #26`, `User #23`, `User #24`).






