import logging

import requests
from datetime import datetime
from werkzeug.urls import url_join

from odoo import api, models, fields, _
from odoo.exceptions import UserError, AccessError
from odoo.tools.misc import format_date, format_datetime

_logger = logging.getLogger(__name__)

class res_company(models.Model):
    _inherit = 'res.company'
    l10n_au_kp_enable = fields.Boolean(string='Enable KeyPay Integration')
    l10n_au_kp_identifier = fields.Char(string='Business Id')
    l10n_au_kp_lock_date = fields.Date(string='Fetch Payrun After', help="Import payruns paied after this date. This date cannot be prior to Lock Date)")
    l10n_au_kp_journal_id = fields.Many2one('account.journal', string='Payroll Journal')

    @api.onchange('fiscalyear_lock_date', 'l10n_au_kp_lock_date')
    def _onchange_exclude_before(self):
        self.l10n_au_kp_lock_date = max(self.l10n_au_kp_lock_date, self.fiscalyear_lock_date)

    def _kp_get_key_and_url(self):
        key = self.env['ir.config_parameter'].get_param('l10n_au_keypay.l10n_au_kp_api_key')
        l10n_au_kp_base_url = self.env['ir.config_parameter'].get_param('l10n_au_keypay.l10n_au_kp_base_url')
        return (key, l10n_au_kp_base_url)

    def _kp_payroll_fetch_journal_entries(self, kp_payrun):
        self.ensure_one()
        key, l10n_au_kp_base_url = self._kp_get_key_and_url()
        # Fetch the journal details: https://api.keypay.com.au/australia/reference/pay-run/journal--get
        url = url_join(l10n_au_kp_base_url, 'api/v2/business/%s/journal/%s' % (self.l10n_au_kp_identifier, kp_payrun['id']))
        response = requests.get(url, auth=(key, ''), timeout=10)
        response.raise_for_status()

        line_ids_commands = []
        for kp_journal_item in response.json():
            item_account = self.env['account.account'].search([
                ('company_id', '=', self.id),
                ('deprecated', '=', False),
                '|', ('l10n_au_kp_account_identifier', '=', kp_journal_item['accountCode']), ('code', '=', kp_journal_item['accountCode'])
            ], limit=1, order='l10n_au_kp_account_identifier')
            if not item_account:
                raise UserError(_("Account not found: %s, either create an account with that code or link an existing one to that keypay code") % (kp_journal_item['accountCode'],))
            line_ids_commands.append((0, 0, {
                'account_id': item_account.id,
                'name': kp_journal_item['reference'],
                'debit': abs(kp_journal_item['amount']) if kp_journal_item['isDebit'] else 0,
                'credit': abs(kp_journal_item['amount']) if kp_journal_item['isCredit'] else 0,
            }))

        period_ending_date = datetime.strptime(kp_payrun["payPeriodEnding"], "%Y-%m-%dT%H:%M:%S")

        return {
            'journal_id': self.l10n_au_kp_journal_id.id,
            'ref': _("Pay period ending %s (#%s)") % (format_date(self.env, period_ending_date), kp_payrun['id']),
            'date': datetime.strptime(kp_payrun["datePaid"], "%Y-%m-%dT%H:%M:%S"),
            'line_ids': line_ids_commands,
            'l10n_au_kp_payrun_identifier': kp_payrun['id'],
        }

    def _kp_payroll_fetch_payrun(self):
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_manager'):
            raise AccessError(_("You don't have the access rights to fetch keypay payrun."))
        key, l10n_au_kp_base_url = self._kp_get_key_and_url()
        if not key or not self.l10n_au_kp_identifier or not self.l10n_au_kp_journal_id:
            raise UserError(_("Company %s does not have the apikey, business_id or the journal_id set") % (self.name))

        from_formated_datetime = self.l10n_au_kp_lock_date and datetime.combine(self.l10n_au_kp_lock_date, datetime.min.time()).replace(hour=23, minute=59, second=59)
        from_formated_datetime = format_datetime(self.env, from_formated_datetime, dt_format="yyyy-MM-dd'T'HH:mm:ss")
        filter = "$filter=DatePaid gt datetime'%s'&" % (from_formated_datetime) if from_formated_datetime else ''
        skip = 0
        top = 100
        kp_payruns = []
        while True:
            # Fetch the pay runs: https://api.keypay.com.au/australia/reference/pay-run/au-pay-run--get-pay-runs
            # Use Odata filtering (can only fetch 100 entries at a time): https://api.keypay.com.au/guides/ODataFiltering
            # There is a limit of 5 requests per second but the api do not discard the requests it just waits every 5 answers: https://api.keypay.com.au/guides/Usage
            url = url_join(l10n_au_kp_base_url, "api/v2/business/%s/payrun?%s$skip=%d&$top=%d" % (self.l10n_au_kp_identifier, filter, skip, top))
            response = requests.get(url, auth=(key, ''), timeout=10)
            response.raise_for_status()
            entries = response.json()
            kp_payruns += entries
            if len(entries) < 100:
                break
            skip += 100
            top += 100

        # We cannot filter using the API as we might run into a 414 Client Error: Request-URI Too Large
        payrun_ids = [kp_payrun['id'] for kp_payrun in kp_payruns]
        processed_payrun_ids = self.env['account.move'].search([('company_id', '=', self.id), ('l10n_au_kp_payrun_identifier', 'in', payrun_ids)])
        processed_payruns = processed_payrun_ids.mapped('l10n_au_kp_payrun_identifier')

        account_move_list_vals = []
        for kp_payrun in kp_payruns:
            # Entry needs to be finalized to have a journal entry
            # Currently no way to filter on boolean via the API...
            if not kp_payrun['isFinalised'] or kp_payrun['id'] in processed_payruns:
                continue

            account_move_vals = self._kp_payroll_fetch_journal_entries(kp_payrun)
            account_move_list_vals.append(account_move_vals)
        return self.env['account.move'].create(account_move_list_vals)

    def _kp_payroll_cron_fetch_payrun(self):
        for company in self.search([('l10n_au_kp_enable', '=', True)]):
            company._kp_payroll_fetch_payrun()
