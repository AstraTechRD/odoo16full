# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date
from odoo.tools import date_utils

from dateutil.relativedelta import relativedelta


class AccountMove(models.Model):
    _inherit = "account.move"

    # used for VAT closing, containing the end date of the period this entry closes
    tax_closing_end_date = fields.Date()
    # technical field used to know if there was a failed control check
    tax_report_control_error = fields.Boolean()

    def _post(self, soft=True):
        # Overridden to create carryover external values and join the pdf of the report when posting the tax closing
        processed_moves = self.env['account.move']
        for move in self.filtered(lambda m: not m.posted_before and m.tax_closing_end_date):
            # Generate carryover values
            report, options = move._get_report_options_from_tax_closing_entry()

            company_ids = [comp_opt['id'] for comp_opt in options.get('multi_company', [])] or self.env.company.ids
            if len(company_ids) >= 2:
                # For tax units, we only do the carryover for all the companies when the last of their closing moves for the period is posted.
                # If a company has no closing move for this tax_closing_date, we consider the closing hasn't been done for it.
                closing_domains = [
                    ('company_id', 'in', company_ids),
                    ('tax_closing_end_date', '=', move.tax_closing_end_date),
                    '|', ('state', '=', 'posted'), ('id', 'in', processed_moves.ids),
                ]

                if move.fiscal_position_id:
                    closing_domains.append(('fiscal_position_id.foreign_vat', '=', move.fiscal_position_id.foreign_vat))

                posted_closings_from_unit_count = self.env['account.move'].sudo().search_count(closing_domains)

                if posted_closings_from_unit_count == len(company_ids) - 1: # -1 to exclude the company of the current move
                    report.with_context(allowed_company_ids=company_ids)._generate_carryover_external_values(options)
            else:
                report._generate_carryover_external_values(options)

            processed_moves += move

            # Post the pdf of the tax report in the chatter, and set the lock date if possible
            self._close_tax_period()

        return super()._post(soft)

    def action_open_tax_report(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account_reports.action_account_report_gt")
        options = self._get_report_options_from_tax_closing_entry()[1]
        # Pass options in context and set ignore_session: read to prevent reading previous options
        action.update({'params': {'options': options, 'ignore_session': 'read'}})
        return action

    def _close_tax_period(self):
        """ Closes tax closing entries. The tax closing activities on them will be marked done, and the next tax closing entry
        will be generated or updated (if already existing). Also, a pdf of the tax report at the time of closing
        will be posted in the chatter of each move.

        The tax lock date of each  move's company will be set to the move's date in case no other draft tax closing
        move exists for that company (whatever their foreign VAT fiscal position) before or at that date, meaning that
        all the tax closings have been performed so far.
        """
        if not self.user_has_groups('account.group_account_manager'):
            raise UserError(_('Only Billing Administrators are allowed to change lock dates!'))

        tax_closing_activity_type = self.env.ref('account_reports.tax_closing_activity_type')

        for move in self:
            # Change lock date to end date of the period, if all other tax closing moves before this one have been treated
            open_previous_closing = self.env['account.move'].search([
                ('activity_ids.activity_type_id', '=', tax_closing_activity_type.id),
                ('company_id', '=', move.company_id.id),
                ('date', '<=', move.date),
                ('state', '=', 'draft'),
                ('id', '!=', move.id),
            ], limit=1)

            if not open_previous_closing:
                move.company_id.sudo().tax_lock_date = move.tax_closing_end_date

            # Add pdf report as attachment to move
            report, options = move._get_report_options_from_tax_closing_entry()

            attachments = move._get_vat_report_attachments(report, options)

            # End activity
            activity = move.activity_ids.filtered(lambda m: m.activity_type_id.id == tax_closing_activity_type.id)
            if activity:
                activity.action_done()

            # Post the message with the PDF
            subject = _(
                "Vat closing from %s to %s",
                format_date(self.env, options['date']['date_from']),
                format_date(self.env, options['date']['date_to']),
            )
            move.with_context(no_new_invoice=True).message_post(body=move.ref, subject=subject, attachments=attachments)

            # Create the recurring entry (new draft move and new activity)
            if move.fiscal_position_id.foreign_vat:
                next_closing_params = {'fiscal_positions': move.fiscal_position_id}
            else:
                next_closing_params = {'include_domestic': True}
            move.company_id._get_and_update_tax_closing_moves(move.tax_closing_end_date + relativedelta(days=1), **next_closing_params)

    def refresh_tax_entry(self):
        for move in self.filtered(lambda m: m.tax_closing_end_date and m.state == 'draft'):
            report, options = move._get_report_options_from_tax_closing_entry()
            self.env[report.custom_handler_model_name]._generate_tax_closing_entries(report, options, closing_moves=move)

    def _get_report_options_from_tax_closing_entry(self):
        self.ensure_one()
        date_to = self.tax_closing_end_date
        # Take the periodicity of tax report from the company and compute the starting period date.
        delay = self.company_id._get_tax_periodicity_months_delay() - 1
        date_from = date_utils.start_of(date_to + relativedelta(months=-delay), 'month')

        # In case the company submits its report in different regions, a closing entry
        # is made for each fiscal position defining a foreign VAT.
        # We hence need to make sure to select a tax report in the right country when opening
        # the report (in case there are many, we pick the first one available; it doesn't impact the closing)
        if self.fiscal_position_id.foreign_vat:
            fpos_option = self.fiscal_position_id.id
            report_country = self.fiscal_position_id.country_id
        else:
            fpos_option = 'domestic'
            report_country = self.company_id.account_fiscal_country_id

        generic_tax_report = self.env.ref('account.generic_tax_report')
        tax_report = self.env['account.report'].search([
            ('availability_condition', '=', 'country'),
            ('country_id', '=', report_country.id),
            ('root_report_id', '=', generic_tax_report.id),
        ], limit=1)

        if not tax_report:
            tax_report = generic_tax_report

        options = {
            'date': {
                'date_from': fields.Date.to_string(date_from),
                'date_to': fields.Date.to_string(date_to),
                'filter': 'custom',
                'mode': 'range',
            },
            'fiscal_position': fpos_option,
            'tax_unit': 'company_only',
        }

        if tax_report.country_id and tax_report.filter_multi_company == 'tax_units':
            # Enforce multicompany if the closing is done for a tax unit
            candidate_tax_unit = self.company_id.account_tax_unit_ids.filtered(lambda x: x.country_id == report_country)
            if candidate_tax_unit:
                options['tax_unit'] = candidate_tax_unit.id
                company_ids = [company.id for company in candidate_tax_unit.sudo().company_ids]
            else:
                company_ids = self.env.company.ids
        else:
            company_ids = self.env.company.ids

        report_options = tax_report.with_context(allowed_company_ids=company_ids)._get_options(previous_options=options)
        if 'tax_report_control_error' in report_options:
            # This key will be set to False in the options by a custom init_options for reports adding control lines to themselves.
            # Its presence indicate that we need to compute the report in order to run the actual checks. The options dictionary will then be
            # modified in place (by a dynamic lines function) to contain the right check value under that key (see l10n_be_reports for an example).
            tax_report._get_lines(report_options)

        return tax_report, report_options

    def _get_vat_report_attachments(self, report, options):
        # Fetch pdf
        pdf_data = report.export_to_pdf(options)
        return [(pdf_data['file_name'], pdf_data['file_content'])]
