# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _
from dateutil import parser


class PosSession(models.Model):
    _inherit = 'pos.session'

    def get_total_discount(self):
        amount = 0
        for line in self.env['pos.order.line'].search([('order_id', 'in', self.order_ids.ids), ('discount', '>', 0)]):
            normal_price = line.qty * line.price_unit
            normal_price = normal_price + (normal_price / 100 * line.tax_ids.amount)
            amount += normal_price - line.price_subtotal_incl

        return amount

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'].append('type')
        return result

    def _loader_params_account_tax(self):
        result = super()._loader_params_account_tax()
        result['search_params']['fields'].append('identification_letter')
        return result


class PosDailyReport(models.TransientModel):
    _name = 'pos.daily.reports.wizard'
    _description = 'Point of Sale Daily Report'

    pos_session_id = fields.Many2one('pos.session')

    def generate_report(self):
        data = {'date_start': False, 'date_stop': False, 'config_ids': self.pos_session_id.config_id.ids, 'session_ids': self.pos_session_id.ids}
        return self.env.ref('pos_l10n_se.pos_daily_report').report_action([], data=data)


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        data = super(ReportSaleDetails, self).get_sale_details(date_start, date_stop, config_ids, session_ids)
        if session_ids:
            session = self.env['pos.session'].search([('id', 'in', session_ids)])
            PF_list = self.env['pos.order_pro_forma'].search([('session_id', "=", session.id)])

            amount_PF = 0
            for order in PF_list:
                amount_PF += order.amount_total

            report_update = {
                'state': session.state,
                'PF_number': len(PF_list),
                'PF_Amount': amount_PF,
                'Discount_number': len(session.order_ids.filtered(lambda o: o.lines.filtered(lambda l: l.discount > 0))),
                'Discount_amount': session.get_total_discount()
            }
            data.update(report_update)
        return data


class PosConfig(models.Model):
    _inherit = 'pos.config'

    proformat_sequence = fields.Many2one('ir.sequence', string='Profo Order IDs Sequence', readonly=True,
                                  help="This sequence is automatically created by Odoo but you can change it "
                                       "to customize the reference numbers of your profo orders.", copy=False,
                                  ondelete='restrict')
    iface_sweden_fiscal_data_module = fields.Many2one(
        "iot.device",
        domain="[('type', '=', 'fiscal_data_module'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    @api.model_create_multi
    def create(self, vals_list):
        proforma_sequences = self.env['ir.sequence'].create([{
            'name': _('POS Profo Order %s', vals['name']),
            'padding': 4,
            'prefix': "Profo %s/" % vals['name'],
            'code': "pos.order_pro_forma",
        } for vals in vals_list])
        for proforma_sequence, vals in zip(proforma_sequences, vals_list):
            vals["proformat_sequence"] = proforma_sequence.id
        return super().create(vals_list)

    def _compute_iot_device_ids(self):
        super(PosConfig, self)._compute_iot_device_ids()
        for config in self:
            if config.is_posbox:
                config.iot_device_ids += config.iface_sweden_fiscal_data_module

    def _check_before_creating_new_session(self):
        if self.iface_sweden_fiscal_data_module:
            self._check_pos_settings_for_sweden()
        return super()._check_before_creating_new_session()

    def _check_pos_settings_for_sweden(self):
        if self.iface_sweden_fiscal_data_module and not self.company_id.vat:
            raise ValidationError(_("The company require an VAT number when you are using the blackbox."))
        if self.iface_sweden_fiscal_data_module and not self.cash_control:
            raise ValidationError(_("You cannot use the sweden blackbox without cash control."))
        if self.iface_sweden_fiscal_data_module and self.iface_splitbill:
            raise ValidationError(_("You cannot use the sweden blackbox with the bill splitting setting."))

    def get_order_sequence_number(self):
        return self.sequence_id.number_next_actual

    def get_profo_order_sequence_number(self):
        self.proformat_sequence._next()
        return self.proformat_sequence.number_next_actual

    def get_next_report_sequence_number(self):
        self.report_sequence_number._next()
        return self.report_sequence_number.number_next_actual


class PosOrder(models.Model):
    _inherit = 'pos.order'

    blackbox_signature = fields.Char("Electronic signature",
                                     help="Electronic signature returned by the Fiscal Data Module", readonly=True)
    blackbox_unit_id = fields.Char(readonly=True)
    blackbox_tax_category_a = fields.Float(readonly=True)
    blackbox_tax_category_b = fields.Float(readonly=True)
    blackbox_tax_category_c = fields.Float(readonly=True)
    blackbox_tax_category_d = fields.Float(readonly=True)
    is_refund = fields.Boolean(readonly=True, compute='_compute_is_refund')
    is_reprint = fields.Boolean(readonly=True)
    blackbox_device = fields.Many2one(related="session_id.config_id.iface_sweden_fiscal_data_module", readonly=True)

    @api.ondelete(at_uninstall=True)
    def _unlink_except_registered_order(self):
        for order in self:
            if order.config_id.iface_sweden_fiscal_data_module:
                raise UserError(_('Deleting of registered orders is not allowed.'))

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)
        fields.update({
            'blackbox_signature': ui_order.get('blackbox_signature'),
            'blackbox_unit_id': ui_order.get('blackbox_unit_id'),
            'blackbox_tax_category_a': ui_order.get('blackbox_tax_category_a'),
            'blackbox_tax_category_b': ui_order.get('blackbox_tax_category_b'),
            'blackbox_tax_category_c': ui_order.get('blackbox_tax_category_c'),
            'blackbox_tax_category_d': ui_order.get('blackbox_tax_category_d'),
        })
        return fields

    @api.depends('amount_total')
    def _compute_is_refund(self):
        for order in self:
            if order.amount_total < 0:
                order.is_refund = True

    def set_is_reprint(self):
        self.is_reprint = True

    def is_already_reprint(self):
        return self.is_reprint

    @api.model
    def create_from_ui(self, orders, draft=False):
        pro_forma_orders = [order['data'] for order in orders if order['data'].get('receipt_type') == "profo"]
        regular_orders = [order for order in orders if not order['data'].get('receipt_type') == "profo"]
        self.env['pos.order_pro_forma'].create_proforma_from_ui(pro_forma_orders)
        return super(PosOrder, self).create_from_ui(regular_orders, draft)

    def refund(self):
        for order in self:
            if order.config_id.iface_sweden_fiscal_data_module:
                raise UserError(_("Refunding registered orders is not allowed."))

        return super(PosOrder, self).refund()


