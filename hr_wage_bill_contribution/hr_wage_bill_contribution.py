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

from openerp.osv import orm, fields
from datetime import datetime
from openerp import netsvc
from openerp.tools.translate import _
from openerp.addons.hr_payroll.hr_payroll import one2many_mod2


class PayrollBrowsableObject(object):
    """
    The same as in hr_payroll module
    Don't know why they put it inline in the get_contribution_lines
    function
    Not very practical when you need to inherit the object
    """
    def __init__(self, pool, cr, uid, dict):
        self.pool = pool
        self.cr = cr
        self.uid = uid
        self.dict = dict

    def __getattr__(self, attr):
        return attr in self.dict and self.dict.__getitem__(attr) or 0.0


class PayslipsBrowsableObject(PayrollBrowsableObject):
    """
    Similar as in hr_payroll module
    """
    def __init__(self, pool, cr, uid, company_id, dict):
        self.company_id = company_id
        super(PayslipsBrowsableObject, self).__init__(
            pool, cr, uid, dict
        )

    def sum(self, code, from_date, to_date=None):
        if to_date is None:
            to_date = datetime.now().strftime('%Y-%m-%d')
        self.cr.execute(
            "SELECT sum( \
                case when hp.credit_note = False \
                then (pl.total) else (-pl.total) end \
            )\
            FROM hr_payslip as hp, hr_payslip_line as pl \
            WHERE hp.company_id = %s \
            AND hp.state = 'done' \
            AND hp.date_from >= %s \
            AND hp.date_to <= %s \
            AND hp.id = pl.slip_id \
            AND pl.code = %s",
            (self.company_id.id, from_date, to_date, code)
        )
        res = self.cr.fetchone()
        return res and res[0] or 0.0


