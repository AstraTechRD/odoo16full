# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.iap.tools import iap_tools
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError

import logging
import time


_logger = logging.getLogger(__name__)

CLIENT_OCR_VERSION = 130

# list of result id that can be sent by iap-extract
SUCCESS = 0
NOT_READY = 1
ERROR_INTERNAL = 2
ERROR_NOT_ENOUGH_CREDIT = 3
ERROR_DOCUMENT_NOT_FOUND = 4
ERROR_NO_DOCUMENT_NAME = 5
ERROR_UNSUPPORTED_IMAGE_FORMAT = 6
ERROR_FILE_NAMES_NOT_MATCHING = 7
ERROR_NO_CONNECTION = 8
ERROR_SERVER_IN_MAINTENANCE = 9

ERROR_MESSAGES = {
    ERROR_INTERNAL: _("An error occurred"),
    ERROR_DOCUMENT_NOT_FOUND: _("The document could not be found"),
    ERROR_NO_DOCUMENT_NAME: _("No document name provided"),
    ERROR_UNSUPPORTED_IMAGE_FORMAT: _("Unsupported image format"),
    ERROR_FILE_NAMES_NOT_MATCHING: _("You must send the same quantity of documents and file names"),
    ERROR_NO_CONNECTION: _("Server not available. Please retry later"),
    ERROR_SERVER_IN_MAINTENANCE: _("Server is currently under maintenance. Please retry later"),
}


class HrExpenseExtractionWords(models.Model):
    _name = "hr.expense.extract.words"
    _description = "Extracted words from expense scan"

    expense_id = fields.Many2one("hr.expense", string="Expense")
    word_text = fields.Char()
    word_page = fields.Integer()


