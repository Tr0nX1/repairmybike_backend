import requests, json

BASE = "http://localhost:8000/api/bookings/bookings/"

def pretty(r):
    print(r.status_code, json.dumps(r.json(), indent=2))

# 1. Create booking
payload = {
    "customer_name": "Rahul Sharma",
    "customer_phone": "9876543210",
    "customer_email": "rahul@example.com",
    "vehicle_model_id": 1,
    "service_ids": [3, 7],
    "service_location": "home",
    "address": "123, MG Road, Bangalore",
    "appointment_date": "2025-11-01",
    "appointment_time": "10:00:00"
}
r = requests.post(BASE, json=payload)
pretty(r)
booking_id = r.json()["data"]["id"]

# 2. List bookings
pretty(requests.get(BASE, params={"phone": "9876543210"}))

# 3. Retrieve created booking
pretty(requests.get(f"{BASE}{booking_id}/"))