class hr_wage_bill_contribution(orm.Model):
    """
    This model allows to compute amounts over the wage bill of a company
    for a period of time.
    """
    _name = 'hr.wage.bill.contribution'
    _inherit = 'hr.payslip'
    _columns = {
        'line_ids': one2many_mod2(
            'hr.wage.bill.contribution.line',
            'contribution_id',
            'Contribution Lines',
            readonly=True,
            states={
                'draft': [('readonly', False)]
            }
        ),
        'details_by_salary_rule': fields.one2many(
            'hr.wage.bill.contribution.line',
            'contribution_id',
            'Contribution Lines',
            readonly=True,
            states={
                'draft': [('readonly', False)]
            }
        ),
    }

    def onchange_struct_id(
        self, cr, uid, ids,
        struct_id,
        context=None,
    ):
        structure = self.pool['hr.payroll.structure'].browse(
            cr, uid, struct_id, context=context
        )
        return {
            'value': {
                'name': _('Contribution to %s') % structure.name
            }
        }

    def refund_sheet(self, cr, uid, ids, context=None):
        """
        The same refund_sheet function as in hr_payroll but
         - returns a different view
         - triggers the hr.wage.bill.contribution workflow
        """
        mod_obj = self.pool.get('ir.model.data')
        wf_service = netsvc.LocalService("workflow")

        # Create the refund and trigger the workflows
        for contribution in self.browse(cr, uid, ids, context=context):
            id_copy = self.copy(
                cr, uid, contribution.id,
                {
                    'credit_note': True,
                    'name': _('Refund: ') + contribution.name
                },
                context=context
            )
            self.compute_sheet(cr, uid, [id_copy], context=context)
            wf_service.trg_validate(
                uid, 'hr.wage.bill.contribution',
                id_copy, 'hr_verify_sheet', cr
            )
            wf_service.trg_validate(
                uid, 'hr.wage.bill.contribution',
                id_copy, 'process_sheet', cr
            )

        # Get the form and tree views
        form_id = mod_obj.get_object_reference(
            cr, uid,
            'hr_wage_bill_contribution',
            'view_hr_wage_bill_contribution_form'
        )
        form_res = form_id and form_id[1] or False

        tree_id = mod_obj.get_object_reference(
            cr, uid,
            'hr_wage_bill_contribution',
            'view_hr_wage_bill_contribution_tree'
        )
        tree_res = tree_id and tree_id[1] or False

        return {
            'name': _("Refund"),
            'view_mode': 'tree, form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'hr.wage.bill.contribution',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'domain': "[('id', 'in', %s)]" % [id_copy],
            'views': [(tree_res, 'tree'), (form_res, 'form')],
            'context': {}
        }

    def unlink(self, cr, uid, ids, context=None):
        for contribution in self.browse(cr, uid, ids, context=context):
            if contribution.state not in ['draft', 'cancel']:
                raise orm.except_orm(
                    _('Warning!'),
                    _("""\
You cannot delete a wage bill contribution which is not draft or cancelled!""")
                )
        return super(hr_wage_bill_contribution, self).unlink(
            cr, uid, ids, context
        )

    def compute_sheet(self, cr, uid, ids, context=None):
        line_obj = self.pool['hr.wage.bill.contribution.line']
        for contribution in self.browse(cr, uid, ids, context=context):

            # Delete old contribution lines
            old_slipline_ids = line_obj.search(
                cr, uid,
                [('contribution_id', '=', contribution.id)],
                context=context
            )
            if old_slipline_ids:
                line_obj.unlink(
                    cr, uid,
                    old_slipline_ids,
                    context=context
                )

            # Compute new lines
            lines = [
                (0, 0, line)
                for line in self.get_contribution_lines(
                    cr, uid,
                    contribution.id,
                    contribution.struct_id.id,
                    context=context
                )
            ]

            # Write new lines
            self.write(
                cr, uid,
                [contribution.id],
                {
                    'line_ids': lines,
                },
                context=context
            )

        return True

    def _sum_salary_rule_category(
        self, cr, uid, localdict, category, amount
    ):
        """
        The same as in hr_payroll but as a method
        Don't know why they put it inline in hr_payroll
        """
        if category.parent_id:
            localdict = self._sum_salary_rule_category(
                cr, uid,
                localdict,
                category.parent_id,
                amount
            )
        localdict['categories'].dict[category.code] = (
            category.code in localdict['categories'].dict) and (
            localdict['categories'].dict[category.code] + amount or amount
        )
        return localdict

    def get_contribution_lines(
        self, cr, uid,
        contribution_id,
        structure_id,
        context=None,
    ):
        # we keep a dict with the result because a value can be overwritten by
        # another rule with the same code
        result_dict = {}
        rules = {}
        payslips = {}
        categories_dict = {}
        obj_rule = self.pool.get('hr.salary.rule')

        contribution_obj = self.pool.get('hr.wage.bill.contribution')
        contribution = contribution_obj.browse(
            cr, uid, contribution_id, context=context
        )

        # browsable objects for local dictionary
        contribution_obj = PayrollBrowsableObject(
            self.pool, cr, uid, contribution
        )
        categories_obj = PayrollBrowsableObject(
            self.pool, cr, uid, categories_dict
        )
        payslip_obj = PayslipsBrowsableObject(
            self.pool, cr, uid, contribution.company_id, payslips,
        )
        rules_obj = PayrollBrowsableObject(self.pool, cr, uid, rules)

        localdict = {
            'contribution': contribution_obj,
            'categories': categories_obj,
            'payslip': payslip_obj,
            'rules': rules_obj,
        }

        # get the ids structure and its parents
        structure_ids = list(set(self.pool.get(
            'hr.payroll.structure'
        )._get_parent_structure(
            cr, uid, [structure_id], context=context
        )))

        # get the rules of the structure and thier children
        rule_ids = self.pool.get('hr.payroll.structure').get_all_rules(
            cr, uid, structure_ids, context=context
        )

        # run the rules by sequence
        sorted_rule_ids = [
            id for id, sequence in sorted(rule_ids, key=lambda x:x[1])
        ]

        blacklist = []

        for rule in obj_rule.browse(
            cr, uid,
            sorted_rule_ids,
            context=context
        ):
            localdict['result'] = None
            localdict['result_qty'] = 1.0
            localdict['result_rate'] = 100

            # check if the rule can be applied
            if obj_rule.satisfy_condition(
                cr, uid, rule.id, localdict, context=context
            ) and rule.id not in blacklist:

                # compute the amount of the rule
                amount, qty, rate = obj_rule.compute_rule(
                    cr, uid, rule.id, localdict, context=context
                )

                # check if there is already a rule computed with that code
                previous_amount = rule.code in localdict and \
                    localdict[rule.code] or 0.0

                # set/overwrite the amount computed
                # for this rule in the localdict
                tot_rule = amount * qty * rate / 100.0
                localdict[rule.code] = tot_rule
                rules[rule.code] = rule

                # sum the amount for its salary category
                localdict = self._sum_salary_rule_category(
                    cr, uid,
                    localdict,
                    rule.category_id,
                    tot_rule - previous_amount
                )

                # create/overwrite the rule in the temporary results
                result_dict[rule.code] = {
                    'salary_rule_id': rule.id,
                    'name': rule.name,
                    'code': rule.code,
                    'category_id': rule.category_id.id,
                    'sequence': rule.sequence,
                    'appears_on_payslip': rule.appears_on_payslip,
                    'condition_select': rule.condition_select,
                    'condition_python': rule.condition_python,
                    'condition_range': rule.condition_range,
                    'condition_range_min': rule.condition_range_min,
                    'condition_range_max': rule.condition_range_max,
                    'amount_select': rule.amount_select,
                    'amount_fix': rule.amount_fix,
                    'amount_python_compute': rule.amount_python_compute,
                    'amount_percentage': rule.amount_percentage,
                    'amount_percentage_base': rule.amount_percentage_base,
                    'register_id': rule.register_id.id,
                    'amount': amount,
                    'quantity': qty,
                    'rate': rate,
                }
            else:
                # blacklist this rule and its children
                # This may happens when the structure has recursive rules
                # with conditions
                blacklist += [id for id, seq in self.pool.get(
                    'hr.salary.rule'
                )._recursive_search_of_rules(
                    cr, uid, [rule], context=context
                )]

        result = [value for code, value in result_dict.items()]
        return result
