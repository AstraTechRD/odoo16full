from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountChangeLockDate(models.TransientModel):
    """
    This wizard is used to change the lock date
    """
    _name = 'account.change.lock.date'
    _description = 'Change Lock Date'

    period_lock_date = fields.Date(
        string='Journal Entries Lock Date',
        default=lambda self: self.env.company.period_lock_date,
        help='Prevents Journal entries creation prior to the defined date. Except for Accountants users.')
    fiscalyear_lock_date = fields.Date(
        string='All Users Lock Date',
        default=lambda self: self.env.company.fiscalyear_lock_date,
        help='Prevents Journal Entry creation or modification prior to the defined date for all users. '
             'As a closed period, all accounting operations are prohibited.')
    tax_lock_date = fields.Date(
        string="Tax Return Lock Date",
        default=lambda self: self.env.company.tax_lock_date,
        help='Prevents Tax Returns modification prior to the defined date (Journal Entries involving taxes). '
             'The Tax Return Lock Date is automatically set when the corresponding Journal Entry is posted.')

    def _prepare_lock_date_values(self):
        return {
            'period_lock_date': self.period_lock_date,
            'fiscalyear_lock_date': self.fiscalyear_lock_date,
            'tax_lock_date': self.tax_lock_date,
        }

    def change_lock_date(self):
        if self.user_has_groups('account.group_account_manager'):
            if any(
                    lock_date > fields.Date.context_today(self)
                    for lock_date in (
                            self.fiscalyear_lock_date,
                            self.tax_lock_date,
                    )
                    if lock_date
            ):
                raise UserError(_('You cannot set a lock date in the future.'))
            self.env.company.sudo().write(self._prepare_lock_date_values())
        else:
            raise UserError(_('Only Billing Administrators are allowed to change lock dates!'))
        return {'type': 'ir.actions.act_window_close'}
