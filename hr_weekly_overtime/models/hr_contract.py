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

from openerp.osv import orm, fields
from openerp.tools.translate import _


class hr_contract(orm.Model):
    _inherit = 'hr.contract'

    _columns = {
        'weekly_overtime_policy_id': fields.many2one(
            'hr.weekly.overtime.policy',
            'Weekly Overtime Policy',
        ),
    }

    def get_weekly_overtime_policy(
        self, cr, uid, ids, context=None
    ):
        """
        Get the overtime policy for a contract. If none is found,
        check if there is one for the employee's department or
        company

        :return: a hr.weekly.overtime.policy browse record
        """
        contract = self.browse(cr, uid, ids[0], context=context)

        if contract.weekly_overtime_policy_id:
            return contract.weekly_overtime_policy_id

        company = contract.employee_id.company_id

        if company.weekly_overtime_policy_id:
            return company.weekly_overtime_policy_id

        raise orm.except_orm(
            _("Error"),
            _("There is no weekly overtime policy defined for the "
                "employee %s") % contract.employee_id.name)
