# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_open_manual_reconciliation_widget(self):
        ''' Open the manual reconciliation widget for the current payment.
        :return: A dictionary representing an action.
        '''
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("Payments without a customer can't be matched"))

        liquidity_lines, counterpart_lines, writeoff_lines = self._seek_for_lines()

        action_context = {'company_ids': self.company_id.ids, 'partner_ids': self.partner_id.ids}
        if self.partner_type == 'customer':
            action_context.update({'mode': 'customers'})
        elif self.partner_type == 'supplier':
            action_context.update({'mode': 'suppliers'})

        if counterpart_lines:
            action_context.update({'move_line_id': counterpart_lines[0].id})

        return {
            'type': 'ir.actions.client',
            'tag': 'manual_reconciliation_view',
            'context': action_context,
        }

    def button_open_statement_lines(self):
        # OVERRIDE
        """ Redirect the user to the statement line(s) reconciled to this payment.
            :return: An action to open the view of the payment in the reconciliation widget.
        """
        self.ensure_one()

        return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
            extra_domain=[('id', 'in', self.reconciled_statement_line_ids.ids)],
            default_context={'create': False},
            name=_("Matched Transactions")
        )
