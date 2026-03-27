# Privacy Policy

**Platform**: RepairMyBike  
**Last Updated**: 2026-03-28  
**Effective Date**: 2026-03-28

---

## 1. Introduction and Scope

Welcome to **RepairMyBike**, a technology-enabled doorstep bike repair and spare parts platform operated by RepairMyBike (hereinafter "Company", "We", "Us", or "Our"). This Privacy Policy ("Policy") governs the collection, storage, processing, and transfer of information from users ("You", "Your", or "User") who access or use our web application and associated backend services (collectively, the "Platform").

We are committed to protecting Your privacy and complying with the **Information Technology Act, 2000**, the **Information Technology (Reasonable Security Practices and Procedures and Sensitive Personal Data or Information) Rules, 2011** ("SPDI Rules"), and other applicable Indian laws.

---

## 2. Definitions

- **Personal Data**: Any information that relates to a natural person, which, either directly or indirectly, in combination with other information available, is capable of identifying such person.
- **Sensitive Personal Data or Information (SPDI)**: As defined under SPDI Rules — includes passwords, financial information, physical/mental health conditions, and biometric data.
- **Session Token**: A cryptographic JSON Web Token (JWT) issued by our authentication provider, Descope, to maintain secure user sessions.
- **Guest Session**: An anonymous, non-authenticated browsing session identified by a temporary unique identifier stored locally on the User's device.

---

## 3. Information We Collect

### 3.1 Information Provided by You (Registered Users)

- **Identity and Contact Data**: Full name, email address, and mobile number. Mobile numbers are verified via One-Time Password (OTP) processes integrated with **Descope**.
- **Address and Location Data**: Flat/House No., Area, Street, Landmark, Pincode, City, State — collected to facilitate on-site bike repair services and spare part deliveries.
- **Vehicle Data**: Two-wheeler type (e.g., motorcycle, scooter), brand, and model — required for accurate service procurement and parts compatibility checks.
- **Profile Picture**: An optional avatar URL, stored via **Cloudinary** (our cloud media provider).

### 3.2 Information Collected Automatically

- **Device and Session Metadata**: Device type, operating system, IP address, browser type, and interaction logs.
- **Firebase Cloud Messaging (FCM) Tokens**: Device-specific push notification tokens used to deliver real-time booking status updates and service alerts.
- **Guest Identifier**: A locally generated UUID-like identifier (`guest_id`) stored in the browser's local storage to support cart persistence and wishlists for unauthenticated users.

### 3.3 Transaction and Order Data

- **Booking Records**: Service type, vehicle details, appointment date/time, service location (Home or Shop Visit), assigned technician, booking status history, and odometer reading.
- **Spare Part Orders**: Items purchased, quantities, shipping address, order status, courier tracking number, and shipping/delivery timestamps.
- **Account Activity**: Saved services, saved spare parts (wishlists), and coupon usage history.

### 3.4 WhatsApp Communication Data (Conditional)

- The Platform is integrated with the **Kapso** API (a WhatsApp Business API provider) for transactional notifications. Messages sent via this channel, along with the User's phone number and message delivery status, are logged internally.
- **Current Status**: WhatsApp notifications are partially configured. Delivery is contingent on correct configuration of `KAPSO_PHONE_NUMBER_ID` in the production environment.

### 3.5 Payment Data

- **⚠️ IMPORTANT: Online payment processing is currently DISABLED.** The Platform is operating in a **Cash-Only** mode. No credit card numbers, debit card details, CVVs, or UPI information are collected or stored on our servers.
- All bookings and spare part orders are settled exclusively in **cash** at the time of service completion or delivery.

---

## 4. Legal Basis and Purpose of Processing

We process Your data based on Your implicit or explicit consent and for the following lawful purposes:

| Purpose | Data Used |
|---|---|
| Account creation and OTP authentication | Phone number, Descope JWT |
| Booking and service management | Name, address, vehicle data, booking details |
| Spare part order fulfillment | Name, phone, address, order items |
| Real-time booking status notifications | FCM token, phone number |
| WhatsApp transactional messages | Phone number (if WhatsApp is enabled) |
| Guest basket and wishlist persistence | Guest UUID (local only) |
| Staff assignment and internal operations | Booking data, staff directory |

---

## 5. Data Sharing and Disclosure

We do **not** sell Your Personal Data. We disclose information to third parties only as necessary:

- **Authentication Partner (Descope)**: For OTP verification and secure session management.
- **Cloud Media Storage (Cloudinary)**: For hosting product images, spare part photos, and profile pictures.
- **Push Notification Service (Google Firebase)**: For delivering real-time booking and order updates to mobile devices.
- **WhatsApp Messaging (Kapso)**: For transactional WhatsApp notifications related to bookings and orders.
- **Operational Partners**: Service technician details shared internally for booking fulfillment; delivery address shared with logistics partners for spare part orders.
- **Legal Compliance**: Disclosure to law enforcement or regulatory authorities when mandated by applicable law.

---

## 6. Data Retention

We retain Your Personal Data only for the duration necessary to provide services or as mandated by statutory periods under Indian law. Booking records, order history, and associated vehicle data are retained for a minimum of **3 years** for audit and warranty purposes. Upon cessation of purpose, data is deleted or anonymized.

---

## 7. Security Measures

We implement the following industry-standard security practices:

- **Authentication**: JWT-based session management with automated expiry, powered by Descope.
- **Role-Based Access Control (RBAC)**: Distinct permission levels for Customers, Staff, and Administrators.
- **Encrypted Transmission**: All API communications are transmitted over HTTPS/SSL-encrypted channels.
- **Cloud Security**: Media assets are stored on Cloudinary with access-controlled URLs.
- **No Payment Data On-Server**: Since the Platform operates as Cash-Only, no sensitive financial data is stored.

---

## 8. User Rights

Under the SPDI Rules and applicable Indian law, You have the following rights:

- **Access and Correction**: Review and update Your profile details (name, email, address, avatar) through the Platform's Profile section.
- **Vehicle Management**: Add, view, or delete Your registered vehicles via the Platform.
- **Saved Items**: Manage Your saved services and spare part wishlist at any time.
- **Withdrawal of Consent**: You may request deactivation of Your account by contacting our support team. This will restrict access to services.
- **Account Erasure**: Request deletion of Your account. We will process after fulfilling any pending service or legal obligations.

---

## 9. Cookies and Local Storage

The Platform stores a `guest_id` in browser local storage to enable cart and wishlist functionality for unauthenticated users. Authenticated user sessions are managed via JWT tokens, not traditional cookies. No third-party advertising cookies are used.

---

## 10. Third-Party Links

Our Platform may contain links to third-party websites (e.g., courier tracking portals). We are not responsible for their privacy practices.

---

## 11. Grievance Redressal

In accordance with the Information Technology Act, 2000, the Grievance Officer for this Platform can be reached at:

- **Email**: support@repairmybike.in
- **Response Time**: Within 30 days of receipt of grievance.

---

## 12. Changes to this Policy

We reserve the right to modify this Policy at any time. Significant changes will be notified via the Platform. Continued use of the Platform after such changes constitutes Your acceptance of the updated Policy.
