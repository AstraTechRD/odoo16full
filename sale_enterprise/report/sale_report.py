# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.osv.expression import expression


class SaleReport(models.Model):
    _inherit = 'sale.report'

    avg_days_to_confirm = fields.Float(
        'Average Days To Confirm', readonly=True, store=False,  # needs store=False to prevent showing up as a 'measure' option
        help="Average days to confirm a sales order after its creation. Due to a hack needed to calculate this, \
              every record will show the same average value, therefore only use this as an aggregated value with group_operator=avg")
    invoice_status = fields.Selection([
        ('upselling', 'Upselling Opportunity'),
        ('invoiced', 'Fully Invoiced'),
        ('to invoice', 'To Invoice'),
        ('no', 'Nothing to Invoice')
        ], string="Invoice Status", readonly=True)

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res['invoice_status'] = "s.invoice_status"
        return res

    def _group_by_sale(self):
        res = super()._group_by_sale()
        res += """,
            s.invoice_status"""
        return res

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ This is a hack to allow us to correctly calculate the average of SO specific date values since
            the normal report query result will duplicate SO values across its SO lines during joins and
            lead to incorrect aggregation values.

            Only the AVG operator is supported for avg_days_to_confirm.
        """
        avg_days_to_confirm = next((field for field in fields if re.search(r'\bavg_days_to_confirm\b', field)), False)

        if avg_days_to_confirm:
            fields.remove(avg_days_to_confirm)
            if any(field.split(':')[1].split('(')[0] != 'avg' for field in [avg_days_to_confirm] if field):
                raise UserError("Value: 'avg_days_to_confirm' should only be used to show an average. If you are seeing this message then it is being accessed incorrectly.")

        res = []
        if fields:
            res = super(SaleReport, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

        if not res and avg_days_to_confirm:
            res = [{}]

        if avg_days_to_confirm:
            query = """ SELECT AVG(days_to_confirm.so_days_to_confirm)::decimal(16,2) AS avg_days_to_confirm
                          FROM (
                              SELECT DATE_PART('day', s.date_order::timestamp - s.create_date::timestamp) AS so_days_to_confirm
                              FROM sale_order s
                              WHERE s.id IN (
                                  SELECT "sale_report"."order_id" FROM %s WHERE %s)
                              ) AS days_to_confirm
                    """

            # NB: date_order is named date in sale.report
            subdomain = domain + [('company_id', '=', self.env.company.id), ('date', '!=', False)]
            subtables, subwhere, subparams = expression(subdomain, self).query.get_sql()

            self.env.cr.execute(query % (subtables, subwhere), subparams)
            res[0].update({
                '__count': 1,
                avg_days_to_confirm.split(':')[0]: self.env.cr.fetchall()[0][0],
            })
        return res
