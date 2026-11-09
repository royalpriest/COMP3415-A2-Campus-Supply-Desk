"""CR-01 acceptance tests through service, CLI and interactive menu."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
import unittest
from unittest.mock import patch
from supplydesk.cli import main
from supplydesk.menu import run_menu
from supplydesk.service import OrderService
from tests import test_service

item = test_service.item


class ExpressTests(unittest.TestCase):
    setUp = test_service.ServiceTests.setUp

    def test_cr_examples_and_thresholds(self):
        cases = [
            ('regular', [item()], 1000, 0, 2200),
            ('student', [item('hoodie', 2)], 8000, 800, 8400),
            ('regular', [item('hoodie', 3)], 12000, 0, 13200),
            ('regular', [item(quantity=20)], 10000, 0, 11200),
            ('student', [item(quantity=10)], 5000, 500, 5700),
        ]
        for customer, items, subtotal, discount, total in cases:
            with self.subTest(customer=customer, items=items):
                quote = self.service.quote(customer, items, 'express')
                self.assertEqual(quote['subtotal_cents'], subtotal)
                self.assertEqual(quote['discount_cents'], discount)
                self.assertEqual(quote['delivery_cents'], 1200)
                self.assertEqual(quote['total_cents'], total)
                self.assertIs(type(quote['total_cents']), int)
        self.assertEqual(self.service.quote('regular', [item('hoodie', 3)], 'delivery')['total_cents'], 12000)
        self.assertFalse(self.path.exists())

    def test_express_half_cent_rounding_and_fee_not_discounted(self):
        state = self.service.store.load()
        state['catalog'][0]['unit_price_cents'] = 5005
        self.service.store.save(state)
        quote = self.service.quote('student', [item(quantity=1)], 'express')
        self.assertEqual(quote['discount_cents'], 501)
        self.assertEqual(quote['delivery_cents'], 1200)
        self.assertEqual(quote['total_cents'], 5704)

    def test_express_lifecycle_preserves_snapshots_and_numbering(self):
        before = self.service.catalog()
        quote = self.service.quote('student', [item('hoodie', 2)], 'express')
        order = self.service.place_order('student', [item('hoodie', 2)], 'express')
        self.assertEqual({key: order[key] for key in quote}, quote)
        self.assertEqual(order['order_id'], 'ORD-0001')
        reopened = OrderService(self.path)
        self.assertEqual(reopened.get_order(order['order_id']), order)
        self.assertEqual(reopened.list_orders(), [order])
        self.assertEqual(next(p for p in reopened.catalog() if p['product_id'] == 'hoodie')['stock'], 3)
        cancelled = reopened.cancel_order(order['order_id'])
        self.assertEqual(cancelled['status'], 'cancelled')
        self.assertEqual({k: v for k, v in cancelled.items() if k != 'status'}, {k: v for k, v in order.items() if k != 'status'})
        self.assertEqual(reopened.catalog(), before)
        saved = self.path.read_bytes()
        self.assertEqual(reopened.cancel_order(order['order_id']), cancelled)
        self.assertEqual(self.path.read_bytes(), saved)
        self.assertEqual(OrderService(self.path).list_orders(), [cancelled])
        self.assertEqual(reopened.place_order('regular', [item()])['order_id'], 'ORD-0002')

    def test_express_validation_and_atomicity(self):
        self.service.place_order('regular', [item('mug', 1)])
        saved = self.path.read_bytes()
        for operation in (self.service.quote, self.service.place_order):
            for customer, items, fulfillment in [
                ('regular', [item()], 'overnight'),
                ('regular', [item()], 'Express'),
                ('other', [item()], 'express'),
                ('regular', [item(quantity=15), item(quantity=15)], 'express'),
                ('regular', [item(quantity=True)], 'express'),
                ('regular', [item(), item('missing')], 'express'),
            ]:
                with self.subTest(operation=operation.__name__, request=(customer, items, fulfillment)):
                    with self.assertRaises(ValueError):
                        operation(customer, items, fulfillment)
                    self.assertEqual(self.path.read_bytes(), saved)

    def test_cli_express_quote_place_and_help(self):
        for command in ('quote', 'place'):
            output = StringIO()
            with redirect_stdout(output):
                code = main(['--data', str(self.path), command, '--customer', 'student', '--fulfillment', 'express', '--item', 'hoodie:2'])
            self.assertEqual(code, 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result['fulfillment'], 'express')
            self.assertEqual(result['total_cents'], 8400)
            if command == 'quote':
                self.assertFalse(self.path.exists())
            else:
                self.assertEqual(OrderService(self.path).get_order(result['order_id']), result)
            help_output = StringIO()
            with redirect_stdout(help_output), self.assertRaises(SystemExit) as error:
                main([command, '--help'])
            self.assertEqual(error.exception.code, 0)
            self.assertIn('express', help_output.getvalue())
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
            main(['quote', '--fulfillment', 'overnight', '--item', 'notebook:2'])
        self.assertEqual(error.exception.code, 2)

    def test_menu_express_quote_and_placement(self):
        responses = ['2', 'student', 'hoodie', '2', '', 'express', '3', 'student', 'hoodie', '2', '', 'express', 'y', '0']
        output = StringIO()
        with patch('builtins.input', side_effect=responses) as prompts, redirect_stdout(output):
            self.assertEqual(run_menu(self.service), 0)
        self.assertTrue(any('pickup/delivery/express' in call.args[0] for call in prompts.call_args_list))
        self.assertIn('Total: $84.00', output.getvalue())
        order = self.service.list_orders()[0]
        self.assertEqual(order['fulfillment'], 'express')
        self.assertEqual(order['delivery_cents'], 1200)
        self.assertEqual(order['total_cents'], 8400)
