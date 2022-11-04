# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import models, fields, _
from odoo.exceptions import UserError, RedirectWarning


class TrialBalanceCustomHandler(models.AbstractModel):
    _inherit = 'account.trial.balance.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'MX':
            options['buttons'] += [
                {'name': _("SAT (XML)"), 'action': 'export_file', 'action_param': 'action_l10n_mx_generate_sat_xml', 'file_export_type': _("SAT (XML)"), 'sequence': 15},
                {'name': _("COA SAT (XML)"), 'action': 'export_file', 'action_param': 'action_l10n_mx_generate_coa_sat_xml', 'file_export_type': _("COA SAT (XML)"), 'sequence': 16},
            ]

    def action_l10n_mx_generate_sat_xml(self, options):
        if self.env.company.account_fiscal_country_id.code != 'MX':
            raise UserError(_("Only Mexican company can generate SAT report."))

        sat_values = self._l10n_mx_get_sat_values(options)
        file_name = f"{sat_values['vat']}{sat_values['year']}{sat_values['month']}"
        sat_report = etree.fromstring(self.env['ir.qweb']._render('l10n_mx_reports.cfdibalance', sat_values))

        self.env['ir.attachment'].l10n_mx_reports_validate_xml_from_attachment(sat_report, 'xsd_mx_cfdibalance_1_3.xsd')

        return {
            'file_name': f"{file_name}CT.xml",
            'file_content': etree.tostring(sat_report, pretty_print=True, xml_declaration=True, encoding='utf-8'),
            'file_type': 'xml',
        }

    def _l10n_mx_get_sat_values(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        sat_options = self._l10n_mx_get_sat_options(options)
        report_lines = report._get_lines(sat_options)

        account_lines = []
        for line in [line for line in report_lines if line.get('level') in (2, 3)]:
            res_model, dummy = report._get_model_info_from_id(line['id'])
            if res_model != 'account.group':
                continue
            cols = line.get('columns', [])
            # Initial Debit - Initial Credit = Initial Balance
            initial = cols[0].get('no_format', 0.0) - cols[1].get('no_format', 0.0)
            # Debit and Credit of the selected period
            debit = cols[2].get('no_format', 0.0)
            credit = cols[3].get('no_format', 0.0)
            # End Debit - End Credit = End Balance
            end = cols[4].get('no_format', 0.0) - cols[5].get('no_format', 0.0)
            account_lines.append({
                'number': line.get('name').split(' ', 1)[0],
                'initial': '%.2f' % initial,
                'debit': '%.2f' % debit,
                'credit': '%.2f' % credit,
                'end': '%.2f' % end,
            })

        report_date = fields.Date.to_date(sat_options['date']['date_from'])
        return {
            'vat': self.env.company.vat or '',
            'month': str(report_date.month).zfill(2),
            'year': report_date.year,
            'type': 'N',
            'accounts': account_lines,
        }

    def action_l10n_mx_generate_coa_sat_xml(self, options):
        if self.env.company.account_fiscal_country_id.code != 'MX':
            raise UserError(_("Only Mexican company can generate SAT report."))

        coa_values = self._l10n_mx_get_coa_values(options)
        file_name = f"{coa_values['vat']}{coa_values['year']}{coa_values['month']}CT"
        coa_report = etree.fromstring(self.env['ir.qweb']._render('l10n_mx_reports.cfdicoa', coa_values))

        self.env['ir.attachment'].l10n_mx_reports_validate_xml_from_attachment(coa_report, 'xsd_mx_cfdicoa_1_3.xsd')

        return {
            'file_name': f"{file_name}.xml",
            'file_content': etree.tostring(coa_report, pretty_print=True, xml_declaration=True, encoding='utf-8'),
            'file_type': 'xml',
        }

    def _l10n_mx_get_coa_values(self, options):
        def define_group_nature(report, lines, selected_level):
            for line in [line for line in lines if line['level'] == selected_level]:
                children_group_lines_nature = set([
                    children['nature']
                    for children in report._get_unfolded_lines(lines, line['id'])
                    if children['level'] == line['level'] + 1 and children.get('nature')
                ])
                if len(children_group_lines_nature) == 1:
                    line['nature'] = children_group_lines_nature.pop()
                elif len(children_group_lines_nature) > 1:
                    line['nature'] = 'DA'
                else:
                    line['nature'] = None
            return lines

        report = self.env['account.report'].browse(options['report_id'])
        # Checking if debit/credit tags are installed
        debit_balance_account_tag = self.env.ref('l10n_mx.tag_debit_balance_account', raise_if_not_found=False)
        credit_balance_account_tag = self.env.ref('l10n_mx.tag_credit_balance_account', raise_if_not_found=False)
        if not debit_balance_account_tag or not credit_balance_account_tag:
            raise UserError(_("Missing Debit or Credit balance account tag in database."))

        coa_options = self._l10n_mx_get_sat_options(options)
        report_lines = report._get_lines(coa_options)
        for line in report_lines:
            res_model, res_id = report._get_model_info_from_id(line['id'])
            if res_model == 'account.account':
                account = self.env['account.account'].browse(res_id)
                if account.account_type == 'equity_unaffected':
                    continue
                line['nature'] = ''
                if debit_balance_account_tag in account.tag_ids:
                    line['nature'] += 'D'
                if credit_balance_account_tag in account.tag_ids:
                    line['nature'] += 'A'

        report_lines = define_group_nature(report, report_lines, selected_level=3)
        report_lines = define_group_nature(report, report_lines, selected_level=2)

        self._l10n_mx_verify_coa_nature(report, report_lines)

        account_lines = []
        for line in [line for line in report_lines if line.get('level') in (2, 3) and line.get('nature')]:
            line_code, line_name = line.get('name', '').split(' ', 1)
            account_lines.append({
                'code': line_code,
                'number': line_code,
                'name': line_name,
                'level': f"{line['level'] - 1}",
                'nature': line['nature'],
            })

        report_date = fields.Date.to_date(coa_options['date']['date_from'])
        return {
            'vat': self.env.company.vat or '',
            'month': str(report_date.month).zfill(2),
            'year': report_date.year,
            'accounts': account_lines,
        }

    def _l10n_mx_get_sat_options(self, options):
        sat_options = options.copy()
        del sat_options['comparison']
        return self.env['account.report'].browse(options['report_id'])._get_options(
            previous_options={
                **sat_options,
                'hierarchy': True,  # We need the hierarchy activated to get group lines
            }
        )

    def _l10n_mx_verify_coa_nature(self, report, report_lines):
        def get_problematic_accounts(lines, specific_line):
            unfolded_lines = report._get_unfolded_lines(lines, specific_line['id'])
            accounts = self.env['account.account']
            for unfolded_line in unfolded_lines:
                res_model, res_id = report._get_model_info_from_id(unfolded_line['id'])
                if res_model == 'account.account':
                    accounts |= self.env['account.account'].browse(res_id)
            return accounts

        accounts_without_tag = self.env['account.account']
        accounts_with_too_much_tag = self.env['account.account']
        for line in [report_line for report_line in report_lines if isinstance(report_line.get('nature'), str)]:
            # Checking that all accounts present in trial balance have one of these tags
            if line['nature'] == '':
                accounts_without_tag |= get_problematic_accounts(report_lines, line)
            elif line['nature'] == 'DA':
                accounts_with_too_much_tag |= get_problematic_accounts(report_lines, line)

        if accounts_without_tag:
            raise RedirectWarning(
                _("Some accounts present in your trial balance don't have a Debit or a Credit balance account tag."),
                {
                    'name': _("Accounts without tag"),
                    'type': 'ir.actions.act_window',
                    'views': [(False, 'list'), (False, 'form')],
                    'res_model': 'account.account',
                    'target': 'current',
                    'domain': [('id', 'in', accounts_without_tag.ids)],
                },
                _('Show list')
            )
        elif accounts_with_too_much_tag:
            raise RedirectWarning(
                _("Some account prefixes used in your trial balance use both Debit and Credit balance account tags. This is not allowed."),
                {
                    'name': _("Accounts with too much tags"),
                    'type': 'ir.actions.act_window',
                    'views': [(False, 'list'), (False, 'form')],
                    'res_model': 'account.account',
                    'target': 'current',
                    'domain': [('id', 'in', accounts_with_too_much_tag.ids)],
                },
                _('Show list')
            )
