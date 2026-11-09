"""Exercise real service calls through both adapters without touching user data."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from unittest.mock import patch
from supplydesk.cli import main
from supplydesk.menu import run_menu
import unittest
import json
from tests import test_service


class InterfaceTests(unittest.TestCase):
    setUp = test_service.ServiceTests.setUp

    def menu(self, responses):
        output = StringIO()
        with patch('builtins.input', side_effect=responses), redirect_stdout(output):
            status = run_menu(self.service)
        self.assertEqual(status, 0)
        return output.getvalue()

    def test_menu_declined_placement_and_defaults(self):
        output = self.menu(['3', '', 'notebook', '2', '', '', 'n', '0'])
        self.assertIn('Customer: regular | Fulfillment: pickup', output)
        self.assertIn('Order not placed.', output)
        self.assertFalse(self.path.exists())

    def test_menu_operations_and_declined_cancellation(self):
        output = self.menu(['1', '4', '3', '', 'notebook', '2', '', '', 'y', '5', 'ORD-0001', '6', 'ORD-0001', 'n', '4', '6', 'ORD-0001', 'y', '0'])
        self.assertIn('No orders yet.', output)
        self.assertIn('Cancellation abandoned.', output)
        self.assertIn('ORD-0001 - placed', output)
        self.assertEqual(self.service.get_order('ORD-0001')['status'], 'cancelled')
        self.assertEqual(self.service.catalog()[0]['stock'], 20)

    def test_menu_recovers_from_bad_input(self):
        output = self.menu(['9', '2', '', 'notebook', 'oops', 'notebook', '2', '', '', '5', 'missing', '0'])
        self.assertIn('Choose a number from 0 to 6.', output)
        self.assertIn('Please enter a whole number.', output)
        self.assertIn('Total: $10.00', output)
        self.assertIn('Error: Unknown order:', output)
        self.assertFalse(self.path.exists())

    def test_menu_eof_and_interrupt_exit(self):
        for exception in (EOFError, KeyboardInterrupt):
            with self.subTest(exception=exception):
                self.assertIn('Goodbye.', self.menu(exception))

    def test_cli_defaults_and_rejected_input(self):
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(main(['--data', str(self.path), 'quote', '--item', 'notebook:2']), 0)
            self.assertEqual(main(['--data', str(self.path), 'place', '--item', 'missing:1']), 2)
        quote = json.loads(output.getvalue())
        self.assertEqual(quote['fulfillment'], 'pickup')
        self.assertEqual(quote['customer_type'], 'regular')
        self.assertEqual(quote['total_cents'], 1000)
        self.assertIn('Unknown product', errors.getvalue())
        self.assertFalse(self.path.exists())
