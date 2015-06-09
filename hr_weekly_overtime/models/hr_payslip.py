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
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _
from datetime import datetime, timedelta


class hr_payslip(orm.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self, cr, uid, ids, context=None):
        self.compute_weekly_overtime_policy(cr, uid, ids, context=context)
        super(hr_payslip, self).compute_sheet(
            cr, uid, ids, context=context)

    def compute_weekly_overtime_policy(
        self, cr, uid, ids, context=None
    ):
        """
        Apply the overtime policy to the worked days of a payslip.

        This method will first look for other payslips that may contain
        worked days in the same week as the current payslip being computed.
        In that case, the hours from the previous payslip will be taken
        into account for the calculations.
        """
        worked_days_obj = self.pool['hr.payslip.worked_days']
        for slip in self.browse(cr, uid, ids, context=context):

            if not slip.contract_id:
                raise orm.except_orm(
                    _("Error"),
                    _("There is no contract defined for the "
                        "payslip %s") % slip.name)

            # Search payslips that contain hours in the first week
            # of the current slip being computed
            today = datetime.strptime(
                slip.date_from, DEFAULT_SERVER_DATE_FORMAT)

            min_date_to = (today - timedelta(days=7)).strftime(
                DEFAULT_SERVER_DATE_FORMAT)

            related_slips = self.search(
                cr, uid, [
                    ('id', '!=', slip.id),
                    ('employee_id', '=', slip.employee_id.id),
                    ('company_id', '=', slip.company_id.id),
                    ('date_to', '>', min_date_to),
                    ('date_from', '<', slip.date_to),
                    ('state', '!=', 'cancel'),
                ], context=context)

            related_worked_days_ids = []

            for previous_slip in self.browse(
                    cr, uid, related_slips, context=context):
                if previous_slip.state != 'done':
                    raise orm.except_orm(
                        _('Error'),
                        _('You are attempting to compute weekly overtime '
                            'in a payslip, but there is another unfinished '
                            'payslip for employee %s') % slip.employee_id)
                for wd in previous_slip.worked_days_line_ids:
                    if wd.date_to > min_date_to:
                        related_worked_days_ids.append(wd.id)

            related_worked_days_ids += [
                wd.id for wd in slip.worked_days_line_ids
                if wd.activity_id.type == 'job'
            ]
            worked_days_obj.compute_weekly_overtime(
                cr, uid, related_worked_days_ids,
                contract_id=slip.contract_id.id,
                context=context)
