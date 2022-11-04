# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.osv import expression


class AccountMove(models.Model):
    _inherit = "account.move"

    # Technical field to keep the value of payment_state when switching from invoicing to accounting
    # (using invoicing_switch_threshold setting field). It allows keeping the former payment state, so that
    # we can restore it if the user misconfigured the switch date and wants to change it.
    payment_state_before_switch = fields.Char(string="Payment State Before Switch", copy=False)

    @api.model
    def _get_invoice_in_payment_state(self):
        # OVERRIDE to enable the 'in_payment' state on invoices.
        return 'in_payment'

    def action_post(self):
        # EXTENDS 'account' to trigger the CRON auto-reconciling the statement lines.
        res = super().action_post()
        if self.statement_line_id:
            self.env.ref('account_accountant.auto_reconcile_bank_statement_line')._trigger()
        return res

    def action_open_bank_reconciliation_widget(self):
        return self.statement_line_id._action_open_bank_reconciliation_widget(
            default_context={
                'search_default_journal_id': self.statement_line_id.journal_id.id,
                'search_default_statement_line_id': self.statement_line_id.id,
                'default_st_line_id': self.statement_line_id.id,
            }
        )

    def action_open_business_doc(self):
        if self.statement_line_id:
            return self.action_open_bank_reconciliation_widget()
        else:
            return super().action_open_business_doc()

    def _get_mail_thread_data_attachments(self):
        res = super()._get_mail_thread_data_attachments()
        res += self.statement_line_id.statement_id.attachment_ids
        return res


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = "account.move.line"

    move_attachment_ids = fields.One2many('ir.attachment', compute='_compute_attachment')

    @api.model
    def _read_group_prepare(self, orderby, aggregated_fields, annotated_groupbys, query):
        # EXTENDS base
        # Hack for the bank reconciliation widget to force the candidates amls having exactly the same amount as the
        # statement line to be on top of the list.
        groupby_terms, orderby_terms = super()._read_group_prepare(orderby, aggregated_fields, annotated_groupbys, query)

        if 'bank_rec_widget_st_line_amount' in self._context:
            st_currency_id = self._context['bank_rec_widget_st_line_currency_id']
            st_amount = self._context['bank_rec_widget_st_line_amount']
            st_amount_percent = st_amount * 0.05
            orderby_terms.append(f'''
                CASE WHEN "account_move_line"."currency_id" != {st_currency_id}
                THEN ABS({st_amount_percent})
                ELSE LEAST(ABS("account_move_line"."amount_residual_currency" - {st_amount}), ABS({st_amount_percent}))
                END
            ''')
            groupby_terms.extend(['"account_move_line"."currency_id"', '"account_move_line"."amount_residual_currency"'])
        return groupby_terms, orderby_terms

    def _compute_attachment(self):
        for record in self:
            record.move_attachment_ids = self.env['ir.attachment'].search(expression.OR(record._get_attachment_domains()))

    def action_reconcile(self):
        """ This function is called by the 'Reconcile' action of account.move.line's
        tree view. It performs reconciliation between the selected lines, or, if they
        only consist of payable and receivable lines for the same partner, it opens
        the transfer wizard, pre-filled with the necessary data to transfer
        the payable/receivable open balance into the receivable/payable's one.
        This way, we can simulate reconciliation between receivable and payable
        accounts, using an intermediate account.move doing the transfer.
        """
        all_accounts = self.mapped('account_id')
        account_types = all_accounts.mapped('account_type')
        all_partners = self.mapped('partner_id')

        if len(all_accounts) == 2 and 'liability_payable' in account_types and 'asset_receivable' in account_types:

            if len(all_partners) != 1:
                raise UserError(_("You cannot reconcile the payable and receivable accounts of multiple partners together at the same time."))

            # In case we have only lines for one (or no) partner and they all
            # are located on a single receivable or payable account,
            # we can simulate reconciliation between them with a transfer entry.
            # So, we open the wizard allowing to do that, pre-filling the values.

            max_total = 0
            max_account = None
            for account in all_accounts:
                account_total = abs(sum(line.balance for line in self.filtered(lambda x: x.account_id == account)))
                if not max_account or max_total < account_total:
                    max_account = account
                    max_total = account_total

            wizard = self.env['account.automatic.entry.wizard'].create({
                'move_line_ids': [(6, 0, self.ids)],
                'destination_account_id': max_account.id,
                'action': 'change_account',
            })

            return {
                'name': _("Transfer Accounts"),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.automatic.entry.wizard',
                'res_id': wizard.id,
                'target': 'new',
                'context': {'active_ids': self.ids, 'active_model': 'account.move.line'},
            }

        return {
            'type': 'ir.actions.client',
            'name': _('Reconcile'),
            'tag': 'manual_reconciliation_view',
            'binding_model_id': self.env['ir.model.data']._xmlid_to_res_id('account.model_account_move_line'),
            'binding_type': 'action',
            'binding_view_types': 'list',
            'context': {'active_ids': self.ids, 'active_model': 'account.move.line'},
        }
