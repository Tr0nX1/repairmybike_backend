import threading
import time
from decimal import Decimal
from django.urls import reverse
from django.db import transaction
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from spare_parts.models import SparePart, SparePartCategory, SparePartBrand, Cart, CartItem, Order, OrderItem
from django.test import TransactionTestCase

User = get_user_model()

class OrderTests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a', password='password123', phone_number='+919999999991')
        self.user_b = User.objects.create_user(username='user_b', password='password123', phone_number='+919999999992')
        
        self.sp_cat = SparePartCategory.objects.create(name='Parts', slug='parts')
        self.sp_brand = SparePartBrand.objects.create(name='Brand', slug='brand')
        
        self.part = SparePart.objects.create(
            category=self.sp_cat,
            brand=self.sp_brand,
            name='Test Part',
            slug='test-part',
            sku='SKU-001',
            mrp=100.00,
            sale_price=90.00,
            stock_qty=10
        )

    def test_checkout_fails_if_any_item_out_of_stock(self):
        """Cart with 3 items, one OOS, entire checkout fails"""
        self.client.force_authenticate(user=self.user_a)
        session_id = "test_session_123"
        
        # Part with no stock
        oos_part = SparePart.objects.create(
            category=self.sp_cat, brand=self.sp_brand, name='OOS Part', 
            slug='oos-part', sku='SKU-OOS', mrp=100, sale_price=90, stock_qty=0
        )
        
        # Add items to cart
        cart, _ = Cart.objects.get_or_create(user=self.user_a, session_id=session_id)
        CartItem.objects.create(cart=cart, spare_part=self.part, quantity=1, unit_price=90)
        CartItem.objects.create(cart=cart, spare_part=oos_part, quantity=1, unit_price=90)
        
        url = reverse('spare-part-cart-checkout')
        data = {
            'session_id': session_id,
            'customer_name': 'Test User',
            'phone': '+919999999991',
            'address': 'Test Address'
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Insufficient stock', resp.data.get('message', ''))
        
        # Verify no order created
        self.assertEqual(Order.objects.count(), 0)

    def test_order_cancel_reverses_stock(self):
        """Cancelling order restores stock_qty"""
        self.client.force_authenticate(user=self.user_a)
        session_id = "test_session_456"
        
        # Manual order creation (simulating successful checkout)
        order = Order.objects.create(
            user=self.user_a, session_id=session_id, 
            customer_name='Test', phone='+91', address='...',
            amount_total=90, status='created'
        )
        OrderItem.objects.create(order=order, spare_part=self.part, quantity=2, unit_price=90)
        
        # Deduct stock manually first
        self.part.stock_qty -= 2
        self.part.save()
        
        url = reverse('spare-part-order-cancel', kwargs={'pk': order.id})
        resp = self.client.post(url, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock_qty, 10)

    def test_cannot_view_other_users_order(self):
        """User A cannot retrieve user B's order (gets 404)"""
        order_b = Order.objects.create(
            user=self.user_b, session_id="session_b",
            customer_name='User B', phone='+912', address='...',
            amount_total=100
        )
        
        self.client.force_authenticate(user=self.user_a)
        url = reverse('spare-part-order-detail', kwargs={'pk': order_b.id})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ConcurrentOrderTests(TransactionTestCase):
    """TransactionTestCase is needed for multi-threaded DB access tests"""
    def setUp(self):
        self.user_a = User.objects.create_user(username='user_a_c', password='password123')
        self.user_b = User.objects.create_user(username='user_b_c', password='password123')
        
        self.sp_cat = SparePartCategory.objects.create(name='Parts C', slug='parts-c')
        self.sp_brand = SparePartBrand.objects.create(name='Brand C', slug='brand-c')
        
        self.part = SparePart.objects.create(
            category=self.sp_cat,
            brand=self.sp_brand,
            name='Limited Part',
            slug='limited-part',
            sku='SKU-LIM',
            mrp=100.00,
            sale_price=90.00,
            stock_qty=1
        )

    def test_concurrent_checkout_does_not_oversell(self):
        """Two simultaneous checkouts for qty=1 item, only one succeeds"""
        # Setup carts
        cart_a = Cart.objects.create(user=self.user_a, session_id="sess_a")
        CartItem.objects.create(cart=cart_a, spare_part=self.part, quantity=1, unit_price=90)
        
        cart_b = Cart.objects.create(user=self.user_b, session_id="sess_b")
        CartItem.objects.create(cart=cart_b, spare_part=self.part, quantity=1, unit_price=90)
        
        from rest_framework.test import APIClient
        
        results = []
        def do_checkout(user, session_id):
            client = APIClient()
            client.force_authenticate(user=user)
            url = reverse('spare-part-cart-checkout')
            data = {
                'session_id': session_id,
                'customer_name': user.username,
                'phone': '123',
                'address': '...'
            }
            resp = client.post(url, data, format='json')
            results.append(resp.status_code)

        t1 = threading.Thread(target=do_checkout, args=(self.user_a, "sess_a"))
        t2 = threading.Thread(target=do_checkout, args=(self.user_b, "sess_b"))
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
        # Verify results: One 201, one 400
        self.assertIn(status.HTTP_201_CREATED, results)
        self.assertIn(status.HTTP_400_BAD_REQUEST, results)
        
        self.part.refresh_from_db()
        self.assertEqual(self.part.stock_qty, 0)
        self.assertEqual(Order.objects.filter(status='created').count(), 1)
