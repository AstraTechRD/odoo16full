# -*- coding: utf-8 -*-
from odoo import _, api, fields, models

from dateutil.relativedelta import relativedelta


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    def action_open_bank_reconcile_widget(self):
        self.ensure_one()
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            name=self.name,
            default_context={
                'default_statement_id': self.id,
                'default_journal_id': self.journal_id.id,
            },
            extra_domain=[('statement_id', '=', self.id)]
        )


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    # Technical field holding the date of the last time the cron tried to auto-reconcile the statement line. Used to
    # optimize the bank matching process"
    cron_last_check = fields.Datetime()

    def action_save_close(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_save_new(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account_accountant.action_bank_statement_line_form_bank_rec_widget')
        action['context'] = {'default_journal_id': self._context['default_journal_id']}
        return action

    @api.model
    def _action_open_bank_reconciliation_widget(self, extra_domain=None, default_context=None, name=None):
        context = default_context or {}
        return {
            'name': name or _("Bank Reconciliation"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'context': context,
            'search_view_id': [self.env.ref('account_accountant.view_bank_statement_line_search_bank_rec_widget').id, 'search'],
            'view_mode': 'kanban,list',
            'views': [
                (self.env.ref('account_accountant.view_bank_statement_line_kanban_bank_rec_widget').id, 'kanban'),
                (self.env.ref('account_accountant.view_bank_statement_line_tree_bank_rec_widget').id, 'list'),
            ],
            'domain': [('state', '!=', 'cancel')] + (extra_domain or []),
        }

    def action_open_recon_st_line(self):
        self.ensure_one()
        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            name=self.name,
            default_context={
                'default_statement_id': self.statement_id.id,
                'default_journal_id': self.journal_id.id,
                'default_st_line_id': self.id,
                'search_default_id': self.id,
            },
        )

    @api.model
    def _cron_try_auto_reconcile_statement_lines(self, batch_size=None):
        """ Method called by the CRON to reconcile the statement lines automatically.

        :param batch_size:  The maximum number of statement lines that could be processed at once by the CRON to avoid
                            a timeout. If specified, the CRON will be trigger again asap using a CRON trigger in case
                            there is still some statement lines to process.
        """
        self.env['account.reconcile.model'].flush_model()

        # Check the companies having at least one reconcile model using the 'auto_reconcile' feature.
        query_obj = self.env['account.reconcile.model']._search([
            ('auto_reconcile', '=', True),
            ('rule_type', 'in', ('writeoff_suggestion', 'invoice_matching')),
        ])
        query_obj.order = 'company_id'
        query_str, query_params = query_obj.select('DISTINCT company_id')
        self._cr.execute(query_str, query_params)
        configured_company_ids = [r[0] for r in self._cr.fetchall()]
        if not configured_company_ids:
            return

        # Find the bank statement lines that are not reconciled and try to reconcile them automatically.
        # The ones that are never be processed by the CRON before are processed first.
        limit = batch_size + 1 if batch_size else None
        has_more_st_lines_to_reconcile = False
        datetime_now = fields.Datetime.now()
        companies = self.env['res.company'].browse(configured_company_ids)
        lock_dates = companies.filtered('fiscalyear_lock_date').mapped('fiscalyear_lock_date')
        st_date_from_limit = max([datetime_now.date() - relativedelta(months=3)] + lock_dates)

        self.env['account.bank.statement.line'].flush_model()
        domain = [
            ('is_reconciled', '=', False),
            ('date', '>', st_date_from_limit),
            ('company_id', 'in', configured_company_ids),
        ]
        query_obj = self._search(domain, order='cron_last_check DESC, id', limit=limit)
        query_str, query_params = query_obj.select('account_bank_statement_line.id')
        self._cr.execute(query_str, query_params)
        st_line_ids = [r[0] for r in self._cr.fetchall()]
        if batch_size and len(st_line_ids) > batch_size:
            st_line_ids = st_line_ids[:batch_size]
            has_more_st_lines_to_reconcile = True

        st_lines = self.env['account.bank.statement.line'].browse(st_line_ids)
        nb_auto_reconciled_lines = 0
        for st_line in st_lines:
            wizard = self.env['bank.rec.widget'].with_context(default_st_line_id=st_line.id).new({})
            wizard._action_trigger_matching_rules()
            if wizard.state == 'valid' and wizard.matching_rules_allow_auto_reconcile:
                wizard.button_validate(async_action=False)

                st_line.move_id.message_post(body=_(
                    "This bank transaction has been automatically validated using the reconciliation model '%s'.",
                    ', '.join(st_line.move_id.line_ids.reconcile_model_id.mapped('name')),
                ))

                nb_auto_reconciled_lines += 1
        st_lines.write({'cron_last_check': datetime_now})

        # The configuration seems effective since some lines has been automatically reconciled right now and there is
        # some statement lines left.
        if nb_auto_reconciled_lines and has_more_st_lines_to_reconcile:
            self.env.ref('account_accountant.auto_reconcile_bank_statement_line')._trigger()
