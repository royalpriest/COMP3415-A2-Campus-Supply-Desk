"""Requirement-based safety net; failures on the starter are retained in evidence."""
import json
from pathlib import Path
import tempfile
import unittest
from supplydesk.service import OrderService


def item(product='notebook', quantity=2):
    return {'product_id': product, 'quantity': quantity}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'state.json'
        self.service = OrderService(self.path)

    def state(self):
        return self.service.store.load()

    def test_quote_matches_order_and_has_no_side_effects(self):
        before = self.state()
        quote = self.service.quote('student', [item('hoodie', 2)], 'delivery')
        self.assertEqual(self.state(), before)
        self.assertFalse(self.path.exists())
        order = self.service.place_order('student', [item('hoodie', 2)], 'delivery')
        self.assertEqual({key: order[key] for key in quote}, quote)
        saved = self.path.read_bytes()
        self.service.quote('regular', [item()])
        self.assertEqual(self.path.read_bytes(), saved)

    def test_student_threshold(self):
        for quantity, discount in [(9, 0), (10, 500), (11, 550)]:
            with self.subTest(quantity=quantity):
                quote = self.service.quote('student', [item(quantity=quantity)])
                self.assertEqual(quote['discount_cents'], discount)
                self.assertEqual(quote['total_cents'], quantity * 500 - discount)

    def test_standard_delivery_threshold(self):
        for quantity, fee in [(19, 600), (20, 0)]:
            with self.subTest(quantity=quantity):
                self.assertEqual(self.service.quote('regular', [item(quantity=quantity)], 'delivery')['delivery_cents'], fee)
        # Gross subtotal reaches $100, but discounted merchandise does not.
        self.assertEqual(self.service.quote('student', [item(quantity=20)], 'delivery')['delivery_cents'], 600)

    def test_half_cent_rounds_up_using_integer_money(self):
        state = self.state()
        state['catalog'][0]['unit_price_cents'] = 5005
        self.service.store.save(state)
        quote = self.service.quote('student', [item(quantity=1)])
        self.assertEqual(quote['discount_cents'], 501)
        self.assertEqual(quote['total_cents'], 4504)
        self.assertIs(type(quote['total_cents']), int)

    def test_all_available_stock_can_be_ordered(self):
        order = self.service.place_order('regular', [item('bag', 4)])
        self.assertEqual(order['total_cents'], 10000)
        self.assertEqual(next(p for p in self.service.catalog() if p['product_id'] == 'bag')['stock'], 0)
        with self.assertRaises(ValueError):
            self.service.place_order('regular', [item('bag', 1)])

    def test_quantity_99_with_sufficient_stock(self):
        state = self.state()
        state['catalog'][0]['stock'] = 100
        self.service.store.save(state)
        order = self.service.place_order('regular', [item(quantity=99)])
        self.assertEqual(order['total_cents'], 49500)
        self.assertEqual(self.service.catalog()[0]['stock'], 1)

    def test_invalid_requests_leave_existing_saved_data_unchanged(self):
        self.service.place_order('regular', [item('mug', 1)])
        before = self.path.read_bytes()
        bad = [('other', [item()], 'pickup'), ('regular', [item()], 'overnight')]
        bad += [('regular', value, 'pickup') for value in [[], None, {}, [None], [{}], [item('missing')], [item(), item('missing')]]]
        bad += [('regular', [item(quantity=q)], 'pickup') for q in [0, -1, 100, True, 1.5, '2', None]]
        for operation in (self.service.quote, self.service.place_order):
            for request in bad:
                with self.subTest(operation=operation.__name__, request=request):
                    with self.assertRaises(ValueError):
                        operation(*request)
                    self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.service.place_order('regular', [item()])['order_id'], 'ORD-0002')

    def test_duplicate_lines_over_stock_are_rejected_atomically(self):
        before = self.state()
        for operation in (self.service.quote, self.service.place_order):
            with self.subTest(operation=operation.__name__):
                with self.assertRaises(ValueError):
                    operation('regular', [item(quantity=15), item(quantity=15)])
                self.assertEqual(self.state(), before)
                self.assertFalse(self.path.exists())

    def test_valid_duplicate_lines_preserve_lines_and_restore_stock(self):
        order = self.service.place_order('regular', [item(quantity=10), item(quantity=10)])
        self.assertEqual(len(order['items']), 2)
        self.assertEqual(self.service.catalog()[0]['stock'], 0)
        self.service.cancel_order(order['order_id'])
        self.assertEqual(self.service.catalog()[0]['stock'], 20)

    def test_repeated_cancellation_does_not_restore_stock_twice(self):
        order = self.service.place_order('regular', [item()])
        cancelled = self.service.cancel_order(order['order_id'])
        before = self.path.read_bytes()
        self.assertEqual(self.service.cancel_order(order['order_id']), cancelled)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.service.catalog()[0]['stock'], 20)

    def test_history_numbering_and_price_snapshot_survive_reopening(self):
        first = self.service.place_order('regular', [item()])
        self.service.cancel_order(first['order_id'])
        second = self.service.place_order('regular', [item('mug', 1)])
        self.assertEqual(second['order_id'], 'ORD-0002')
        state = self.state()
        state['catalog'][0]['unit_price_cents'] = 9999
        self.service.store.save(state)
        reopened = OrderService(self.path)
        history = reopened.list_orders()
        self.assertEqual([o['order_id'] for o in history], ['ORD-0001', 'ORD-0002'])
        self.assertEqual(history[0]['status'], 'cancelled')
        self.assertEqual(history[0]['total_cents'], first['total_cents'])
        self.assertEqual(reopened.catalog()[0]['stock'], 20)

    def test_unknown_order_does_not_change_data(self):
        self.service.place_order('regular', [item()])
        before = self.path.read_bytes()
        for operation in (self.service.get_order, self.service.cancel_order):
            with self.assertRaises(ValueError):
                operation('ORD-9999')
            self.assertEqual(self.path.read_bytes(), before)

    def test_malformed_save_is_not_silently_reset(self):
        self.path.write_text('{broken', encoding='utf-8')
        with self.assertRaises(json.JSONDecodeError):
            self.service.catalog()
        self.assertEqual(self.path.read_text(), '{broken')
