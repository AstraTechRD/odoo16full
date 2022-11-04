from odoo import models


class SaleSubscription(models.Model):
    _inherit = "sale.order"

    def _create_recurring_invoice(self, automatic=False, batch_size=30):
        invoices = super()._create_recurring_invoice(automatic, batch_size)
        # Already compute taxes for unvalidated documents as they can already be paid
        invoices.filtered(lambda m: m.state == 'draft').button_update_avatax()
        return invoices

    def _do_payment(self, payment_token, invoice):
        invoice.button_update_avatax()
        return super()._do_payment(payment_token, invoice)
