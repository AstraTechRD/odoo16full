# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression


class EventSaleReport(models.Model):
    _inherit = 'event.sale.report'

    avg_amount_sale_order = fields.Float("Average Sale Order Amount", store=False)
    avg_daily_registrations = fields.Float("Average Daily Registrations", store=False)
    avg_sold_daily_registrations = fields.Float("Average Daily Registrations Sold", store=False)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """ Freely adapted from sale_report. Hack to allow us to correctly calculate some values that
        would otherwise be erroneously computed.

        Only the AVG operator is supported for these additional model fields.
        """
        read_group_fields, special_fields = self._extract_special_fields(fields)

        res = [self._get_special_values(special_fields, domain) if special_fields else {}]
        if read_group_fields:
            res_read_group = super().read_group(
                domain, read_group_fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
            res[0].update(res_read_group[0])
            res = res[:1] + res_read_group[1:]
        return res

    def _get_special_values(self, special_template_fields, domain):
        subdomain = expression.AND([domain, [('company_id', '=', self.env.company.id)]])
        subtables, subwhere, subparams = expression.expression(subdomain, self).query.get_sql()

        with_sales_kpis = {'avg_amount_sale_order', 'avg_sold_daily_registrations'} & special_template_fields.keys()
        optional_sales_kpis_union = '' if not with_sales_kpis else """
       UNION ALL
          SELECT count(*), AVG(s.amount_total)::decimal(16,2)
            FROM sale_order s 
            JOIN registrations 
              ON registrations.sale_order_id = s.id"""

        query = f"""
            WITH registrations AS (
                 SELECT "event_sale_report"."sale_order_id", "event_sale_report"."event_registration_create_date" 
                   FROM {subtables} 
                  WHERE {subwhere}
            )
          SELECT count(*),
                 max(registrations.event_registration_create_date)::date - min(registrations.event_registration_create_date)::date + 1
            FROM registrations
            {optional_sales_kpis_union}
        """

        self.env.cr.execute(query, subparams)
        n_registrations_created, n_days_created = self.env.cr.fetchone()
        if not n_days_created:
            return {}
        values = {'__count': 1}
        if 'avg_daily_registrations' in special_template_fields.keys():
            values[special_template_fields['avg_daily_registrations']] = n_registrations_created / n_days_created

        if with_sales_kpis:
            n_registrations_sold, avg_amount_sale_order = self.env.cr.fetchone()
            if 'avg_amount_sale_order' in special_template_fields.keys():
                values[special_template_fields['avg_amount_sale_order']] = avg_amount_sale_order
            if 'avg_sold_daily_registrations' in special_template_fields.keys():
                values[special_template_fields['avg_sold_daily_registrations']] = n_registrations_sold / n_days_created
        return values

    @staticmethod
    def _extract_special_fields(read_group_fields):
        """Returns the "normal" fields as well as a mapping of these special model fields requested
        to the name used on template."""
        special_fields_regex = r'(avg_amount_sale_order|avg_daily_registrations|avg_sold_daily_registrations)'
        read_group_fields_filtered = []
        special_fields = {}

        for field in read_group_fields:
            special_field_match = re.search(special_fields_regex, field)
            if not special_field_match:
                read_group_fields_filtered.append(field)
                continue
            model_field_name = special_field_match.groups()[0]
            if f'avg({model_field_name})' not in field:
                raise UserError(
                    f"Value: '{model_field_name}' should only be used to show an average. "
                    f"If you are seeing this message then it is being accessed incorrectly.")
            # Pair model field with template field name
            special_fields[model_field_name] = field.split(':')[0]
        return read_group_fields_filtered, special_fields
