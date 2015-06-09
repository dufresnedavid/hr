# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Savoir-faire Linux. All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.tests import common
from openerp.osv.orm import except_orm


def create_activities(self):
    cr, uid, context = self.cr, self.uid, self.context

    self.job_model = self.registry('hr.job')
    self.leave_model = self.registry('hr.holidays.status')
    self.activity_model = self.registry('hr.activity')

    job_id = self.job_model.create(cr, uid, {
        'name': 'Job Test'}, context=context)

    leave_id = self.leave_model.create(cr, uid, {
        'name': 'Leave Test'}, context=context)

    self.activity_job_id = self.activity_model.search(cr, uid, [
        ('job_id', '=', job_id)], context=context)[0]

    self.activity_leave_id = self.activity_model.search(cr, uid, [
        ('leave_id', '=', leave_id)], context=context)[0]


def create_worked_days(
    self, values, payslip_id=False, contract_id=False,
    activity_id=False, browse=False,
):
    cr, uid, context = self.cr, self.uid, self.context

    ids = [
        self.worked_days_model.create(
            cr, uid, {
                # 18 days -> 10 hours each day
                'date_from': wd[0],
                'date_to': wd[1],
                'number_of_hours': wd[2],
                'hourly_rate': 25,
                'rate': 100,
                'payslip_id': payslip_id or self.payslip_id,
                'code': 'test',
                'name': 'test',
                'contract_id': contract_id or self.contract_id,
                'activity_id': activity_id or self.activity_job_id,
            }, context=context)
        for wd in values
    ]

    return browse and self.worked_days_model.browse(
        cr, uid, ids, context=context) or ids


