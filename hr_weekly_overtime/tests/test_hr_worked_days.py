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
from .test_hr_payslip import create_activities, create_worked_days


class test_hr_worked_days(common.TransactionCase):
    def setUp(self):
        super(test_hr_worked_days, self).setUp()
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

        self.company_id = self.company_model.create(
            cr, uid, {
                'name': 'Company 1',
                'weekly_overtime_policy_id': self.policy_id,
                'week_start': '3',
            }, context=context)

        self.employee_id = self.employee_model.create(
            cr, uid, {
                'name': 'Employee 1',
                'company_id': self.company_id,
            }, context=context)

        self.contract_id = self.contract_model.create(
            cr, uid, {
                'employee_id': self.employee_id,
                'name': 'Contract 1',
                'wage': 50000,
            },
            context=context)

        self.payslip_id = self.payslip_model.create(
            cr, uid, {
                'employee_id': self.employee_id,
                'contract_id': self.contract_id,
                'date_from': '2015-01-01',
                'date_to': '2015-01-31',
            },
            context=context)

        self.payslip_2_id = self.payslip_model.create(
            cr, uid, {
                'employee_id': self.employee_id,
                'contract_id': self.contract_id,
                'date_from': '2015-01-01',
                'date_to': '2015-01-31',
            },
            context=context)

        self.payslip_model.write(
            cr, uid, [self.payslip_2_id], {'state': 'done'},
            context=context)

    def test_split_by_week(self):
        cr, uid, context = self.cr, self.uid, self.context

        worked_days_id = self.worked_days_model.create(
            cr, uid, {
                # 18 days -> 10 hours each day
                'date_from': '2015-01-12',
                'date_to': '2015-01-29',
                'number_of_hours': 180,
                'hourly_rate': 25,
                'rate': 100,
                'payslip_id': self.payslip_id,
                'code': 'test',
                'name': 'test',
                'contract_id': self.contract_id,
            }, context=context)

        res = self.worked_days_model._split_by_week(
            cr, uid, worked_days_id, week_start='2015-01-07',
            context=context)

        self.assertEqual(len(res), 4)

        self.assertEqual(res[0][0], '2015-01-07')
        self.assertEqual(res[0][1].date_from, '2015-01-12')
        self.assertEqual(res[0][1].date_to, '2015-01-13')
        self.assertEqual(res[0][1].number_of_hours, 20)

        self.assertEqual(res[1][0], '2015-01-14')
        self.assertEqual(res[1][1].date_from, '2015-01-14')
        self.assertEqual(res[1][1].date_to, '2015-01-20')
        self.assertEqual(res[1][1].number_of_hours, 70)

        self.assertEqual(res[2][0], '2015-01-21')
        self.assertEqual(res[2][1].date_from, '2015-01-21')
        self.assertEqual(res[2][1].date_to, '2015-01-27')
        self.assertEqual(res[2][1].number_of_hours, 70)

        self.assertEqual(res[3][0], '2015-01-28')
        self.assertEqual(res[3][1].date_from, '2015-01-28')
        self.assertEqual(res[3][1].date_to, '2015-01-29')
        self.assertEqual(res[3][1].number_of_hours, 20)

    def search_worked_days(self, payslip_id=False, browse=False):
        cr, uid, context = self.cr, self.uid, self.context

        ids = self.worked_days_model.search(
            cr, uid, [
                ('payslip_id', '=', payslip_id or self.payslip_id),
            ], context=context)

        return browse and self.worked_days_model.browse(
            cr, uid, ids, context=context) or ids

    def create_policy_lines(self, values, browse=False):
        cr, uid, context = self.cr, self.uid, self.context

        ids = [
            self.policy_line_model.create(
                cr, uid, {
                    'policy_id': self.policy_id,
                    'min_hours': line[0],
                    'max_hours': line[1],
                    'rate': line[2],
                }, context=context)
            for line in values
        ]

        return browse and self.policy_line_model.browse(
            cr, uid, ids, context=context) or ids

    def test_group_by_week(self):
        cr, uid, context = self.cr, self.uid, self.context

        worked_days_ids = create_worked_days(self, [
            ('2015-01-12', '2015-01-18', 70),
            ('2015-01-19', '2015-01-29', 110),
        ])

        company = self.company_model.browse(
            cr, uid, self.company_id, context=context)

        res = self.worked_days_model._group_by_week(
            cr, uid, worked_days_ids, company,
            context=context)

        self.assertEqual(len(res), 4)

        self.assertEqual(res['2015-01-07'][0].date_from, '2015-01-12')
        self.assertEqual(res['2015-01-07'][0].date_to, '2015-01-13')
        self.assertEqual(res['2015-01-07'][0].number_of_hours, 20)

        self.assertEqual(res['2015-01-14'][0].date_from, '2015-01-14')
        self.assertEqual(res['2015-01-14'][0].date_to, '2015-01-18')
        self.assertEqual(res['2015-01-14'][0].number_of_hours, 50)

        self.assertEqual(res['2015-01-14'][1].date_from, '2015-01-19')
        self.assertEqual(res['2015-01-14'][1].date_to, '2015-01-20')
        self.assertEqual(res['2015-01-14'][1].number_of_hours, 20)

        self.assertEqual(res['2015-01-21'][0].date_from, '2015-01-21')
        self.assertEqual(res['2015-01-21'][0].date_to, '2015-01-27')
        self.assertEqual(res['2015-01-21'][0].number_of_hours, 70)

        self.assertEqual(res['2015-01-28'][0].date_from, '2015-01-28')
        self.assertEqual(res['2015-01-28'][0].date_to, '2015-01-29')
        self.assertEqual(res['2015-01-28'][0].number_of_hours, 20)

    def test_apply_overtime_policy(self):
        """
        Test the _apply_overtime_policy method with simple
        policy
        """
        cr, uid, context = self.cr, self.uid, self.context

        worked_days = create_worked_days(self, [
            ('2015-01-14', '2015-01-15', 40),
            ('2015-01-16', '2015-01-20', 30),
        ], browse=True)

        policy_lines = self.create_policy_lines([
            (40, 50, 150),
            (50, 60, 200),
            (60, False, 300),
        ], browse=True)

        self.worked_days_model._apply_overtime_policy(
            cr, uid, worked_days, policy_lines, context=context)

        worked_days = self.search_worked_days(browse=True)
        worked_days.sort(key=lambda wd: wd.rate)

        self.assertEqual(len(worked_days), 4)

        self.assertEqual(worked_days[0].number_of_hours, 40)
        self.assertEqual(worked_days[0].rate, 100)

        self.assertEqual(worked_days[1].number_of_hours, 10)
        self.assertEqual(worked_days[1].rate, 150)

        self.assertEqual(worked_days[2].number_of_hours, 10)
        self.assertEqual(worked_days[2].rate, 200)

        self.assertEqual(worked_days[3].number_of_hours, 10)
        self.assertEqual(worked_days[3].rate, 300)

    def test_apply_overtime_policy_abnormal(self):
        """
        Test the _apply_overtime_policy method with an abnormal
        policy
        """
        cr, uid, context = self.cr, self.uid, self.context

        worked_days = create_worked_days(self, [
            ('2015-01-16', '2015-01-20', 44),
            ('2015-01-14', '2015-01-15', 26),
        ], browse=True)

        policy_lines = self.create_policy_lines([
            (0, 20, 150),
            (35, 40, 75),
            (50, 62, 300),
        ], browse=True)

        self.worked_days_model._apply_overtime_policy(
            cr, uid, worked_days, policy_lines, context=context)

        worked_days = self.search_worked_days(browse=True)

        worked_days.sort(key=lambda wd: wd.number_of_hours)
        self.assertEqual(len(worked_days), 7)

        self.assertEqual(worked_days[0].number_of_hours, 5)
        self.assertEqual(worked_days[0].rate, 75)

        self.assertEqual(worked_days[1].number_of_hours, 6)
        self.assertEqual(worked_days[1].rate, 100)

        self.assertEqual(worked_days[2].number_of_hours, 8)
        self.assertEqual(worked_days[2].rate, 100)

        self.assertEqual(worked_days[3].number_of_hours, 9)
        self.assertEqual(worked_days[3].rate, 100)

        self.assertEqual(worked_days[4].number_of_hours, 10)
        self.assertEqual(worked_days[4].rate, 100)

        self.assertEqual(worked_days[5].number_of_hours, 12)
        self.assertEqual(worked_days[5].rate, 300)

        self.assertEqual(worked_days[6].number_of_hours, 20)
        self.assertEqual(worked_days[6].rate, 150)

    def test_apply_overtime_policy_previous_payslip(self):
        """
        Test the _apply_overtime_policy method with worked days
        from previous payslip
        """
        cr, uid, context = self.cr, self.uid, self.context

        worked_days = create_worked_days(self, [
            ('2015-01-14', '2015-01-15', 5, self.payslip_2_id),
            ('2015-01-16', '2015-01-17', 35, self.payslip_id),
            ('2015-01-18', '2015-01-20', 30, self.payslip_id),
        ], browse=True)

        policy_lines = self.create_policy_lines([
            (40, 50, 150),
            (50, False, 200),
        ], browse=True)

        self.worked_days_model._apply_overtime_policy(
            cr, uid, worked_days, policy_lines, context=context)

        worked_days = self.search_worked_days(browse=True)
        worked_days.sort(key=lambda wd: wd.number_of_hours)

        self.assertEqual(len(worked_days), 4)

        self.assertEqual(worked_days[0].number_of_hours, 5)
        self.assertEqual(worked_days[0].rate, 100)

        self.assertEqual(worked_days[1].number_of_hours, 10)
        self.assertEqual(worked_days[1].rate, 150)

        self.assertEqual(worked_days[2].number_of_hours, 20)
        self.assertEqual(worked_days[2].rate, 200)

        self.assertEqual(worked_days[3].number_of_hours, 35)
        self.assertEqual(worked_days[3].rate, 100)
