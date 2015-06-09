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
from itertools import permutations


class hr_weekly_overtime_policy(orm.Model):
    _name = 'hr.weekly.overtime.policy'
    _description = 'Weekly Overtime Policy'

    _columns = {
        'name': fields.char(
            'Policy Name', required=True
        ),
        'line_ids': fields.one2many(
            'hr.weekly.overtime.policy.line',
            'policy_id',
            string='Weekly Overtime Lines',
        ),
    }

    def _check_overlapping_lines(self, cr, uid, ids, context=None):
        """
        Check that no overtime policy line overlaps any other
        """
        for policy in self.browse(cr, uid, ids, context=context):
            for r1, r2 in permutations(policy.line_ids, 2):
                if r1.max_hours and (
                        r1.min_hours <= r2.min_hours < r1.max_hours):
                    return False
                elif not r1.max_hours and (r1.min_hours <= r2.min_hours):
                    return False
        return True

    _constraints = [(
        _check_overlapping_lines,
        'Error! You cannot have overlapping hours for a policy',
        ['line_ids']
    )]
