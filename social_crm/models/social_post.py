# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SocialPost(models.Model):
    _inherit = 'social.post'

    use_leads = fields.Boolean('Use Leads', compute='_compute_use_leads')
    leads_opportunities_count = fields.Integer('Leads / Opportunities count', groups='sales_team.group_sale_salesman',
                                               compute='_compute_leads_opportunities_count', compute_sudo=True)

    def _compute_use_leads(self):
        for post in self:
            post.use_leads = self.env.user.has_group('crm.group_use_lead')

    def _compute_leads_opportunities_count(self):
        mapped_data = {}
        if self.source_id.ids:
            lead_data = self.env['crm.lead'].read_group(
                [('source_id', 'in', self.source_id.ids)],
                ['source_id'], ['source_id'])
            mapped_data = {datum['source_id'][0]: datum['source_id_count'] for datum in lead_data}
        for post in self:
            post.leads_opportunities_count = mapped_data.get(post.source_id.id, 0)

    def action_redirect_to_leads_opportunities(self):
        view = 'crm.crm_lead_all_leads' if self.use_leads else 'crm.crm_lead_opportunities'
        action = self.env["ir.actions.actions"]._for_xml_id(view)
        action['view_mode'] = 'tree,kanban,graph,pivot,form,calendar'
        action['domain'] = self._get_crm_utm_domain()
        action['context'] = {'active_test': False, 'create': False}
        return action

    def _get_crm_utm_domain(self):
        """ We want all records that match the UTMs """
        return [('source_id', '=', self.source_id.id)]