class HrExpense(models.Model):
    _inherit = ['hr.expense']
    _order = "state_processed desc, date desc, id desc"

    @api.depends('extract_status_code')
    def _compute_error_message(self):
        for record in self:
            if record.extract_status_code != SUCCESS and record.extract_status_code != NOT_READY:
                record.extract_error_message = ERROR_MESSAGES.get(record.extract_status_code, ERROR_MESSAGES[ERROR_INTERNAL])
            else:
                record.extract_error_message = ''

    def _compute_can_show_send_resend(self, record):
        can_show = True
        if not self.env.company.expense_extract_show_ocr_option_selection or self.env.company.expense_extract_show_ocr_option_selection == 'no_send':
            can_show = False
        if record.state != 'draft':
            can_show = False
        if record.message_main_attachment_id is None or len(record.message_main_attachment_id) == 0:
            can_show = False
        return can_show

    @api.depends('state', 'extract_state', 'message_main_attachment_id')
    def _compute_show_resend_button(self):
        for record in self:
            record.extract_can_show_resend_button = self._compute_can_show_send_resend(record)
            if record.extract_state not in ['error_status', 'not_enough_credit']:
                record.extract_can_show_resend_button = False

    @api.depends('state', 'extract_state', 'message_main_attachment_id')
    def _compute_show_send_button(self):
        for record in self:
            record.extract_can_show_send_button = self._compute_can_show_send_resend(record)
            if record.extract_state not in ['no_extract_requested']:
                record.extract_can_show_send_button = False

    @api.depends('extract_state')
    def _compute_state_processed(self):
        for record in self:
            record.state_processed = record.extract_state in ['waiting_extraction', 'waiting_upload']

    extract_state = fields.Selection([('no_extract_requested', 'No extract requested'),
                                      ('not_enough_credit', 'Not enough credit'),
                                      ('error_status', 'An error occurred'),
                                      ('waiting_upload', 'Waiting upload'),
                                      ('waiting_extraction', 'Waiting extraction'),
                                      ('extract_not_ready', 'waiting extraction, but it is not ready'),
                                      ('waiting_validation', 'Waiting validation'),
                                      ('to_validate', 'To validate'),
                                      ('done', 'Completed flow')],
                                     'Extract state', default='no_extract_requested', required=True, copy=False)
    extract_status_code = fields.Integer("Status code", copy=False)
    extract_error_message = fields.Text("Error message", compute=_compute_error_message)
    extract_remote_id = fields.Integer("Id of the request to IAP-OCR", default="-1", copy=False, readonly=True)
    extract_word_ids = fields.One2many("hr.expense.extract.words", inverse_name="expense_id", copy=False)
    extract_can_show_resend_button = fields.Boolean("Can show the ocr resend button", compute=_compute_show_resend_button)
    extract_can_show_send_button = fields.Boolean("Can show the ocr send button", compute=_compute_show_send_button)
    # We want to see the records that are just processed by OCR at the top of the list
    state_processed = fields.Boolean(string='Status regarding OCR status', compute=_compute_state_processed, store=True)

    def attach_document(self, **kwargs):
        """when an attachment is uploaded, send the attachment to iap-extract if this is the first attachment"""
        if self.env.company.expense_extract_show_ocr_option_selection == 'auto_send':
            for record in self:
                if record.extract_state == "no_extract_requested":
                    record.action_manual_send_for_digitization()

    def _message_set_main_attachment_id(self, attachment_ids):
        super(HrExpense, self)._message_set_main_attachment_id(attachment_ids)
        self.attach_document()

    def get_validation(self, field):

        text_to_send = {}
        if field == "total":
            text_to_send["content"] = self.unit_amount
        elif field == "date":
            text_to_send["content"] = str(self.date) if self.date else False
        elif field == "description":
            text_to_send["content"] = self.name
        elif field == "currency":
            text_to_send["content"] = self.currency_id.name
        elif field == "bill_reference":
            text_to_send["content"] = self.reference
        return text_to_send

    @api.model
    def _cron_validate(self):
        """Send user corrected values to the ocr"""
        exp_to_validate = self.search([('extract_state', '=', 'to_validate')])
        documents = {
            record.extract_remote_id: {
                'total': record.get_validation('total'),
                'date': record.get_validation('date'),
                'description': record.get_validation('description'),
                'currency': record.get_validation('currency'),
                'bill_reference': record.get_validation('bill_reference')
            } for record in exp_to_validate
        }
        params = {
            'documents': documents,
            'version': CLIENT_OCR_VERSION,
        }
        endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'hr_expense_extract_endpoint', 'https://iap-extract.odoo.com') + '/api/extract/expense/1/validate_batch'
        try:
            iap_tools.iap_jsonrpc(endpoint, params=params)
            exp_to_validate.extract_state = 'done'
        except AccessError:
            pass

    def action_submit_expenses(self, **kwargs):
        res = super(HrExpense, self).action_submit_expenses(**kwargs)
        self.extract_state = 'to_validate'
        self.env.ref('hr_expense_extract.ir_cron_ocr_validate')._trigger()
        return res

    @api.model
    def check_all_status(self):
        for record in self.search([('state', '=', 'draft'), ('extract_state', 'in', ['waiting_extraction', 'extract_not_ready'])]):
            try:
                record._check_status()
            except:
                pass

    def check_status(self):
        """contact iap to get the actual status of the ocr requests"""
        records_to_update = self.filtered(lambda exp: exp.extract_state in ['waiting_extraction', 'extract_not_ready'])
        
        for record in records_to_update:
            record._check_status()

        limit = max(0, 20 - len(records_to_update))
        if limit > 0:
            records_to_preupdate = self.search([('extract_state', 'in', ['waiting_extraction', 'extract_not_ready']), ('id', 'not in', records_to_update.ids), ('state', '=', 'draft')], limit=limit)
            for record in records_to_preupdate:
                try:
                    record._check_status()
                except:
                    pass

    def _check_status(self):
        self.ensure_one()
        endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'hr_expense_extract_endpoint', 'https://iap-extract.odoo.com') + '/iap/expense_extract/get_result'
        params = {
                'version': CLIENT_OCR_VERSION,
                'document_id': self.extract_remote_id
            }
        result = iap_tools.iap_jsonrpc(endpoint, params=params)
        self.extract_status_code = result['status_code']
        if result['status_code'] == SUCCESS:
            self.extract_state = "waiting_validation"
            ocr_results = result['results'][0]
            self.extract_word_ids.unlink()

            description_ocr = ocr_results['description']['selected_value']['content'] if 'description' in ocr_results else ""
            total_ocr = ocr_results['total']['selected_value']['content'] if 'total' in ocr_results else ""
            date_ocr = ocr_results['date']['selected_value']['content'] if 'date' in ocr_results else ""
            currency_ocr = ocr_results['currency']['selected_value']['content'] if 'currency' in ocr_results else ""
            bill_reference_ocr = ocr_results['bill_reference']['selected_value']['content'] if 'bill_reference' in ocr_results else ""

            self.state = 'draft'
            if not self.name or self.name == self.message_main_attachment_id.name.split('.')[0]:
                self.name = description_ocr
                self.predicted_category = description_ocr
                predicted_product_id = self._predict_product(description_ocr, category=True)
                if predicted_product_id:
                    self.product_id = predicted_product_id if predicted_product_id else self.product_id
                    self.total_amount = total_ocr

            context_create_date = fields.Date.context_today(self, self.create_date)
            if not self.date or self.date == context_create_date:
                self.date = date_ocr

            if not self.total_amount:
                self.total_amount = total_ocr

            if not self.reference:
                self.reference = bill_reference_ocr

            if self.user_has_groups('base.group_multi_currency') and (not self.currency_id or self.currency_id == self.env.company.currency_id):
                currency = self.env["res.currency"].search([
                    '|', '|',
                    ('currency_unit_label', 'ilike', currency_ocr),
                    ('name', 'ilike', currency_ocr),
                    ('symbol', 'ilike', currency_ocr)],
                    limit=1
                )
                if currency:
                    self.currency_id = currency

        elif result['status_code'] == NOT_READY:
            self.extract_state = 'extract_not_ready'
        else:
            self.extract_state = 'error_status'

    def action_manual_send_for_digitization(self):
        for rec in self:
            rec.env['iap.account']._send_iap_bus_notification(
                service_name='invoice_ocr',
                title=_("Expense is being Digitized"))
        self.extract_state = 'waiting_upload'
        self.env.ref('hr_expense_extract.ir_cron_ocr_parse')._trigger()

    def action_send_for_digitization(self):
        if any(expense.state != 'draft' or expense.sheet_id for expense in self):
            raise UserError(_("You cannot send a expense that is not in draft state!"))

        self.action_manual_send_for_digitization()

        if len(self) == 1:
            return {
                'name': _('Generated Expense'),
                'view_mode': 'form',
                'res_model': 'hr.expense',
                'type': 'ir.actions.act_window',
                'views': [[False, 'form']],
                'res_id': self[0].id,
            }
        else:
            return {
                'name': _('Expenses sent'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,form',
                'res_model': 'hr.expense',
                'target': 'current',
                'domain': [('id', 'in', [expense.id for expense in self])],

            }

    @api.model
    def _cron_parse(self):
        for rec in self.search([('extract_state', '=', 'waiting_upload')]):
            rec.retry_ocr()

    def retry_ocr(self):
        """Retry to contact iap to submit the first attachment in the chatter"""
        if not self.env.company.expense_extract_show_ocr_option_selection or self.env.company.expense_extract_show_ocr_option_selection == 'no_send':
            return False
        attachments = self.message_main_attachment_id
        if (
                attachments.exists() and
                self.extract_state in ['no_extract_requested', 'waiting_upload', 'not_enough_credit', 'error_status']
        ):
            account_token = self.env['iap.account'].get('invoice_ocr')
            endpoint = self.env['ir.config_parameter'].sudo().get_param(
                    'hr_expense_extract_endpoint', 'https://iap-extract.odoo.com') + '/iap/expense_extract/parse'

            #this line contact iap to create account if this is the first request. This allow iap to give free credits if the database is elligible
            self.env['iap.account'].get_credits('invoice_ocr')

            user_infos = {
                'user_company_VAT': self.company_id.vat,
                'user_company_name': self.company_id.name,
                'user_company_country_code': self.company_id.country_id.code,
                'user_lang': self.env.user.lang,
                'user_email': self.env.user.email,
            }
            params = {
                'account_token': account_token.account_token,
                'version': CLIENT_OCR_VERSION,
                'dbuuid': self.env['ir.config_parameter'].sudo().get_param('database.uuid'),
                'documents': [x.datas.decode('utf-8') for x in attachments],
                'file_names': [x.name for x in attachments],
                'user_infos': user_infos,
                }
            try:
                result = iap_tools.iap_jsonrpc(endpoint, params=params)
                self.extract_status_code = result['status_code']
                if result['status_code'] == SUCCESS:
                    self.extract_state = 'waiting_extraction'
                    self.extract_remote_id = result['document_id']
                    if 'isMobile' in self.env.context and self.env.context['isMobile']:
                        for record in self:
                            timer = 0
                            while record.extract_state != 'waiting_validation' and timer < 10:
                                timer += 1
                                time.sleep(1)
                                record._check_status()
                elif result['status_code'] == ERROR_NOT_ENOUGH_CREDIT:
                    self.extract_state = 'not_enough_credit'
                else:
                    self.extract_state = 'error_status'
                    _logger.warning('There was an issue while doing the OCR operation on this file. Error: -1')

            except AccessError:
                self.extract_state = 'error_status'
                self.extract_status_code = ERROR_NO_CONNECTION

    def buy_credits(self):
        url = self.env['iap.account'].get_credits_url(base_url='', service_name='invoice_ocr')
        return {
            'type': 'ir.actions.act_url',
            'url': url,
        }

    @api.model
    def get_empty_list_help(self, help):
        expenses = self.search_count(
            [
                ('employee_id', 'in', self.env.user.employee_ids.ids),
                ('state', 'in', ['draft', 'reported', 'approved', 'done', 'refused'])
            ])
        if self.env.user.has_group('hr_expense.group_hr_expense_manager') and (not isinstance(help, str) or "o_view_nocontent_empty_folder" not in help):
            action_id = self.env.ref('hr_expense_extract.action_expense_sample_receipt').id
            html_to_return = """
<p class="o_view_nocontent_expense_receipt">
    <h2 class="d-none d-md-block">
        Drag and drop files to create expenses
    </h2>
    <p>
        Or
    </p>
    <h2 class="d-none d-md-block">
        Did you try the mobile app?
    </h2>
</p>
<p>Snap pictures of your receipts and let Odoo<br/> automatically create expenses for you.</p>
<p class="d-none d-md-block">
    <a href="https://apps.apple.com/be/app/odoo/id1272543640" target="_blank" class="o_expense_mobile_app">
        <img alt="Apple App Store" class="img img-fluid h-100 o_expense_apple_store" src="/hr_expense/static/img/app_store.png"/>
    </a>
    <a href="https://play.google.com/store/apps/details?id=com.odoo.mobile" target="_blank" class="o_expense_mobile_app">
        <img alt="Google Play Store" class="img img-fluid h-100 o_expense_google_store" src="/hr_expense/static/img/play_store.png"/>
    </a>
</p>"""
            if not expenses:
                html_to_return += """
%(mail_alias)s
<p>
    <a type="action" name="%(action_id)s" class="btn btn-primary text-white">Try Sample Receipt</a>
</p>""" % {'action_id': action_id, 'mail_alias': self._get_empty_list_mail_alias()}
            return html_to_return
        return super().get_empty_list_help(help)


class HrExpenseSheet(models.Model):
    _inherit = ['hr.expense.sheet']

    def action_register_payment(self):
        samples = self.mapped('expense_line_ids.sample')
        if samples.count(True):
            action = self.env['ir.actions.actions']._for_xml_id('hr_expense_extract.action_expense_sample_register')
            action['context'] = {'active_id': self.id}
            return action

        return super().action_register_payment()
