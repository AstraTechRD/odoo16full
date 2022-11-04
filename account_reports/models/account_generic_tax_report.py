# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import models, api, fields, Command, _
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import UserError, RedirectWarning
from odoo.osv import expression
from odoo.tools.misc import get_lang


class GenericTaxReportCustomHandler(models.AbstractModel):
    _name = 'account.generic.tax.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Generic Tax Report Custom Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        return self._get_dynamic_lines(report, options, 'default')

    def _caret_options_initializer(self):
        return {
            'generic_tax_report': [
                {'name': _("Audit"), 'action': 'caret_option_audit_tax'},
            ]
        }

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['buttons'].append({'name': _('Closing Entry'), 'action': 'action_periodic_vat_entries', 'sequence': 80})

    def _get_dynamic_lines(self, report, options, grouping):
        """ Compute the report lines for the generic tax report.

        :param options: The report options.
        :return:        A list of lines, each one being a python dictionary.
        """
        options_by_column_group = report._split_options_per_column_group(options)

        # Compute tax_base_amount / tax_amount for each selected groupby.
        if grouping == 'tax_account':
            groupby_fields = [('src_tax', 'type_tax_use'), ('src_tax', 'id'), ('account', 'id')]
            comodels = [None, 'account.tax', 'account.account']
        elif grouping == 'account_tax':
            groupby_fields = [('src_tax', 'type_tax_use'), ('account', 'id'), ('src_tax', 'id')]
            comodels = [None, 'account.account', 'account.tax']
        else:
            groupby_fields = [('src_tax', 'type_tax_use'), ('src_tax', 'id')]
            comodels = [None, 'account.tax']

        tax_amount_hierarchy = self._read_generic_tax_report_amounts(report, options_by_column_group, groupby_fields)

        # Fetch involved records in order to ensure all lines are sorted according the comodel order.
        # To do so, we compute 'sorting_map_list' allowing to retrieve each record by id and the order
        # to be used.
        record_ids_gb = [set() for dummy in groupby_fields]

        def populate_record_ids_gb_recursively(node, level=0):
            for k, v in node.items():
                if k:
                    record_ids_gb[level].add(k)
                    populate_record_ids_gb_recursively(v['children'], level=level + 1)

        populate_record_ids_gb_recursively(tax_amount_hierarchy)

        sorting_map_list = []
        for i, comodel in enumerate(comodels):
            if comodel:
                # Relational records.
                records = self.env[comodel].with_context(active_test=False).search([('id', 'in', tuple(record_ids_gb[i]))])
                sorting_map = {r.id: (r, j) for j, r in enumerate(records)}
                sorting_map_list.append(sorting_map)
            else:
                # src_tax_type_tax_use.
                selection = self.env['account.tax']._fields['type_tax_use'].selection
                sorting_map_list.append({v[0]: (v, j) for j, v in enumerate(selection) if v[0] in record_ids_gb[i]})

        # Compute report lines.
        lines = []
        self._populate_lines_recursively(
            report,
            options,
            lines,
            sorting_map_list,
            groupby_fields,
            tax_amount_hierarchy,
        )
        return lines

    # -------------------------------------------------------------------------
    # GENERIC TAX REPORT COMPUTATION (DYNAMIC LINES)
    # -------------------------------------------------------------------------

    def _read_generic_tax_report_amounts(self, report, options_by_column_group, groupby_fields):
        """ Read the tax details to compute the tax amounts.

        :param options_list:    The list of report options, one for each period.
        :param groupby_fields:  A list of tuple (alias, field) representing the way the amounts must be grouped.
        :return:                A dictionary mapping each groupby key (e.g. a tax_id) to a sub dictionary containing:

            base_amount:    The tax base amount expressed in company's currency.
            tax_amount      The tax amount expressed in company's currency.
            children:       The children nodes following the same pattern as the current dictionary.
        """
        fetch_group_of_taxes = False

        select_clause_list = []
        groupby_query_list = []
        for alias, field in groupby_fields:
            select_clause_list.append(f'{alias}.{field} AS {alias}_{field}')
            groupby_query_list.append(f'{alias}.{field}')

            # Fetch both info from the originator tax and the child tax to manage the group of taxes.
            if alias == 'src_tax':
                select_clause_list.append(f'tax.{field} AS tax_{field}')
                groupby_query_list.append(f'tax.{field}')
                fetch_group_of_taxes = True

        select_clause_str = ','.join(select_clause_list)
        groupby_query_str = ','.join(groupby_query_list)

        # Fetch the group of taxes.
        # If all children taxes are 'none', all amounts are aggregated and only the group will appear on the report.
        # If some children taxes are not 'none', the children are displayed.
        group_of_taxes_to_expand = set()
        if fetch_group_of_taxes:
            group_of_taxes = self.env['account.tax'].with_context(active_test=False).search([('amount_type', '=', 'group')])
            for group in group_of_taxes:
                if set(group.children_tax_ids.mapped('type_tax_use')) != {'none'}:
                    group_of_taxes_to_expand.add(group.id)

        res = {}
        for column_group_key, options in options_by_column_group.items():
            tables, where_clause, where_params = report._query_get(options, 'strict_range')
            tax_details_query, tax_details_params = self.env['account.move.line']._get_query_tax_details(tables, where_clause, where_params)

            # Avoid adding multiple times the same base amount sharing the same grouping_key.
            # It could happen when dealing with group of taxes for example.
            row_keys = set()

            self._cr.execute(f'''
                SELECT
                    {select_clause_str},
                    trl.refund_tax_id IS NOT NULL AS is_refund,
                    SUM(tdr.base_amount) AS base_amount,
                    SUM(tdr.tax_amount) AS tax_amount
                FROM ({tax_details_query}) AS tdr
                JOIN account_tax_repartition_line trl ON trl.id = tdr.tax_repartition_line_id
                JOIN account_tax tax ON tax.id = tdr.tax_id
                JOIN account_tax src_tax ON
                    src_tax.id = COALESCE(tdr.group_tax_id, tdr.tax_id)
                    AND src_tax.type_tax_use IN ('sale', 'purchase')
                JOIN account_account account ON account.id = tdr.base_account_id
                WHERE tdr.tax_exigible
                GROUP BY tdr.tax_repartition_line_id, trl.refund_tax_id, {groupby_query_str}
                ORDER BY src_tax.sequence, src_tax.id, tax.sequence, tax.id
            ''', tax_details_params)

            for row in self._cr.dictfetchall():
                node = res

                # tuple of values used to prevent adding multiple times the same base amount.
                cumulated_row_key = [row['is_refund']]

                for alias, field in groupby_fields:
                    grouping_key = f'{alias}_{field}'

                    # Manage group of taxes.
                    # In case the group of taxes is mixing multiple taxes having a type_tax_use != 'none', consider
                    # them instead of the group.
                    if grouping_key == 'src_tax_id' and row['src_tax_id'] in group_of_taxes_to_expand:
                        # Add the originator group to the grouping key, to make sure that its base amount is not
                        # treated twice, for hybrid cases where a tax is both used in a group and independently.
                        cumulated_row_key.append(row[grouping_key])

                        # Ensure the child tax is used instead of the group.
                        grouping_key = 'tax_id'

                    row_key = row[grouping_key]
                    cumulated_row_key.append(row_key)
                    cumulated_row_key_tuple = tuple(cumulated_row_key)

                    node.setdefault(row_key, {
                        'base_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                        'tax_amount': {column_group_key: 0.0 for column_group_key in options['column_groups']},
                        'children': {},
                    })
                    sub_node = node[row_key]

                    # Add amounts.
                    if cumulated_row_key_tuple not in row_keys:
                        sub_node['base_amount'][column_group_key] += row['base_amount']
                    sub_node['tax_amount'][column_group_key] += row['tax_amount']

                    node = sub_node['children']
                    row_keys.add(cumulated_row_key_tuple)

        return res

    def _populate_lines_recursively(self, report, options, lines, sorting_map_list, groupby_fields, values_node, index=0, type_tax_use=None, parent_line_id=None):
        ''' Populate the list of report lines passed as parameter recursively. At this point, every amounts is already
        fetched for every periods and every groupby.

        :param options:             The report options.
        :param lines:               The list of report lines to populate.
        :param sorting_map_list:    A list of dictionary mapping each encountered key with a weight to sort the results.
        :param index:               The index of the current element to process (also equals to the level into the hierarchy).
        :param groupby_fields:      A list of tuple <alias, field> defining in which way tax amounts should be grouped.
        :param values_node:         The node containing the amounts and children into the hierarchy.
        :param type_tax_use:        The type_tax_use of the tax.
        :param parent_line_id:      The line id of the parent line (if any)
        '''
        if index == len(groupby_fields):
            return

        alias, field = groupby_fields[index]
        groupby_key = f'{alias}_{field}'

        # Sort the keys in order to add the lines in the same order as the records.
        sorting_map = sorting_map_list[index]
        sorted_keys = sorted(list(values_node.keys()), key=lambda x: sorting_map[x][1])

        for key in sorted_keys:

            # Compute 'type_tax_use' with the first grouping since 'src_tax_type_tax_use' is always
            # the first one.
            if groupby_key == 'src_tax_type_tax_use':
                type_tax_use = key
            sign = -1 if type_tax_use == 'sale' else 1

            # Prepare columns.
            tax_amount_dict = values_node[key]
            columns = []
            tax_base_amounts = tax_amount_dict['base_amount']
            tax_amounts = tax_amount_dict['tax_amount']
            for column_group in options['column_groups']:
                tax_base_amount = tax_base_amounts[column_group]
                tax_amount = tax_amounts[column_group]

                # Add the tax base amount.
                if index == len(groupby_fields) - 1:
                    columns.append({
                       'no_format': sign * tax_base_amount,
                       'name': report.format_value(sign * tax_base_amount, figure_type='monetary'),
                       'style': 'white-space:nowrap;',
                    })
                else:
                    columns.append({'name': '', 'style': 'white-space:nowrap;',})

                # Add the tax amount.
                columns.append({
                   'no_format': sign * tax_amount,
                   'name': report.format_value(sign * tax_amount, figure_type='monetary'),
                   'style': 'white-space:nowrap;',
                })

            # Prepare line.
            default_vals = {
                'columns': columns,
                'level': index + 1,
                'unfoldable': False,
            }
            report_line = self._build_report_line(report, options, default_vals, groupby_key, sorting_map[key][0], parent_line_id)

            if groupby_key == 'src_tax_id':
                report_line['caret_options'] = 'generic_tax_report'

            lines.append((0, report_line))

            # Process children recursively.
            self._populate_lines_recursively(
                report,
                options,
                lines,
                sorting_map_list,
                groupby_fields,
                tax_amount_dict.get('children'),
                index=index + 1,
                type_tax_use=type_tax_use,
                parent_line_id=report_line['id'],
            )

    def _build_report_line(self, report, options, default_vals, groupby_key, value, parent_line_id):
        """ Build the report line accordingly to its type.
        :param options:         The report options.
        :param default_vals:    The pre-computed report line values.
        :param groupby_key:     The grouping_key record.
        :param value:           The value that could be a record.
        :param parent_line_id   The line id of the parent line (if any, can be None otherwise)
        :return:                A python dictionary.
        """
        report_line = dict(default_vals)
        if parent_line_id is not None:
            report_line['parent_id'] = parent_line_id

        if groupby_key == 'src_tax_type_tax_use':
            type_tax_use_option = value
            report_line['id'] = report._get_generic_line_id(None, None, markup=type_tax_use_option[0], parent_line_id=parent_line_id)
            report_line['name'] = type_tax_use_option[1]

        elif groupby_key == 'src_tax_id':
            tax = value
            report_line['id'] = report._get_generic_line_id(tax._name, tax.id, parent_line_id=parent_line_id)

            if tax.amount_type == 'percent':
                report_line['name'] = f"{tax.name} ({tax.amount}%)"
            elif tax.amount_type == 'fixed':
                report_line['name'] = f"{tax.name} ({tax.amount})"
            else:
                report_line['name'] = tax.name

            if options.get('multi-company'):
                report_line['name'] = f"{report_line['name']} - {tax.company_id.display_name}"

        elif groupby_key == 'account_id':
            account = value
            report_line['id'] = report._get_generic_line_id(account._name, account.id, parent_line_id=parent_line_id)

            if options.get('multi-company'):
                report_line['name'] = f"{account.display_name} - {account.company_id.display_name}"
            else:
                report_line['name'] = account.display_name

        return report_line

     # -------------------------------------------------------------------------
     # BUTTONS & CARET OPTIONS
     # -------------------------------------------------------------------------

    def caret_option_audit_tax(self, options, params):
        report = self.env.ref('account.generic_tax_report')
        model, tax_id = report._get_model_info_from_id(params['line_id'])

        if model != 'account.tax':
            raise UserError(_("Cannot audit tax from another model than account.tax."))

        tax = self.env['account.tax'].browse(tax_id)

        if tax.amount_type == 'group':
            tax_affecting_base_domain = [
                ('tax_ids', 'in', tax.children_tax_ids.ids),
                ('tax_repartition_line_id', '!=', False),
            ]
        else:
            tax_affecting_base_domain = [
                ('tax_ids', '=', tax.id),
                ('tax_ids.type_tax_use', '=', tax.type_tax_use),
                ('tax_repartition_line_id', '!=', False),
            ]

        domain = report._get_options_domain(options, 'strict_range') + expression.OR((
            # Base lines
            [
                ('tax_ids', 'in', tax.ids),
                ('tax_ids.type_tax_use', '=', tax.type_tax_use),
                ('tax_repartition_line_id', '=', False),
            ],
            # Tax lines
            [
                ('group_tax_id', '=', tax.id) if tax.amount_type == 'group' else ('tax_line_id', '=', tax.id),
            ],
            # Tax lines acting as base lines
            tax_affecting_base_domain,
        ))

        ctx = self._context.copy()
        ctx.update({'search_default_group_by_account': 2, 'expand': 1})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Items for Tax Audit'),
            'res_model': 'account.move.line',
            'views': [[self.env.ref('account.view_move_line_tax_audit_tree').id, 'list'], [False, 'form']],
            'domain': domain,
            'context': ctx,
        }

     # -------------------------------------------------------------------------
     # TAX CLOSING
     # -------------------------------------------------------------------------

    def action_periodic_vat_entries(self, options):
        # Return action to open form view of newly entry created
        report = self.env.ref('account.generic_tax_report')
        moves = self._generate_tax_closing_entries(report, options)
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action = clean_action(action, env=self.env)
        if len(moves) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = moves.id
        else:
            action['domain'] = [('id', 'in', moves.ids)]
        return action

    def _generate_tax_closing_entries(self, report, options, closing_moves=None):
        """Generates and/or updates VAT closing entries.

        This method computes the content of the tax closing in the following way:
        - Search on all tax lines in the given period, group them by tax_group (each tax group might have its own
        tax receivable/payable account).
        - Create a move line that balances each tax account and add the difference in the correct receivable/payable
        account. Also take into account amounts already paid via advance tax payment account.

        The tax closing is done so that an individual move is created per available VAT number: so, one for each
        foreign vat fiscal position (each with fiscal_position_id set to this fiscal position), and one for the domestic
        position (with fiscal_position_id = None). The moves created by this function hence depends on the content of the
        options dictionary, and what fiscal positions are accepted by it.

        :param options: the tax report options dict to use to make the closing.
        :param closing_moves: If provided, closing moves to update the content from.
                              They need to be compatible with the provided options (if they have a fiscal_position_id, for example).

        :return: The closing moves.
        """
        options_company_ids = [company_opt['id'] for company_opt in options.get('multi_company', [])]
        companies = self.env['res.company'].browse(options_company_ids) if options_company_ids else self.env.company
        end_date = fields.Date.from_string(options['date']['date_to'])

        closing_moves_by_company = defaultdict(lambda: self.env['account.move'])
        if closing_moves:
            for move in closing_moves.filtered(lambda x: x.state == 'draft'):
                closing_moves_by_company[move.company_id] |= move
        else:
            closing_moves = self.env['account.move']
            for company in companies:
                include_domestic, fiscal_positions = self._get_fpos_info_for_tax_closing(company, report, options)
                company_closing_moves = company._get_and_update_tax_closing_moves(end_date, fiscal_positions=fiscal_positions, include_domestic=include_domestic)
                closing_moves_by_company[company] = company_closing_moves
                closing_moves += company_closing_moves

        for company, company_closing_moves in closing_moves_by_company.items():

            # First gather the countries for which the closing is being done
            countries = self.env['res.country']
            for move in company_closing_moves:
                if move.fiscal_position_id.foreign_vat:
                    countries |= move.fiscal_position_id.country_id
                else:
                    countries |= company.account_fiscal_country_id

            # Check the tax groups from the company for any misconfiguration in these countries
            if self.env['account.tax.group']._check_misconfigured_tax_groups(company, countries):
                self._redirect_to_misconfigured_tax_groups(company, countries)

            if company.tax_lock_date and company.tax_lock_date >= end_date:
                raise UserError(_("This period is already closed for company %s", company.name))

            for move in company_closing_moves:
                # get tax entries by tax_group for the period defined in options
                move_options = {**options, 'fiscal_position': move.fiscal_position_id.id if move.fiscal_position_id else 'domestic'}
                line_ids_vals, tax_group_subtotal = self._compute_vat_closing_entry(company, move_options)

                line_ids_vals += self._add_tax_group_closing_items(tax_group_subtotal, end_date)

                if move.line_ids:
                    line_ids_vals += [Command.delete(aml.id) for aml in move.line_ids]

                move_vals = {}
                if line_ids_vals:
                    move_vals['line_ids'] = line_ids_vals

                move_vals['tax_report_control_error'] = bool(move_options.get('tax_report_control_error'))

                move.write(move_vals)

        return closing_moves

    @api.model
    def _compute_vat_closing_entry(self, company, options):
        """Compute the VAT closing entry.

        This method returns the one2many commands to balance the tax accounts for the selected period, and
        a dictionnary that will help balance the different accounts set per tax group.
        """
        self = self.with_company(company) # Needed to handle access to property fields correctly

        # first, for each tax group, gather the tax entries per tax and account
        self.env['account.tax'].flush_model(['name', 'tax_group_id'])
        self.env['account.tax.repartition.line'].flush_model(['use_in_tax_closing'])
        self.env['account.move.line'].flush_model(['account_id', 'debit', 'credit', 'move_id', 'tax_line_id', 'date', 'company_id', 'display_type'])
        self.env['account.move'].flush_model(['state'])

        # Check whether it is multilingual, in order to get the translation from the JSON value if present
        lang = self.env.user.lang or get_lang(self.env).code
        tax_name = f"COALESCE(tax.name->>'{lang}', tax.name->>'en_US')" if \
            self.pool['account.tax'].name.translate else 'tax.name'

        sql = f"""
            SELECT "account_move_line".tax_line_id as tax_id,
                    tax.tax_group_id as tax_group_id,
                    {tax_name} as tax_name,
                    "account_move_line".account_id,
                    COALESCE(SUM("account_move_line".balance), 0) as amount
            FROM account_tax tax, account_tax_repartition_line repartition, %s
            WHERE %s
              AND tax.id = "account_move_line".tax_line_id
              AND repartition.id = "account_move_line".tax_repartition_line_id
              AND repartition.use_in_tax_closing
            GROUP BY tax.tax_group_id, "account_move_line".tax_line_id, tax.name, "account_move_line".account_id
        """

        new_options = {
            **options,
            'all_entries': False,
            'date': dict(options['date']),
            'multi_company': [{'id': company.id, 'name': company.name}],
        }

        period_start, period_end = company._get_tax_closing_period_boundaries(fields.Date.from_string(options['date']['date_to']))
        new_options['date']['date_from'] = fields.Date.to_string(period_start)
        new_options['date']['date_to'] = fields.Date.to_string(period_end)

        tables, where_clause, where_params = self.env.ref('account.generic_tax_report')._query_get(
            new_options,
            'strict_range',
            domain=self._get_vat_closing_entry_additional_domain()
        )
        query = sql % (tables, where_clause)
        self.env.cr.execute(query, where_params)
        results = self.env.cr.dictfetchall()

        tax_group_ids = [r['tax_group_id'] for r in results]
        tax_groups = {}
        for tg, result in zip(self.env['account.tax.group'].browse(tax_group_ids), results):
            if tg not in tax_groups:
                tax_groups[tg] = {}
            if result.get('tax_id') not in tax_groups[tg]:
                tax_groups[tg][result.get('tax_id')] = []
            tax_groups[tg][result.get('tax_id')].append((result.get('tax_name'), result.get('account_id'), result.get('amount')))

        # then loop on previous results to
        #    * add the lines that will balance their sum per account
        #    * make the total per tax group's account triplet
        # (if 2 tax groups share the same 3 accounts, they should consolidate in the vat closing entry)
        move_vals_lines = []
        tax_group_subtotal = {}
        currency = self.env.company.currency_id
        for tg, values in tax_groups.items():
            total = 0
            # ignore line that have no property defined on tax group
            if not tg.property_tax_receivable_account_id or not tg.property_tax_payable_account_id:
                continue
            for dummy, value in values.items():
                for v in value:
                    tax_name, account_id, amt = v
                    # Line to balance
                    move_vals_lines.append((0, 0, {'name': tax_name, 'debit': abs(amt) if amt < 0 else 0, 'credit': amt if amt > 0 else 0, 'account_id': account_id}))
                    total += amt

            if not currency.is_zero(total):
                # Add total to correct group
                key = (tg.property_advance_tax_payment_account_id.id or False, tg.property_tax_receivable_account_id.id, tg.property_tax_payable_account_id.id)

                if tax_group_subtotal.get(key):
                    tax_group_subtotal[key] += total
                else:
                    tax_group_subtotal[key] = total

        # If the tax report is completely empty, we add two 0-valued lines, using the first in in and out
        # account id we find on the taxes.
        if len(move_vals_lines) == 0:
            rep_ln_in = self.env['account.tax.repartition.line'].search([
                ('account_id.deprecated', '=', False),
                ('repartition_type', '=', 'tax'),
                ('company_id', '=', company.id),
                ('invoice_tax_id.type_tax_use', '=', 'purchase')
            ], limit=1)
            rep_ln_out = self.env['account.tax.repartition.line'].search([
                ('account_id.deprecated', '=', False),
                ('repartition_type', '=', 'tax'),
                ('company_id', '=', company.id),
                ('invoice_tax_id.type_tax_use', '=', 'sale')
            ], limit=1)

            if rep_ln_out.account_id and rep_ln_in.account_id:
                move_vals_lines = [
                    Command.create({
                        'name': _('Tax Received Adjustment'),
                        'debit': 0,
                        'credit': 0.0,
                        'account_id': rep_ln_out.account_id.id
                    }),

                    Command.create({
                        'name': _('Tax Paid Adjustment'),
                        'debit': 0.0,
                        'credit': 0,
                        'account_id': rep_ln_in.account_id.id
                    })
                ]

        return move_vals_lines, tax_group_subtotal

    def _get_vat_closing_entry_additional_domain(self):
        return []

    @api.model
    def _add_tax_group_closing_items(self, tax_group_subtotal, end_date):
        """Transform the parameter tax_group_subtotal dictionnary into one2many commands.

        Used to balance the tax group accounts for the creation of the vat closing entry.
        """
        def _add_line(account, name, company_currency):
            self.env.cr.execute(sql_account, (account, end_date))
            result = self.env.cr.dictfetchone()
            advance_balance = result.get('balance') or 0
            # Deduct/Add advance payment
            if not company_currency.is_zero(advance_balance):
                line_ids_vals.append((0, 0, {
                    'name': name,
                    'debit': abs(advance_balance) if advance_balance < 0 else 0,
                    'credit': abs(advance_balance) if advance_balance > 0 else 0,
                    'account_id': account
                }))
            return advance_balance

        currency = self.env.company.currency_id
        sql_account = '''
            SELECT SUM(aml.balance) AS balance
            FROM account_move_line aml
            LEFT JOIN account_move move ON move.id = aml.move_id
            WHERE aml.account_id = %s
              AND aml.date <= %s
              AND move.state = 'posted'
        '''
        line_ids_vals = []
        # keep track of already balanced account, as one can be used in several tax group
        account_already_balanced = []
        for key, value in tax_group_subtotal.items():
            total = value
            # Search if any advance payment done for that configuration
            if key[0] and key[0] not in account_already_balanced:
                total += _add_line(key[0], _('Balance tax advance payment account'), currency)
                account_already_balanced.append(key[0])
            if key[1] and key[1] not in account_already_balanced:
                total += _add_line(key[1], _('Balance tax current account (receivable)'), currency)
                account_already_balanced.append(key[1])
            if key[2] and key[2] not in account_already_balanced:
                total += _add_line(key[2], _('Balance tax current account (payable)'), currency)
                account_already_balanced.append(key[2])
            # Balance on the receivable/payable tax account
            if not currency.is_zero(total):
                line_ids_vals.append(Command.create({
                    'name': _('Payable tax amount') if total < 0 else _('Receivable tax amount'),
                    'debit': total if total > 0 else 0,
                    'credit': abs(total) if total < 0 else 0,
                    'account_id': key[2] if total < 0 else key[1]
                }))
        return line_ids_vals

    @api.model
    def _redirect_to_misconfigured_tax_groups(self, company, countries):
        """ Raises a RedirectWarning informing the user his tax groups are missing configuration
        for a given company, redirecting him to the tree view of account.tax.group, filtered
        accordingly to the provided countries.
        """
        need_config_action = {
            'type': 'ir.actions.act_window',
            'name': 'Tax groups',
            'res_model': 'account.tax.group',
            'view_mode': 'tree',
            'views': [[False, 'list']],
            'context': len(countries) == 1 and {'search_default_country_id': countries.ids or {}},
            # More than 1 id into search_default isn't supported
        }

        raise RedirectWarning(
            _('Please specify the accounts necessary for the Tax Closing Entry.'),
            need_config_action,
            _('Configure your TAX accounts - %s', company.display_name),
            additional_context={'allowed_company_ids': company.ids, 'force_account_company': company.id}
        )

    def _get_fpos_info_for_tax_closing(self, company, report, options):
        """ Returns the fiscal positions information to use to generate the tax closing
        for this company, with the provided options.

        :return: (include_domestic, fiscal_positions), where fiscal positions is a recordset
                 and include_domestic is a boolean telling whehter or not the domestic closing
                 (i.e. the one without any fiscal position) must also be performed
        """
        if options['fiscal_position'] == 'domestic':
            fiscal_positions = self.env['account.fiscal.position']
        elif options['fiscal_position'] == 'all':
            fiscal_positions = self.env['account.fiscal.position'].search([('company_id', '=', company.id), ('foreign_vat', '!=', False)])
        else:
            fpos_ids = [options['fiscal_position']]
            fiscal_positions = self.env['account.fiscal.position'].browse(fpos_ids)

        if options['fiscal_position'] == 'all':
            fiscal_country = company.account_fiscal_country_id
            include_domestic = not fiscal_positions \
                               or not report.country_id \
                               or fiscal_country == fiscal_positions[0].country_id
        else:
            include_domestic = options['fiscal_position'] == 'domestic'

        return include_domestic, fiscal_positions


class GenericTaxReportCustomHandlerAT(models.AbstractModel):
    _name = 'account.generic.tax.report.handler.account.tax'
    _inherit = 'account.generic.tax.report.handler'
    _description = 'Generic Tax Report Custom Handler (Account -> Tax)'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        return super()._get_dynamic_lines(report, options, 'account_tax')


class GenericTaxReportCustomHandlerTA(models.AbstractModel):
    _name = 'account.generic.tax.report.handler.tax.account'
    _inherit = 'account.generic.tax.report.handler'
    _description = 'Generic Tax Report Custom Handler (Tax -> Account)'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals):
        return super()._get_dynamic_lines(report, options, 'tax_account')
