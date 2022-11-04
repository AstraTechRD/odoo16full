# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from ast import literal_eval

from odoo import api, fields, models, _

_logger = logging.getLogger


class SaleOrderAlert(models.Model):
    _name = 'sale.order.alert'
    _description = 'Sale Order Alert'
    _inherits = {'base.automation': 'automation_id'}
    _check_company_auto = True

    @api.model
    def default_get(self, default_fields):
        res = super().default_get(default_fields)
        if 'model_id' in default_fields:
            # model_id default cannot be specified at field level
            # because model_id is an inherited field from base.automation
            res['model_id'] = self.env['ir.model']._get_id('sale.order')
        return res

    automation_id = fields.Many2one('base.automation', 'Automated Action', required=True, ondelete='restrict')
    action = fields.Selection([
        ('next_activity', 'Create next activity'),
        ('set_stage', 'Set a stage on the subscription'), ('set_to_renew', 'Mark as To Renew'), ('email', 'Send an email to the customer'),
        ('sms', 'Send an SMS Text Message to the customer')], string='Action', required=True, default=None)
    trigger_condition = fields.Selection([
        ('on_create_or_write', 'Modification'), ('on_time', 'Timed Condition')], string='Trigger On', required=True, default='on_create_or_write')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    subscription_template_ids = fields.Many2many('sale.order.template', string='Quotation templates', check_company=True)
    customer_ids = fields.Many2many('res.partner', string='Customers')
    company_id = fields.Many2one('res.company', string='Company')
    mrr_min = fields.Monetary('MRR Range Min', currency_field='currency_id')
    team_ids = fields.Many2many('crm.team', string='Sales Team')
    mrr_max = fields.Monetary('MRR Range Max', currency_field='currency_id')
    product_ids = fields.Many2many(
        'product.product', string='Specific Products',
        domain="[('product_tmpl_id.recurring_invoice', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    mrr_change_amount = fields.Float('MRR Change Amount')
    mrr_change_unit = fields.Selection(selection='_get_selection_mrr_change_unit', string='MRR Change Unit', default='percentage')
    mrr_change_period = fields.Selection([('1month', '1 Month'), ('3months', '3 Months')], string='MRR Change Period',
                                         default='1month', help="Period over which the KPI is calculated")
    rating_percentage = fields.Integer('Rating Percentage', help="Rating Satisfaction is the ratio of positive rating to total number of rating.")
    rating_operator = fields.Selection([('>', 'greater than'), ('<', 'less than')], string='Rating Operator', default='>')
    stage_from_id = fields.Many2one('sale.order.stage', help="Trigger on changes of stage. Trigger over all stages if not set")
    stage_to_id = fields.Many2one('sale.order.stage')
    stage_id = fields.Many2one('sale.order.stage', string='Stage')
    activity_user = fields.Selection([
        ('contract', 'Subscription Salesperson'),
        ('channel_leader', 'Sales Team Leader'),
        ('users', 'Specific Users'),
    ], string='Assign To')
    activity_user_ids = fields.Many2many('res.users', string='Specific Users')
    subscription_count = fields.Integer(compute='_compute_subscription_count')
    cron_nextcall = fields.Datetime(compute='_compute_nextcall', store=False)

    def _get_selection_mrr_change_unit(self):
        return [('percentage', '%'), ('currency', self.env.company.currency_id.symbol)]

    def _compute_subscription_count(self):
        for alert in self:
            domain = literal_eval(alert.filter_domain) if alert.filter_domain else []
            alert.subscription_count = self.env['sale.order'].search_count(domain)

    def _configure_filter_domain(self):
        for alert in self:
            domain = [('is_subscription', '=', True)]
            if alert.subscription_template_ids:
                domain += [('sale_order_template_id', 'in', alert.subscription_template_ids.ids)]
            if alert.customer_ids:
                domain += [('partner_id', 'in', alert.customer_ids.ids)]
            if alert.team_ids:
                domain += [('team_id', 'in', alert.team_ids.ids)]
            if alert.company_id:
                domain += [('company_id', '=', alert.company_id.id)]
            if alert.mrr_min:
                domain += [('recurring_monthly', '>=', alert.mrr_min)]
            if alert.mrr_max:
                domain += [('recurring_monthly', '<=', alert.mrr_max)]
            if alert.product_ids:
                domain += [('order_line.product_id', 'in', alert.product_ids.ids)]
            if alert.mrr_change_amount:
                if alert.mrr_change_unit == 'percentage':
                    domain += [('kpi_%s_mrr_percentage' % alert.mrr_change_period, '>', alert.mrr_change_amount / 100)]
                else:
                    domain += [('kpi_%s_mrr_delta' % alert.mrr_change_period, '>', alert.mrr_change_amount)]
            if alert.rating_percentage:
                domain += [('percentage_satisfaction', alert.rating_operator, alert.rating_percentage)]
            if alert.stage_to_id:
                domain += [('stage_id', '=', alert.stage_to_id.id)]
            super(SaleOrderAlert, alert).write({'filter_domain': domain})

    def unlink(self):
        self.automation_id.active = False
        return super().unlink()

    def _configure_filter_pre_domain(self):
        for alert in self:
            domain = []
            if alert.stage_from_id:
                domain = [('stage_id', '=', alert.stage_from_id.id)]
            super(SaleOrderAlert, alert).write({'filter_pre_domain': domain})

    def _configure_alert_from_action(self, vals_list):
        # Unlink the children server actions if not needed anymore
        self.filtered(lambda alert: alert.action != 'next_activity' and alert.child_ids).unlink()
        field_names = ['stage_id', 'to_renew']
        tag_fields = self.env['ir.model.fields'].search([('model', 'in', self.mapped('model_name')), ('name', 'in', field_names)])
        for alert, vals in zip(self, vals_list):
            field_name = None
            action_value = None
            if alert.action == 'set_stage' and alert.stage_id:
                field_name = 'stage_id'
                action_value = alert.stage_id.id
            elif alert.action == 'set_to_renew':
                field_name = 'to_renew'
                action_value = True
            if field_name and action_value:
                tag_field = tag_fields.filtered(lambda t: t.name == field_name)
                # Require sudo to write on ir.actions.server fields
                super(SaleOrderAlert, alert.sudo()).write({
                    'state': 'object_write',
                    'fields_lines': [(5, 0, 0), (0, False, {
                        'evaluation_type': 'equation',
                        'col1': tag_field.id,
                        'value': action_value})
                    ]}
                )

            elif vals.get('action') in ('email', 'sms'):
                super(SaleOrderAlert, alert).write({'state': vals.get('action')})
            elif vals.get('action') == 'next_activity' or vals.get('activity_user_ids') or vals.get('activity_user'):
                alert._set_activity_action()




    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('trigger_condition'):
                vals['trigger'] = vals['trigger_condition']
        alerts = super().create(vals_list)
        alerts._configure_filter_domain()
        alerts._configure_filter_pre_domain()
        alerts._configure_alert_from_action(vals_list)
        return alerts

    def write(self, vals):
        if vals.get('trigger_condition'):
            vals['trigger'] = vals['trigger_condition']
        res = super().write(vals)
        self._configure_filter_domain()
        self._configure_filter_pre_domain()
        self._configure_alert_from_action([vals])
        return res

    def action_view_subscriptions(self):
        self.ensure_one()
        domain = literal_eval(self.filter_domain) if self.filter_domain else [('is_subscription', '=', True)]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Subscriptions'),
            'res_model': 'sale.order',
            'view_mode': 'kanban,tree,form,pivot,graph,cohort,activity',
            'domain': domain,
            'context': {'create': False},
        }

    def run_cron_manually(self):
        self.ensure_one()
        domain = literal_eval(self.filter_domain)
        subs = self.env['sale.order'].search(domain)
        ctx = {
            'active_model': 'sale.order',
            'active_ids': subs.ids,
            'domain_post': domain,
        }
        self.action_server_id.with_context(**ctx).run()

    def _set_activity_action(self):
        self.child_ids.unlink()
        for alert in self:
            if self.activity_user == 'users':
                seq = 1
                action_values = []
                for user in alert.activity_user_ids:
                    action_values.append({
                        'name': '%s-%s' % (alert.name, seq),
                        'sequence': seq,
                        'state': 'next_activity',
                        'model_id': alert.model_id.id,
                        'activity_summary': alert.activity_summary,
                        'activity_type_id': alert.activity_type_id.id,
                        'activity_note': alert.activity_note,
                        'activity_date_deadline_range': alert.activity_date_deadline_range,
                        'activity_date_deadline_range_type': alert.activity_date_deadline_range_type,
                        'activity_user_type': 'specific',
                        'activity_user_id': user.id,
                        'usage': 'base_automation',
                    })
                    seq += 1
                action_ids = self.env['ir.actions.server'].create(action_values)
                alert.write({
                    'state': 'multi',
                    'child_ids': [(4, act_id) for act_id in action_ids.ids]
                })
            elif self.activity_user == 'contract':
                alert.write({
                    'state': 'next_activity',
                    'activity_user_type': 'generic',
                    'activity_user_field_name': 'user_id',
                })
            elif self.activity_user == 'channel_leader':
                alert.write({
                    'state': 'next_activity',
                    'activity_user_type': 'generic',
                    'activity_user_field_name': 'team_user_id',
                })

    def _compute_nextcall(self):
        cron = self.env.ref('sale_subscription.ir_cron_sale_subscription_update_kpi', raise_if_not_found=False)
        if not cron:
            self.update({'cron_nextcall': False})
        else:
            nextcall = cron.read(fields=['nextcall'])[0]
            self.update({'cron_nextcall': fields.Datetime.to_string(nextcall['nextcall'])})
