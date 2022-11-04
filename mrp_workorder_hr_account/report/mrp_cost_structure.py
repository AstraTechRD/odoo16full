# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models


class MrpCostStructure(models.AbstractModel):
    _inherit = 'report.mrp_account_enterprise.mrp_cost_structure'

    def get_lines(self, productions):
        lines = super().get_lines(productions)
        currency_table = self.env['res.currency']._get_query_currency_table({'multi_company': True, 'date': {'date_to': fields.Date.today()}})
        employee_times = self.env['mrp.workcenter.productivity'].search([
            ('production_id', 'in', productions.ids),
            ('employee_id', '!=', False),
        ])
        if employee_times:
            query_str = """SELECT
                                wo.product_id,
                                emp.name,
                                t.employee_cost,
                                op.id,
                                wo.name,
                                sum(t.duration),
                                currency_table.rate
                            FROM mrp_workcenter_productivity t
                            LEFT JOIN mrp_workorder wo ON (wo.id = t.workorder_id)
                            LEFT JOIN mrp_routing_workcenter op ON (wo.operation_id = op.id)
                            LEFT JOIN {currency_table} ON currency_table.company_id = t.company_id
                            LEFT JOIN hr_employee emp ON t.employee_id = emp.id
                            WHERE t.workorder_id IS NOT NULL AND t.employee_id IS NOT NULL AND wo.production_id IN %s
                            GROUP BY product_id, emp.id, op.id, wo.name, t.employee_cost, currency_table.rate
                            ORDER BY emp.name
                        """.format(currency_table=currency_table,)
            self.env.cr.execute(query_str, (tuple(productions.ids), ))
            empl_cost_by_product = defaultdict(list)
            for product, employee_name, employee_cost, op_id, wo_name, duration, currency_rate in self.env.cr.fetchall():
                cost = employee_cost * currency_rate
                empl_cost_by_product[product].append([employee_name, op_id, wo_name, duration / 60.0, cost * currency_rate])
            for product_lines in lines:
                product_lines['operations'] += empl_cost_by_product.get(product_lines['product'].id, [])
        return lines
