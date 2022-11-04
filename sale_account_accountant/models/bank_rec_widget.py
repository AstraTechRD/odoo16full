from odoo import _, fields, models, Command
from odoo.addons.web.controllers.utils import clean_action


class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    matched_sale_order_ids = fields.Many2many(
        comodel_name='sale.order',
        store=False,
    )

    def _action_trigger_matching_rules(self):
        # EXTENDS account_accountant
        matching = super()._action_trigger_matching_rules()
        if matching and matching.get('sale_orders'):
            self.matched_sale_order_ids = [Command.set(matching['sale_orders'].ids)]
        return matching

    def button_show_sale_orders(self):
        self.ensure_one()
        self.next_action_todo = clean_action(
            self._prepare_button_show_reconciled_action(self.matched_sale_order_ids._origin, name=_("Sale Orders")),
            self.env,
        )
