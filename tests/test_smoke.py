"""Starter checks exercise basic setup. They are not complete acceptance coverage."""
import tempfile
import unittest
from pathlib import Path
from ledger import storage, reporting, importing, matching


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = storage.connect(Path(self.tmp.name) / 'demo.sqlite3')
        storage.seed(self.db)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_seed_is_repeatable(self):
        storage.seed(self.db)
        self.assertEqual(len(reporting.invoices(self.db)), 6)

    def test_seed_summary(self):
        summary = reporting.overview(self.db)['summary']
        self.assertEqual(summary['invoice_count'], 6)
        self.assertEqual(summary['outstanding'], 3209.99)

    def test_one_valid_invoice(self):
        result = importing.import_csv(
            self.db,
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,SMOKE-1,25.00,2026-09-09\n',
            'invoices'
        )
        self.assertEqual(result['imported'], 1)

    def test_payment_reference_when_amount_is_unique(self):
        result = importing.import_csv(
            self.db,
            'payment_id,customer_id,invoice_number,amount\n'
            'SMOKE-P1,HARBOR,INV-100,20.00\n',
            'payments'
        )
        self.assertEqual(result['imported'], 1)

        invoice = next(
            r for r in reporting.invoices(self.db)
            if r['invoice_number'] == 'INV-100'
        )

        self.assertEqual(invoice['paid'], 20.00)

    def test_payment_matches_customer_and_invoice_not_amount_only(self):
        importing.import_csv(
            self.db,
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,MATCH-1,20.00,2026-09-30\n',
            'invoices'
        )

        importing.import_csv(
            self.db,
            'customer_id,invoice_number,amount,due_date\n'
            'MAPLE,MATCH-1,20.00,2026-09-30\n',
            'invoices'
        )

        payment = {
            'customer_id': 'MAPLE',
            'invoice_number': 'MATCH-1',
            'amount': 20.00,
        }

        invoice_id = matching.find_invoice(self.db, payment)

        invoice = next(
            r for r in reporting.invoices(self.db)
            if r['customer_id'] == 'MAPLE'
            and r['invoice_number'] == 'MATCH-1'
        )

        self.assertEqual(invoice_id, invoice['id'])

    def test_bad_invoice_row_does_not_block_good_rows(self):
        csv_text = (
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,GOOD-1,100.00,2026-09-30\n'
            'HARBOR,BAD-1,-50.00,2026-09-30\n'
            'MAPLE,GOOD-2,200.00,2026-09-30\n'
        )

        result = importing.import_csv(
            self.db,
            csv_text,
            'invoices'
        )

        self.assertEqual(result['imported'], 2)
        self.assertEqual(result['rejected'], 1)

    def test_duplicate_invoice_is_skipped(self):
        csv_text = (
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,DUP-1,100.00,2026-09-30\n'
        )

        first = importing.import_csv(
            self.db,
            csv_text,
            'invoices'
        )

        second = importing.import_csv(
            self.db,
            csv_text,
            'invoices'
        )

        self.assertEqual(first['imported'], 1)
        self.assertEqual(second['skipped'], 1)
        self.assertEqual(second['imported'], 0)

    def test_changed_duplicate_invoice_is_rejected(self):
        first_csv = (
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,DUP-2,100.00,2026-09-30\n'
        )

        changed_csv = (
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,DUP-2,999.00,2026-09-30\n'
        )

        first = importing.import_csv(
            self.db,
            first_csv,
            'invoices'
        )

        second = importing.import_csv(
            self.db,
            changed_csv,
            'invoices'
        )

        self.assertEqual(first['imported'], 1)
        self.assertEqual(second['rejected'], 1)

    def test_status_filters_separate_open_and_paid(self):
        open_invoices = reporting.invoices(self.db, 'open')
        paid_invoices = reporting.invoices(self.db, 'paid')

        self.assertTrue(open_invoices)
        self.assertTrue(paid_invoices)

        self.assertTrue(
            all(invoice['status'] == 'open' for invoice in open_invoices)
        )

        self.assertTrue(
            all(invoice['status'] == 'paid' for invoice in paid_invoices)
        )

    def test_money_values_preserve_cents(self):
        importing.import_csv(
            self.db,
            'customer_id,invoice_number,amount,due_date\n'
            'HARBOR,MONEY-1,100.10,2026-09-30\n',
            'invoices'
        )

        importing.import_csv(
            self.db,
            'payment_id,customer_id,invoice_number,amount\n'
            'MONEY-P1,HARBOR,MONEY-1,33.33\n'
            'MONEY-P2,HARBOR,MONEY-1,33.33\n',
            'payments'
        )

        invoice = next(
            r for r in reporting.invoices(self.db)
            if r['invoice_number'] == 'MONEY-1'
        )

        self.assertEqual(invoice['paid'], 66.66)
        self.assertEqual(invoice['balance'], 33.44)


    def test_export_preserves_money_to_two_decimals(self):
        csv_text = reporting.export_csv(self.db)

        row = next(
            line for line in csv_text.splitlines()
            if 'NORTH,INV-300' in line
        )

        self.assertIn('19.99,10.00,9.99,open', row)

    def test_export_has_header(self):
        self.assertTrue(
            reporting.export_csv(self.db).startswith(
                'customer_id,invoice_number,amount,paid,balance,status'
            )
        )


if __name__ == '__main__':
    unittest.main()