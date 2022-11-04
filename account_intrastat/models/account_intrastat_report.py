# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.tools import get_lang

from datetime import datetime
from collections import defaultdict

_merchandise_export_code = {
    'BE': '29',
    'FR': '21',
    'NL': '7',
}

_merchandise_import_code = {
    'BE': '19',
    'FR': '11',
    'NL': '6',
}

_unknown_country_code = {
    'BE': 'QU',
    'NL': 'QV',
}

_qn_unknown_individual_vat_country_codes = ('FI', 'SE', 'SK', 'DE', 'AT')


class IntrastatReportCustomHandler(models.AbstractModel):
    _name = 'account.intrastat.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Intrastat Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        # dict of the form {move_id: {column_group_key: {expression_label: value}}}
        move_info_dict = {}

        # dict of the form {column_group_key: total_value}
        total_values_dict = {}

        # Build query
        query_list = []
        full_query_params = []
        for column_group_key, column_group_options in report._split_options_per_column_group(options).items():
            query, params = self._prepare_query(column_group_options, column_group_key)
            query_list.append(f"({query})")
            full_query_params += params

        full_query = " UNION ALL ".join(query_list)
        self._cr.execute(full_query, full_query_params)
        results = self._cr.dictfetchall()

        # Fill dictionaries
        for result in self._fill_missing_values(results):
            move_id = result['id']
            column_group_key = result['column_group_key']

            current_move_info = move_info_dict.setdefault(move_id, {})

            current_move_info[column_group_key] = result
            current_move_info['name'] = result['name']

            total_values_dict.setdefault(column_group_key, 0)
            total_values_dict[column_group_key] += result['value']

        # Create lines
        lines = []
        for move_id, move_info in move_info_dict.items():
            line = self._create_report_line(options, move_info, move_id, ['value'])
            lines.append((0, line))

        # Create total line if only one type of invoice is selected
        if options.get('intrastat_total_line'):
            total_line = self._create_report_total_line(options, total_values_dict)
            lines.append((0, total_line))
        return lines

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        previous_options = previous_options or {}

        # Filter only partners with VAT
        options['intrastat_with_vat'] = previous_options.get('intrastat_with_vat', False)

        # Filter types of invoices
        default_type = [
            {'name': _('Arrival'), 'selected': False, 'id': 'arrival'},
            {'name': _('Dispatch'), 'selected': False, 'id': 'dispatch'},
        ]
        options['intrastat_type'] = previous_options.get('intrastat_type', default_type)
        options['country_format'] = previous_options.get('country_format')
        options['commodity_flow'] = previous_options.get('commodity_flow')

        # Filter the domain based on the types of invoice selected
        include_arrivals = options['intrastat_type'][0]['selected']
        include_dispatches = options['intrastat_type'][1]['selected']
        if not include_arrivals and not include_dispatches:
            include_arrivals = include_dispatches = True

        invoice_types = []
        if include_arrivals:
            invoice_types += ['in_invoice', 'out_refund']
        if include_dispatches:
            invoice_types += ['out_invoice', 'in_refund']

        # When only one type is selected, we can display a total line
        options['intrastat_total_line'] = include_arrivals != include_dispatches
        options.setdefault('forced_domain', []).append(('move_id.move_type', 'in', invoice_types))

        # Filter report type (extended form)
        options['intrastat_extended'] = previous_options.get('intrastat_extended', True)

        # 2 columns are conditional and should only appear when rendering the extended intrastat report
        # Some countries don't use the region code column; we hide it for them.
        excluded_columns = set()
        if not options['intrastat_extended']:
            excluded_columns |= {'transport_code', 'incoterm_code'}
        if not self._show_region_code():
            excluded_columns.add('region_code')

        new_columns = []
        for col in options['columns']:
            if col['expression_label'] not in excluded_columns:
                new_columns.append(col)

                # Replace country names by codes if necessary (for file exports)
                if options.get('country_format') == 'code':
                    if col['expression_label'] == 'country_name':
                        col['expression_label'] = 'country_code'
                    elif col['expression_label'] == 'intrastat_product_origin_country_name':
                        col['expression_label'] = 'intrastat_product_origin_country_code'

        # Only pick Sale/Purchase journals (+ divider)
        report._init_options_journals(options, previous_options=previous_options, additional_journals_domain=[('type', 'in', ('sale', 'purchase'))])

        # When printing the report to xlsx, we want to use country codes instead of names
        xlsx_button_option = next(button_opt for button_opt in options['buttons'] if button_opt.get('action_param') == 'export_to_xlsx')
        xlsx_button_option['action_param'] = 'export_to_xlsx'

    def _caret_options_initializer(self):
        """ Add a caret option for navigating from an intrastat report line to the associated journal entry """
        return {'account.move.line': [{'name': _("View Journal Entry"), 'action': 'caret_option_open_record_form', 'action_param': 'move_id'}]}

    ####################################################
    # OVERRIDES
    ####################################################

    def _show_region_code(self):
        """Return a bool indicating if the region code is to be displayed for the country concerned in this localisation."""
        # TO OVERRIDE
        return True

    ####################################################
    # OPTIONS: INIT
    ####################################################

    def export_to_xlsx(self, options, response=None):
        # We need to regenerate the options to make sure we hide the country name columns as expected.
        report = self.env['account.report'].browse(options['report_id'])
        new_options = report._get_options(previous_options={**options, 'country_format': 'code', 'commodity_flow': 'code'})
        return report.export_to_xlsx(new_options, response=response)

    ####################################################
    # REPORT LINES: CORE
    ####################################################

    @api.model
    def _create_report_line(self, options, line_vals, line_id, number_values):
        """ Create a standard (non-total) line for the report

        :param options: report options
        :param line_vals: values necessary for the line
        :param line_id: id of the line
        :param number_values: list of expression labels that need to have the 'number' class
        """
        report = self.env['account.report']
        columns = []
        for column in options['columns']:
            expression_label = column['expression_label']
            value = line_vals.get(column['column_group_key'], {}).get(expression_label, False)

            if options.get('commodity_flow') != 'code' and column['expression_label'] == 'system':
                value = f"{value} ({line_vals.get(column['column_group_key'], {}).get('type', False)})"

            columns.append({
                'name': report.format_value(value, figure_type=column['figure_type']) if value else None,
                'no_format': value,
                'class': 'number' if expression_label in number_values else '',
            })

        errors = (
            ('expired_trans', 'move_line_id'),
            ('premature_trans', 'move_line_id'),
            ('missing_trans', 'move_line_id'),
            ('expired_comm', 'product_id'),
            ('premature_comm', 'product_id'),
            ('missing_comm', 'product_id'),
            ('missing_unit', 'product_id'),
            ('missing_weight', 'product_id'),
        )
        for column_group in options['column_groups']:
            for error, val_key in errors:
                if line_vals.get(column_group) and line_vals[column_group].get(error):
                    options.setdefault('intrastat_warnings', defaultdict(list))
                    options['intrastat_warnings'][error].append(line_vals[column_group][val_key])
        return {
            'id': report._get_generic_line_id('account.move.line', line_id),
            'caret_options': 'account.move.line',
            'name': line_vals['name'],
            'columns': columns,
            'level': 2,
        }

    @api.model
    def _create_report_total_line(self, options, total_vals):
        """ Create a total line for the report

        :param options: report options
        :param total_vals: total values dict
        """
        report = self.env['account.report']
        columns = []
        for column in options['columns']:
            expression_label = column['expression_label']
            value = total_vals.get(column['column_group_key'], {}).get(expression_label, False)

            columns.append({
                'name': report.format_value(value, figure_type=column['figure_type']) if value else None,
                'no_format': value,
                'class': 'number',
            })
        return {
            'id': report._get_generic_line_id(None, None, markup='total'),
            'name': _('Total'),
            'class': 'total',
            'level': 1,
            'columns': columns,
        }

    ####################################################
    # REPORT LINES: QUERY
    ####################################################

    @api.model
    def _prepare_query(self, options, column_group_key=None):
        query_blocks, where_params = self._build_query(options, column_group_key)
        query = f"{query_blocks['select']} {query_blocks['from']} {query_blocks['where']} {query_blocks['order']}"
        return query, where_params

    @api.model
    def _build_query(self, options, column_group_key=None):
        # triangular use cases are handled by letting the intrastat_country_id editable on
        # invoices. Modifying or emptying it allow to alter the intrastat declaration
        # accordingly to specs (https://www.nbb.be/doc/dq/f_pdf_ex/intra2017fr.pdf (§ 4.x))
        tables, where_clause, where_params = self.env['account.report'].browse(options['report_id'])._query_get(options, 'strict_range')

        import_merchandise_code = _merchandise_import_code.get(self.env.company.country_id.code, '29')
        export_merchandise_code = _merchandise_export_code.get(self.env.company.country_id.code, '19')
        unknown_individual_vat = 'QN999999999999' if self.env.company.country_id.code in _qn_unknown_individual_vat_country_codes else 'QV999999999999'
        unknown_country_code = _unknown_country_code.get(self.env.company.country_id.code, 'QV')
        weight_category_id = self.env['ir.model.data']._xmlid_to_res_id('uom.product_uom_categ_kgm')

        select = f"""
            SELECT
                %s AS column_group_key,
                row_number() over () AS sequence,
                CASE WHEN account_move.move_type IN ('in_invoice', 'out_refund') THEN %s ELSE %s END AS system,
                country.code AS country_code,
                COALESCE(country.name->>'{self.env.user.lang or get_lang(self.env).code}', country.name->>'en_US') AS country_name,
                company_country.code AS comp_country_code,
                transaction.code AS transaction_code,
                company_region.code AS region_code,
                code.code AS commodity_code,
                account_move_line.id AS id,
                prodt.id AS template_id,
                prodt.categ_id AS category_id,
                account_move_line.product_uom_id AS uom_id,
                inv_line_uom.category_id AS uom_category_id,
                account_move.id AS invoice_id,
                account_move_line.id as move_line_id,
                account_move.currency_id AS invoice_currency_id,
                account_move.name,
                COALESCE(account_move.date, account_move.invoice_date) AS invoice_date,
                account_move.move_type AS invoice_type,
                COALESCE(inv_incoterm.code, comp_incoterm.code) AS incoterm_code,
                COALESCE(inv_transport.code, comp_transport.code) AS transport_code,
                CASE WHEN account_move.move_type IN ('in_invoice', 'out_refund') THEN 'Arrival' ELSE 'Dispatch' END AS type,
                partner.vat as partner_vat,
                ROUND(
                    prod.weight * account_move_line.quantity / (
                        CASE WHEN inv_line_uom.category_id IS NULL OR inv_line_uom.category_id = prod_uom.category_id
                        THEN inv_line_uom.factor ELSE 1 END
                    ) * (
                        CASE WHEN prod_uom.uom_type <> 'reference'
                        THEN prod_uom.factor ELSE 1 END
                    ),
                    SCALE(ref_weight_uom.rounding)
                ) AS weight,
                account_move_line.quantity / (
                    CASE WHEN inv_line_uom.category_id IS NULL OR inv_line_uom.category_id = prod_uom.category_id
                    THEN inv_line_uom.factor ELSE 1 END
                ) AS quantity,
                CASE WHEN code.supplementary_unit IS NOT NULL and prod.intrastat_supplementary_unit_amount != 0
                    THEN prod.intrastat_supplementary_unit_amount * (
                        quantity / (
                            CASE WHEN inv_line_uom.category_id IS NULL OR inv_line_uom.category_id = prod_uom.category_id
                            THEN inv_line_uom.factor ELSE 1 END
                        )
                    ) ELSE NULL END AS supplementary_units,
                account_move_line.quantity AS line_quantity,
                CASE WHEN account_move_line.price_subtotal = 0 THEN account_move_line.price_unit * account_move_line.quantity ELSE account_move_line.price_subtotal END AS value,
                COALESCE(product_country.code, %s) AS intrastat_product_origin_country_code,
                COALESCE(product_country.name->>'{self.env.user.lang or get_lang(self.env).code}', product_country.name->>'en_US') AS intrastat_product_origin_country_name,
                CASE WHEN partner.vat IS NOT NULL THEN partner.vat
                     WHEN partner.vat IS NULL AND partner.is_company IS FALSE THEN %s
                     ELSE 'QV999999999999'
                END AS partner_vat,
                transaction.expiry_date <= account_move.invoice_date AS expired_trans,
                transaction.start_date > account_move.invoice_date AS premature_trans,
                transaction.id IS NULL AS missing_trans,
                code.expiry_date <= account_move.invoice_date AS expired_comm,
                code.start_date > account_move.invoice_date AS premature_comm,
                code.id IS NULL as missing_comm,
                COALESCE(prod.intrastat_supplementary_unit_amount, 0) = 0 AND code.supplementary_unit IS NOT NULL as missing_unit,
                COALESCE(prod.weight, 0) = 0 AND code.supplementary_unit IS NULL AS missing_weight,
                prod.id AS product_id,
                prodt.categ_id AS template_categ
        """
        from_ = f"""
            FROM
                {tables}
                JOIN account_move ON account_move.id = account_move_line.move_id
                LEFT JOIN account_intrastat_code transaction ON account_move_line.intrastat_transaction_id = transaction.id
                LEFT JOIN res_company company ON account_move.company_id = company.id
                LEFT JOIN account_intrastat_code company_region ON company.intrastat_region_id = company_region.id
                LEFT JOIN res_partner partner ON account_move_line.partner_id = partner.id
                LEFT JOIN res_partner comp_partner ON company.partner_id = comp_partner.id
                LEFT JOIN res_country country ON account_move.intrastat_country_id = country.id
                LEFT JOIN res_country company_country ON comp_partner.country_id = company_country.id
                INNER JOIN product_product prod ON account_move_line.product_id = prod.id
                LEFT JOIN product_template prodt ON prod.product_tmpl_id = prodt.id
                LEFT JOIN account_intrastat_code code ON code.id = prod.intrastat_code_id
                LEFT JOIN uom_uom inv_line_uom ON account_move_line.product_uom_id = inv_line_uom.id
                LEFT JOIN uom_uom prod_uom ON prodt.uom_id = prod_uom.id
                LEFT JOIN account_incoterms inv_incoterm ON account_move.invoice_incoterm_id = inv_incoterm.id
                LEFT JOIN account_incoterms comp_incoterm ON company.incoterm_id = comp_incoterm.id
                LEFT JOIN account_intrastat_code inv_transport ON account_move.intrastat_transport_mode_id = inv_transport.id
                LEFT JOIN account_intrastat_code comp_transport ON company.intrastat_transport_mode_id = comp_transport.id
                LEFT JOIN res_country product_country ON product_country.id = account_move_line.intrastat_product_origin_country_id
                LEFT JOIN res_country partner_country ON partner.country_id = partner_country.id AND partner_country.intrastat IS TRUE
                LEFT JOIN uom_uom ref_weight_uom on ref_weight_uom.category_id = %s and ref_weight_uom.uom_type = 'reference'
        """
        where = f"""
            WHERE
                {where_clause}
                AND (account_move_line.price_subtotal != 0 OR account_move_line.price_unit * account_move_line.quantity != 0)
                AND company_country.id != country.id
                AND country.intrastat = TRUE AND (country.code != 'GB' OR account_move.date < '2021-01-01')
                AND prodt.type != 'service'
        """
        order = "ORDER BY account_move.invoice_date DESC, account_move_line.id"

        if options['intrastat_with_vat']:
            where += " AND partner.vat IS NOT NULL "

        query = {
            'select': select,
            'from': from_,
            'where': where,
            'order': order,
        }

        query_params = [
            column_group_key,
            import_merchandise_code,
            export_merchandise_code,
            unknown_country_code,
            unknown_individual_vat,
            weight_category_id,
            *where_params
        ]

        return query, query_params

    ####################################################
    # REPORT LINES: HELPERS
    ####################################################

    @api.model
    def _fill_missing_values(self, vals_list):
        """ Some values are too complex to be retrieved in the SQL query.
        Then, this method is used to compute the missing values fetched from the database.
        :param vals_list:    A dictionary created by the dictfetchall method.
        """
        for vals in vals_list:
            # Check the currency.
            currency_id = self.env['res.currency'].browse(vals['invoice_currency_id'])
            company_currency_id = self.env.company.currency_id
            if currency_id != company_currency_id:
                vals['value'] = currency_id._convert(vals['value'], company_currency_id, self.env.company, vals['invoice_date'])

        return vals_list

    ####################################################
    # ACTIONS
    ####################################################

    def action_invalid_code_moves(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invalid transaction intrastat code entries.'),
            'res_model': 'account.move.line',
            'views': [(
                self.env.ref('account_intrastat.account_move_line_tree_view_account_intrastat_transaction_codes').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', options['intrastat_warnings'][params['option_key']])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    def action_invalid_code_products(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Invalid commodity intrastat code products.'),
            'res_model': 'product.product',
            'views': [(
                self.env.ref('account_intrastat.product_product_tree_view_account_intrastat').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', options['intrastat_warnings'][params['option_key']])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    def action_undefined_units_products(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Undefined supplementary unit products.'),
            'res_model': 'product.product',
            'views': [(
                self.env.ref('account_intrastat.product_product_tree_view_account_intrastat_supplementary_unit').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', options['intrastat_warnings'][params['option_key']])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }

    def action_undefined_weight_products(self, options, params):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Undefined weight products.'),
            'res_model': 'product.product',
            'views': [(
                self.env.ref('account_intrastat.product_product_tree_view_account_intrastat_weight').id,
                'list',
            ), (False, 'form')],
            'domain': [('id', 'in', options['intrastat_warnings'][params['option_key']])],
            'context': {
                'create': False,
                'delete': False,
                'expand': True,
            },
        }
