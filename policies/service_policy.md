# Service Policy (Bike Repair and Maintenance)

**Platform**: RepairMyBike  
**Last Updated**: 2026-03-28  
**Effective Date**: 2026-03-28

---

## 1. Scope of Services

**RepairMyBike** is a technology-enabled doorstep bike repair and maintenance platform. We connect customers with skilled technicians for on-site service, and also operate certified Partner Workshops for complex repairs. Our services cover motorcycles, scooters, and other two-wheelers registered on the Platform.

---

## 2. Service Booking Process

Services are booked through the Platform as follows:

1. **User Registration**: Mobile number verification via OTP (Descope).
2. **Vehicle Registration**: User registers their vehicle (Type → Brand → Model) on the Platform.
3. **Service Selection**: User selects the required service(s) from the available catalog.
4. **Appointment Scheduling**: User selects a preferred date, time slot, and service location (Home or Shop Visit).
5. **Booking Confirmation**: A booking is created with status `Pending`. Confirmation with status `Confirmed` is sent via Push Notification (Firebase) and/or WhatsApp (Kapso).
6. **Staff Assignment**: An appropriate technician is assigned (`Staff Assigned` status).
7. **Service Execution**: Technician arrives and executes the service (`In Progress` status).
8. **Completion**: Service marked as `Completed`. Invoice generated in-app.
9. **Payment**: Cash payment collected from the User upon service completion.

---

## 3. Service Modalities

### 3.1 Home Service (On-Site / Doorstep)

- A Company-assigned technician travels to the User's registered or specified address.
- The User must provide:
  - A safe and accessible environment (private parking, garage, or open driveway).
  - Clear access to the vehicle.
- Public road-side repairs are generally not conducted to ensure safety and compliance with local regulations.
- The User must ensure no apartment or housing society rules prohibit repair work in the designated area.

### 3.2 Shop / Workshop Visit (Off-Site)

- Required for complex repairs that demand workshop-level equipment, such as:
  - Engine overhauls
  - Chassis and frame repairs
  - Electrical system diagnostics
- Location details and appointment scheduling for Partner Workshops are provided within the Platform.
- The Company may arrange pick-up and drop-off of the vehicle for select pincodes, as displayed at the time of booking.

---

## 4. Technician Assignment

- Bookings are assigned to a qualified technician from the Company's **Staff Directory**.
- Assignment is based on availability, proximity, and the type of service requested.
- The User is notified of the assigned technician's name and, where applicable, estimated time of arrival (ETA) via Push Notification.
- The Company reserves the right to reassign a technician before the service begins without advance notice if operationally necessary.

---

## 5. Spare Parts and Consumables

- **Genuine Parts Commitment**: RepairMyBike uses only genuine OEM (Original Equipment Manufacturer) or certified high-quality aftermarket parts from verified suppliers.
- **In-Progress Identification**: If the technician identifies additional faults or required parts during the service that were not part of the original booking, a digital estimate will be shared via the app. No additional work will commence without the User's explicit approval.
- **Consumables**: Items such as engine oil, brake fluid, and filters are ordered specifically for each service job and are non-returnable once applied to the vehicle.

---

## 6. Subscription-Based Service (AMC Plans)

- Users may subscribe to Annual Maintenance Plan (AMP) or similar membership plans (Basic or Premium tiers).
- Plans include a defined number of service **visits** per billing period (Monthly, Quarterly, Half-Yearly, or Yearly).
- Each time a booking linked to a subscription is marked `Completed`, one visit is automatically deducted from the User's remaining visits for the period.
- If a User exceeds their included visits within a billing period, additional visits are billed as individual services at the standard rate.
- Upon auto-renewal, the visit count resets to the plan's `included_visits` limit.

---

## 7. Service Warranty (Labour Warranty)

RepairMyBike stands behind the quality of its technicians' work:

- **Duration**: A warranty on labour is applicable for **7 days or 500 kilometers** (whichever occurs first) from the date of service completion.
- **Coverage**: If the same issue recurs within the warranty period due to a defect in workmanship, the Company will rectify it at no additional labour charge.
- **Exclusions**: This warranty does not cover:
  - Issues arising from accidents or external damage after service.
  - Tampering by third-party mechanics.
  - Usage in violation of the vehicle manufacturer's guidelines.
  - Pre-existing faults outside the scope of the original service.
  - Consumables (oil, filters, brake pads) subject to normal wear and tear.

---

## 8. Service Records and Digital Health Reports

- Every completed service generates a **Service Invoice** and a **Service History Record** accessible in the "My Bookings" section of the User's account.
- Booking Status History (Pending → Confirmed → Assigned → In Progress → Completed/Cancelled) is logged with timestamps for transparency.
- Users are advised to retain these records for insurance claims, resale documentation, and future warranty reference.

---

## 9. Liability Disclaimer

- **Pre-existing Faults**: The Company is not responsible for mechanical failures or defects that existed prior to the booked service and were either not disclosed by the User or not included in the active service scope.
- **Internal/Latent Failures**: RepairMyBike is not liable for accidental internal engine, electrical, or mechanical failures that occur during testing or standard repair procedures caused by the aged or degraded state of the vehicle's existing components.
- **Vehicle Safety**: The User is advised to remove all personal belongings (documents, helmets, valuables) from the vehicle before handing it over to the technician.

---

## 10. Technician Conduct

- All RepairMyBike technicians are trained, verified, and bound by a professional Code of Conduct.
- Any grievances regarding technician behaviour must be reported immediately via:
  - The in-app support section.
  - Email: support@repairmybike.in
- Verified misconduct complaints will result in immediate suspension and investigation of the concerned technician.

---

## 11. Service Cancellations

- Users may cancel a booking before it reaches the `In Progress` status.
- Cancellation within 2 hours of the appointment window may incur a convenience fee.
- Refer to the **Refund and Cancellation Policy** for complete cancellation terms.

---

## 12. Contact

For service-related queries, warranty claims, or complaints:

- **Email**: support@repairmybike.in
- **Response Time**: Within 24–48 hours.
