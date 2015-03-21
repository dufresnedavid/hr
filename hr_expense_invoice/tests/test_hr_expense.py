# -*- encoding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in root directory
##############################################################################

from openerp.tests import common
from openerp import fields


class TestHrExpenseExpense(common.TransactionCase):

    def setUp(self):
        super(TestHrExpenseExpense, self).setUp()

        self.invoice_model = self.env['account.invoice']
        self.expense_model = self.env['hr.expense.expense']
        self.line_model = self.env['hr.expense.line']
        self.partner_model = self.env['res.partner']
        self.employee_model = self.env['hr.employee']
        self.account_model = self.env['account.account']

        self.partner = self.partner_model.create({
            'name': 'Test',
            'supplier': True,
        })

        self.employee = self.employee_model.create({
            'name': 'Test',
            'address_home_id': self.partner_model.create(
                {'name': 'Test'}).id
        })

        self.invoice = self.invoice_model.create({
            'partner_id': self.partner.id,
            'type': 'in_invoice',
            'date_invoice': fields.Date.today(),
            'account_id': self.account_model.search(
                [('type', '=', 'payable')])[0].id,
            'invoice_line': [(0, 0, {
                'name': 'Test',
                'account_id': self.account_model.search(
                    [('type', '=', 'other')])[0].id,
                'price_unit': 100,
            })]
        })

        self.invoice.signal_workflow('invoice_open')

    def test_create_expense(self):
        """
        Test expense line is created properly and when it is done,
        the related invoice's state is changed to paid
        """
        self.expense = self.expense_model.create({
            'employee_id': self.employee.id,
            'name': 'Test',
        })

        self.expense_line = self.line_model.create({
            'expense_id': self.expense.id,
            'invoice': self.invoice.id,
            'name': 'Test',
        })

        self.expense_line.onchange_invoice()

        self.expense.signal_workflow('confirm')
        self.expense.signal_workflow('validate')
        self.expense.signal_workflow('done')

        self.invoice.refresh()

        self.assertEqual(self.invoice.state, 'paid')