class test_hr_payslip(common.TransactionCase):

    def setUp(self):
        super(test_hr_payslip, self).setUp()
        self.employee_model = self.registry('hr.employee')
        self.company_model = self.registry('res.company')
        self.user_model = self.registry("res.users")
        self.payslip_model = self.registry("hr.payslip")
        self.worked_days_model = self.registry("hr.payslip.worked_days")
        self.contract_model = self.registry("hr.contract")
        self.policy_model = self.registry('hr.weekly.overtime.policy')
        self.policy_line_model = self.registry(
            'hr.weekly.overtime.policy.line')
        self.context = self.user_model.context_get(self.cr, self.uid)

        cr, uid, context = self.cr, self.uid, self.context

        create_activities(self)

        self.policy_id = self.policy_model.create(
            cr, uid, {'name': 'Policy 1'}, context=context)

        for line in [
            (40, 50, 150),
            (50, 60, 200),
            (60, False, 300),
        ]:
            self.policy_line_model.create(
                cr, uid, {
                    'policy_id': self.policy_id,
                    'min_hours': line[0],
                    'max_hours': line[1],
                    'rate': line[2],
                }, context=context)

        self.company_id = self.company_model.create(
            cr, uid, {
                'name': 'Company 1',
                'weekly_overtime_policy_id': self.policy_id,
                'week_start': '1',
            }, context=context)

        self.employee_ids = [
            self.employee_model.create(
                cr, uid, {
                    'name': employee[0],
                    'company_id': self.company_id,
                }, context=context)
            for employee in [
                ('Employee 1'),
                ('Employee 2'),
            ]
        ]
        self.contract_ids = [
            self.contract_model.create(
                cr, uid, {
                    'name': contract[0],
                    'employee_id': contract[1],
                    'wage': 50000,
                }, context=context)
            for contract in [
                ('Contract 1', self.employee_ids[0]),
                ('Contract 2', self.employee_ids[1]),
            ]
        ]

        self.payslip_ids = [
            self.payslip_model.create(
                cr, uid, {
                    'employee_id': payslip[0],
                    'contract_id': payslip[1],
                    'date_from': payslip[2],
                    'date_to': payslip[3],
                },
                context=context)
            for payslip in [
                (self.employee_ids[0], self.contract_ids[0],
                    '2015-01-01', '2015-01-31'),
                (self.employee_ids[0], self.contract_ids[0],
                    '2015-02-01', '2015-02-28'),
                (self.employee_ids[1], self.contract_ids[1],
                    '2015-01-01', '2015-01-31'),
                (self.employee_ids[1], self.contract_ids[1],
                    '2015-02-01', '2015-02-28'),
            ]
        ]

        create_worked_days(self, [
            ('2015-01-16', '2015-01-25', 100),
            ('2015-01-27', '2015-01-31', 50),
        ], payslip_id=self.payslip_ids[0], contract_id=self.contract_ids[0])
        create_worked_days(self, [
            ('2015-02-03', '2015-02-07', 50),
            ('2015-02-10', '2015-02-24', 150),
        ], payslip_id=self.payslip_ids[1], contract_id=self.contract_ids[0])

        # This worked days record will be ignored because it is a leave type
        create_worked_days(self, [
            ('2015-02-03', '2015-02-07', 75),
        ], payslip_id=self.payslip_ids[1], contract_id=self.contract_ids[0],
            activity_id=self.activity_leave_id)

        create_worked_days(self, [
            ('2015-01-27', '2015-01-31', 50),
        ], payslip_id=self.payslip_ids[2], contract_id=self.contract_ids[1])

        create_worked_days(self, [
            ('2015-02-03', '2015-02-07', 50),
        ], payslip_id=self.payslip_ids[3], contract_id=self.contract_ids[1])

        self.payslip_model.write(
            cr, uid, [self.payslip_ids[0], self.payslip_ids[2]],
            {'state': 'done'}, context=context)

    def assertEqual_worked_days(self, worked_days, values):
        self.assertEqual(worked_days.number_of_hours, values[0])
        self.assertEqual(worked_days.rate, values[1])
        self.assertEqual(worked_days.date_from, values[2])
        self.assertEqual(worked_days.date_to, values[3])

    def test_compute_weekly_overtime_policy(self):
        cr, uid, context = self.cr, self.uid, self.context
        self.payslip_model.compute_weekly_overtime_policy(
            cr, uid, [self.payslip_ids[1]], context=context)

        payslip = self.payslip_model.browse(
            cr, uid, self.payslip_ids[1], context=context)

        worked_days = [
            wd for wd in
            payslip.worked_days_line_ids
            if wd.activity_id.type == 'job'
        ]
        worked_days.sort(key=lambda wd: wd.date_from)

        self.assertEqual(len(worked_days), 10)

        self.assertEqual_worked_days(
            worked_days[0], (40, 100, '2015-02-03', '2015-02-07'))
        self.assertEqual_worked_days(
            worked_days[1], (10, 150, '2015-02-03', '2015-02-07'))

        self.assertEqual_worked_days(
            worked_days[2], (40, 100, '2015-02-10', '2015-02-15'))
        self.assertEqual_worked_days(
            worked_days[3], (10, 150, '2015-02-10', '2015-02-15'))
        self.assertEqual_worked_days(
            worked_days[4], (10, 200, '2015-02-10', '2015-02-15'))

        self.assertEqual_worked_days(
            worked_days[5], (40, 100, '2015-02-16', '2015-02-22'))
        self.assertEqual_worked_days(
            worked_days[6], (10, 150, '2015-02-16', '2015-02-22'))
        self.assertEqual_worked_days(
            worked_days[7], (10, 200, '2015-02-16', '2015-02-22'))
        self.assertEqual_worked_days(
            worked_days[8], (10, 300, '2015-02-16', '2015-02-22'))

        self.assertEqual_worked_days(
            worked_days[9], (20, 100, '2015-02-23', '2015-02-24'))

    def test_compute_weekly_overtime_policy_asynchrone_weeks(self):
        """
        Test weekly overtime with hours from the same week in another
        payslip
        """
        cr, uid, context = self.cr, self.uid, self.context

        # Start the week of work thursday instead of monday
        self.company_model.write(
            cr, uid, [self.company_id], {'week_start': '4'}, context=context)

        self.payslip_model.compute_weekly_overtime_policy(
            cr, uid, [self.payslip_ids[1]], context=context)

        payslip = self.payslip_model.browse(
            cr, uid, self.payslip_ids[1], context=context)

        worked_days = [
            wd for wd in
            payslip.worked_days_line_ids
            if wd.activity_id.type == 'job'
        ]
        worked_days.sort(key=lambda wd: wd.date_from)

        self.assertEqual_worked_days(
            worked_days[0], (10, 100, '2015-02-03', '2015-02-04'))
        self.assertEqual_worked_days(
            worked_days[1], (10, 150, '2015-02-03', '2015-02-04'))
        self.assertEqual_worked_days(
            worked_days[2], (30, 100, '2015-02-05', '2015-02-07'))

        self.assertEqual_worked_days(
            worked_days[3], (10, 100, '2015-02-10', '2015-02-11'))
        self.assertEqual_worked_days(
            worked_days[4], (10, 150, '2015-02-10', '2015-02-11'))

    def test_previous_payslip_not_completed(self):
        """
        Test that an error is raised if a payslip is computed while
        a previous payslip is still not completed
        """
        cr, uid, context = self.cr, self.uid, self.context

        self.payslip_model.write(
            cr, uid, [self.payslip_ids[0]],
            {'state': 'draft'}, context=context)

        self.assertRaises(
            except_orm,
            self.payslip_model.compute_weekly_overtime_policy,
            cr, uid, [self.payslip_ids[1]], context=context)

    def test_previous_payslip_cancelled(self):
        """
        Test that a payslip computes normally if a previous payslip
        was cancelled
        """
        cr, uid, context = self.cr, self.uid, self.context

        self.payslip_model.write(
            cr, uid, [self.payslip_ids[0]],
            {'state': 'cancel'}, context=context)

        self.payslip_model.compute_weekly_overtime_policy(
            cr, uid, [self.payslip_ids[1]], context=context)
