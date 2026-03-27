# Payment Policy

**Platform**: RepairMyBike  
**Last Updated**: 2026-03-28  
**Effective Date**: 2026-03-28

---

## 1. Overview

This Payment Policy ("Policy") governs all financial transactions on the **RepairMyBike** Platform, covering both repair service bookings and spare part purchases.

---

## 2. Current Payment Mode

> **⚠️ CRITICAL NOTICE**: The RepairMyBike Platform currently operates in **Cash-Only Mode**. Online payment gateways, including Razorpay, UPI, credit/debit cards, and net banking, are **explicitly disabled** in the current operational environment (`RAZORPAY_ENABLED = False`).

> **All payments for repair services and spare part orders are accepted exclusively in cash** — either at the time of service completion (for Home Service/Shop Visit bookings) or upon delivery (for spare part orders via Cash on Delivery / COD).

This is a deliberate operational decision for the current phase of business. Online payment capability is built into the system architecture and may be enabled in a future release.

---

## 3. Accepted Payment Methods

| Service Type | Accepted Payment | Method |
|---|---|---|
| Repair Service Booking | Cash | Paid to technician upon completion |
| Shop Visit | Cash | Paid at the workshop upon completion |
| Spare Part Order | Cash on Delivery (COD) | Paid to delivery agent upon receipt |
| Subscription Plan | Cash | Paid to a Company representative upon plan activation |

**Not currently accepted:**
- Credit Cards
- Debit Cards
- UPI (GPay, PhonePe, BHIM, Paytm, etc.)
- Net Banking
- Wallets
- EMI
- Razorpay or any other payment gateway

---

## 4. Pricing and Final Bill

### 4.1 Repair Services

- The price shown during booking is an **initial estimate** based on the selected service and vehicle type.
- The final bill may differ based on:
  - Additional spare parts required during the service.
  - Supplementary labor identified during the repair.
- Any additional charges require the User's explicit consent before work commences on the additional scope.

### 4.2 Spare Parts

- The price displayed on the product listing and at checkout is the confirmed selling price in **Indian Rupees (INR)**.
- Shipping charges, if applicable, are shown separately before order confirmation.
- The price at the time of order placement is the final price.

### 4.3 Subscriptions

- Subscription plan prices are displayed in the Platform and are quoted in INR per billing period (Monthly, Quarterly, Half-Yearly, or Yearly).
- The effective price may be the discounted price (`discount_price`) where a promotional offer is active; otherwise, the standard plan price applies.

---

## 5. Discounts and Promotional Coupons

- The Platform supports discount coupons applicable to repair service bookings.
- Coupons have defined validity periods, minimum order values, and usage limits.
- Only one coupon may be applied per booking.
- Discounts are shown as a deduction on the final booking summary before confirmation.
- Coupons are not redeemable for cash and cannot be combined with other offers.

---

## 6. GST and Taxes

All prices displayed on the Platform are inclusive of applicable Goods and Services Tax (GST) as required under Indian law, unless explicitly stated otherwise. GST invoices are available upon request.

---

## 7. Invoicing

A digital service invoice is generated for every completed booking and delivered order. This is accessible within the Platform under:
- "My Bookings" (for repair services)
- "Order History" (for spare part orders)

---

## 8. Payment Failures

Since the Platform operates in Cash-Only mode, there are no online payment failure scenarios. If a Cash on Delivery transaction cannot be completed due to the User being unavailable, please refer to the Shipping & Delivery Policy regarding failed deliveries.

---

## 9. Security

Since no online payment gateway is active, the Platform does **not** collect, transmit, or store any sensitive financial data such as:
- Card Numbers (PAN)
- CVV / CVC
- UPI IDs
- Net Banking Credentials

The Platform is therefore not subject to PCI-DSS requirements in its current operating mode.

---

## 10. Future Online Payment Integration

The Platform's backend infrastructure includes a fully coded (but disabled) integration with **Razorpay**, India's leading payment gateway. This integration includes:
- Order creation APIs
- Payment signature verification
- Refund initiation APIs

Online payment via Razorpay may be re-enabled in a future operational phase. Users will be notified of any changes to the payment methods via the Platform.

---

## 11. Currency

All transactions on the RepairMyBike Platform are denominated in **Indian Rupees (INR)**.

---

## 12. Contact

For any payment-related queries or billing discrepancies:

- **Email**: support@repairmybike.in
- **Please include**: Your Booking ID or Order ID in the subject line.
- **Response Time**: Within 2 business days.