class PosOrderProforma(models.Model):
    _name = 'pos.order_pro_forma'
    _description = 'Proforma order'

    name = fields.Char('Profo Order Ref', readonly=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.users'].browse(self.env.uid).company_id.id, readonly=True)
    currency_id = fields.Many2one("res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True,
                                  required=True)
    date_order = fields.Datetime('Order Date', readonly=True)
    create_date = fields.Datetime(string="Pro Forma Creation")
    user_id = fields.Many2one('res.users', 'Salesman', help="Person who uses the cash register. It can be a reliever, a student or an interim employee.", readonly=True)
    amount_total = fields.Float(readonly=True)
    lines = fields.One2many('pos.order_line_pro_forma', 'order_id', 'Order Lines', readonly=True, copy=True)
    pos_reference = fields.Char('Receipt Ref', readonly=True)
    session_id = fields.Many2one('pos.session', 'Session', readonly=True)
    partner_id = fields.Many2one('res.partner', 'Customer', readonly=True)
    config_id = fields.Many2one('pos.config', related='session_id.config_id', readonly=True)
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', 'Fiscal Position', readonly=True)
    table_id = fields.Many2one('restaurant.table', 'Table', readonly=True)

    blackbox_unit_id = fields.Char(readonly=True)
    blackbox_signature = fields.Char(readonly=True)
    blackbox_tax_category_a = fields.Float(readonly=True)
    blackbox_tax_category_b = fields.Float(readonly=True)
    blackbox_tax_category_c = fields.Float(readonly=True)
    blackbox_tax_category_d = fields.Float(readonly=True)

    def set_values(self, ui_order):
        return {
            'name': _('POS Proforma Order %s', ui_order['sequence_number']),
            'user_id': ui_order['user_id'] or False,
            'session_id': ui_order['pos_session_id'],
            'pos_reference': ui_order['name'],
            'lines': [self.env['pos.order_line_pro_forma']._order_line_fields(l) for l in ui_order['lines']] if ui_order['lines'] else False,
            'partner_id': ui_order['partner_id'] or False,
            'fiscal_position_id': ui_order['fiscal_position_id'],
            'amount_total': ui_order.get('amount_total'),
            'table_id': ui_order.get('table_id'),
            'blackbox_unit_id': ui_order.get('blackbox_unit_id'),
            'blackbox_signature': ui_order.get('blackbox_signature'),
            'date_order': parser.parse(ui_order['creation_date']).strftime("%Y-%m-%d %H:%M:%S"),
            'blackbox_tax_category_a': ui_order.get('blackbox_tax_category_a'),
            'blackbox_tax_category_b': ui_order.get('blackbox_tax_category_b'),
            'blackbox_tax_category_c': ui_order.get('blackbox_tax_category_c'),
            'blackbox_tax_category_d': ui_order.get('blackbox_tax_category_d'),
            'pricelist_id': ui_order.get('pricelist_id'),
        }

    @api.model
    def create_proforma_from_ui(self, orders):
        for ui_order in orders:
            values = self.set_values(ui_order)
            self.create(values)


class PosOrderLineProforma(models.Model):
    _name = 'pos.order_line_pro_forma'  # needs to be a new class
    _inherit = 'pos.order.line'
    _description = 'Proforma order line'

    order_id = fields.Many2one('pos.order_pro_forma')

    @api.model_create_multi
    def create(self, vals_list):
        # the pos.order.line create method consider 'order_id' is a pos.order
        # override to bypass it and generate a name
        for vals in vals_list:
            if vals.get('order_id') and not vals.get('name'):
                name = self.env['pos.order_pro_forma'].browse(vals['order_id']).name
                vals['name'] = "%s-%s" % (name, vals.get('id'))
        return super().create(vals_list)


class AccountTax(models.Model):
    _inherit = 'account.tax'

    identification_letter = fields.Char(compute='_compute_identification_letter')

    @api.depends('amount_type', 'amount')
    def _compute_identification_letter(self):
        for tax in self:
            if tax.type_tax_use == "sale" and (tax.amount_type == "percent" or tax.amount_type == "group"):
                if tax.amount == 25:
                    tax.identification_letter = "A"
                elif tax.amount == 12:
                    tax.identification_letter = "B"
                elif tax.amount == 6:
                    tax.identification_letter = "C"
                elif tax.amount == 0:
                    tax.identification_letter = "D"
                else:
                    tax.identification_letter = False
            else:
                tax.identification_letter = False
