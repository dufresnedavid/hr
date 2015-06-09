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

from openerp.osv import fields, orm


class hr_weekly_overtime_policy_line(orm.Model):
    _name = 'hr.weekly.overtime.policy.line'
    _description = 'Weekly Overtime Policy Line'

    _columns = {
        'policy_id': fields.many2one(
            'hr.weekly.overtime.policy',
            'Policy',
            required=True,
            ondelete='cascade',
        ),
        'min_hours': fields.float(
            'Lower Limit',
            digits=(2, 2),
            required=True,
        ),
        'max_hours': fields.float(
            'Upper Limit',
            digits=(2, 2),
        ),
        'rate': fields.float(
            'Rate',
            required=True,
            help="The rate by which multiply the hourly rate of an employee"
        ),
    }
