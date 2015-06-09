# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Savoir-faire Linux. All Rights Reserved.
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

from openerp.osv import orm
from itertools import chain
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta
strptime = datetime.strptime
strftime = datetime.strftime


class hr_payslip_worked_days(orm.Model):
    _inherit = 'hr.payslip.worked_days'

    def _split_by_week(
        self, cr, uid, ids, week_start, context=None
    ):
        """
        Split a worked day record by week
        :param ids: a single worked_days ids
        :param week_start: a date in default server format prior or equal
            to the given worked_days's date_from
        :return: a list of worked_days records
        """
        if isinstance(ids, (int, long)):
            ids = [ids]

        wd = self.browse(cr, uid, ids[0], context=context)
        res = [(week_start, wd)]

        next_week_start = strptime(
            week_start, DEFAULT_SERVER_DATE_FORMAT) + timedelta(days=7)
        wd_date_to = strptime(wd.date_to, DEFAULT_SERVER_DATE_FORMAT)

        while wd_date_to >= next_week_start:
            wd_date_from = strptime(wd.date_from, DEFAULT_SERVER_DATE_FORMAT)

            days_count = (wd_date_to - wd_date_from).days + 1
            days_before = (next_week_start - wd_date_from).days
            days_after = days_count - days_before

            # Split the number of hours into 2
            hours_before = wd.number_of_hours * days_before / days_count
            hours_after = wd.number_of_hours * days_after / days_count

            next_week_str = next_week_start.strftime(
                DEFAULT_SERVER_DATE_FORMAT)

            new_wd_values = self.copy_data(cr, uid, wd.id, {
                'date_from': next_week_str,
                'number_of_hours': hours_after,
            })
            new_worked_day_id = self.create(
                cr, uid, new_wd_values, context=context)

            wd.write({
                'date_to': (next_week_start - timedelta(days=1)).strftime(
                    DEFAULT_SERVER_DATE_FORMAT),
                'number_of_hours': hours_before,
            })

            wd.refresh()

            wd = self.browse(cr, uid, new_worked_day_id, context=context)
            res.append((next_week_str, wd))

            next_week_start += timedelta(days=7)

        return res

    def _group_by_week(
        self, cr, uid, ids, company, context=None
    ):
        """
        Group worked days by week
        :param ids: worked days ids from a single payslip
        """
        first_day = int(company.week_start)
        worked_days = self.browse(cr, uid, ids, context=context)
        week_start = company.week_start

        wd_tuples = []

        for wd in worked_days:
            worked_days_from = strptime(
                wd.date_from, DEFAULT_SERVER_DATE_FORMAT)
            work_days_num = int(strftime(worked_days_from, '%w'))

            weekdays_passed = work_days_num - first_day

            if first_day > work_days_num:
                weekdays_passed += 7

            # Get the first day of the week
            week_start = (
                worked_days_from - timedelta(days=weekdays_passed)
            ).strftime(DEFAULT_SERVER_DATE_FORMAT)
            wd_tuples.append((week_start, wd))

        worked_days = list(chain(*[
            wd._split_by_week(wd_week_start)
            for wd_week_start, wd in wd_tuples
        ]))

        res = {}

        for wd_week_start, wd in worked_days:
            if wd_week_start in res:
                res[wd_week_start].append(wd)
            else:
                res[wd_week_start] = [wd]

        return res

    def _apply_overtime_policy(
        self, cr, uid, worked_days, policy_lines, context=None
    ):
        """
        Apply an overtime policy to a list of worked days.

        :param worked_days: a list of worked days browse records
        :param policy_lines: a list of overtime policy line
            browse records
        """
        if not policy_lines:
            return

        worked_days.sort(key=lambda wd: wd.date_from)

        line_count = 0
        current_line = policy_lines[0]

        hours_count = sum([
            wd.number_of_hours for wd in worked_days
            if wd.payslip_id.state == 'done'
        ])
        wd_count = 0

        while len(worked_days) > wd_count:
            wd = worked_days[wd_count]

            if wd.payslip_id.state == 'done':
                wd_count += 1
                continue

            previous_hours_count = hours_count
            hours_count += wd.number_of_hours

            if hours_count <= current_line.min_hours:
                wd.write({'rate': 100})

            elif previous_hours_count < current_line.min_hours:

                # Create a new worked days record and insert it
                new_wd_values = self.copy_data(
                    cr, uid, wd.id, {
                        'number_of_hours': hours_count - current_line.min_hours
                    }, context=context)
                new_wd_id = self.create(
                    cr, uid, new_wd_values, context=context)
                new_wd = self.browse(cr, uid, new_wd_id, context=context)
                worked_days.insert(wd_count + 1, new_wd)

                # Update the current worked days
                wd.write({
                    'number_of_hours': wd.number_of_hours
                    - new_wd.number_of_hours,
                    'rate': 100,
                })

                hours_count = current_line.min_hours

            elif not current_line.max_hours:
                # Update the current worked days
                wd.write({'rate': current_line.rate})

            elif hours_count > current_line.max_hours:

                # Create a new worked days record and insert it
                new_wd_values = self.copy_data(
                    cr, uid, wd.id, {
                        'number_of_hours': hours_count - current_line.max_hours
                    }, context=context)
                new_wd_id = self.create(
                    cr, uid, new_wd_values, context=context)
                new_wd = self.browse(cr, uid, new_wd_id, context=context)
                worked_days.insert(wd_count + 1, new_wd)

                # Update the current worked days
                wd.write({
                    'number_of_hours': wd.number_of_hours
                    - new_wd.number_of_hours,
                    'rate': current_line.rate,
                })

                hours_count = current_line.max_hours

            else:
                wd.write({'rate': current_line.rate})

            if hours_count >= current_line.max_hours:

                # Point on another policy line
                line_count += 1

                if len(policy_lines) <= line_count:
                    break

                current_line = policy_lines[line_count]

            wd_count += 1

    def compute_weekly_overtime(
        self, cr, uid, ids, contract_id, context=None
    ):
        """
        Apply the weekly overtime policy of the contract to a set of
        worked days

        :param ids: worked days ids from payslips all related to the
        same employee
        """
        contract = self.pool['hr.contract'].browse(
            cr, uid, contract_id, context=context)

        policy = contract.get_weekly_overtime_policy()

        if not policy or not policy.line_ids:
            return

        policy_lines = sorted([
            line for line in policy.line_ids
        ], key=lambda line: line.min_hours)

        worked_days_by_week = self._group_by_week(
            cr, uid, ids, contract.employee_id.company_id, context=context)

        for week in worked_days_by_week:
            self._apply_overtime_policy(
                cr, uid, worked_days_by_week[week], policy_lines,
                context=context)
