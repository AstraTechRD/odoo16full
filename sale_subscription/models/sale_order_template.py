# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrderTemplate(models.Model):
    _name = "sale.order.template"
    _inherit = 'sale.order.template'

    is_subscription = fields.Boolean(compute='_compute_is_subscription', search='_search_is_subscription')
    recurrence_id = fields.Many2one('sale.temporal.recurrence', string='Recurrence')
    recurring_rule_boundary = fields.Selection([
        ('unlimited', 'Forever'),
        ('limited', 'Fixed')
    ], string='Duration', default='unlimited')
    recurring_rule_count = fields.Integer(string="End After", default=1)
    recurring_rule_type = fields.Selection([('month', 'Months'), ('year', 'Years'), ], help="Contract duration", default='month')

    user_closable = fields.Boolean(string="Self closable",
                                   help="If checked, the user will be able to close his account from the frontend")
    journal_id = fields.Many2one(
        'account.journal', string="Invoicing Journal",
        domain="[('type', '=', 'sale')]", company_dependent=True, check_company=True,
        help="If set, subscriptions with this template will invoice in this journal; "
             "otherwise the sales journal with the lowest sequence is used.")
    color = fields.Integer()
    auto_close_limit = fields.Integer(
        string="Automatic Closing", default=15,
        help="If the chosen payment method has failed to renew the subscription after this time, "
             "the subscription is automatically closed.")
    good_health_domain = fields.Char(string='Good Health', default='[]',
                                     help="Domain used to change subscription's Kanban state with a 'Good' rating")
    bad_health_domain = fields.Char(string='Bad Health', default='[]',
                                    help="Domain used to change subscription's Kanban state with a 'Bad' rating")

    # ARJ TODO master: use a setting or a config parameter
    invoice_mail_template_id = fields.Many2one(
        'mail.template', string='Invoice Email Template', domain=[('model', '=', 'account.move')],
        default=lambda self: self.env.ref('sale_subscription.mail_template_subscription_invoice', raise_if_not_found=False))

    @api.depends('sale_order_template_line_ids.product_id', 'recurrence_id')
    def _compute_is_subscription(self):
        for template in self:
            recurring_product = template.sale_order_template_line_ids.mapped('recurring_invoice')
            template.is_subscription = recurring_product and template.recurrence_id

    @api.model
    def _search_is_subscription(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))
        recurring_templates = self.env['sale.order.template'].search([('recurrence_id', '!=', False)])
        if (operator == '=' and value) or (operator == '!=' and not value):
            # Look for subscription templates
            domain = [('id', 'in', recurring_templates.ids)]
        else:
            # Look for non subscription templates
            domain = [('id', 'not in', recurring_templates.ids)]
        return domain


class SaleOrderTemplateLine(models.Model):
    _name = "sale.order.template.line"
    _inherit = ['sale.order.template.line']

    recurring_invoice = fields.Boolean(related='product_id.recurring_invoice')
    recurrence_id = fields.Many2one(related="sale_order_template_id.recurrence_id")

    # ARJ TODO MASTER move that in temporal to make it work with rental
    def open_product_pricing(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('sale_temporal.product_pricing_action')
        action['domain'] = [('product_template_id', 'in', self.product_id.product_tmpl_id.ids),
                            ('recurrence_id', '=', self.recurrence_id.id)]
        return action


class SaleOrderTemplateOption(models.Model):
    _name = "sale.order.template.option"
    _inherit = ['sale.order.template.option']

    recurring_invoice = fields.Boolean(related='product_id.recurring_invoice')
    recurrence_id = fields.Many2one(related="sale_order_template_id.recurrence_id")
