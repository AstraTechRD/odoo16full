# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import SUPERUSER_ID, api, fields, models, _


class ProposeChange(models.TransientModel):
    _name = 'propose.change'
    _description = 'Propose a change in the production'

    workorder_id = fields.Many2one(
        'mrp.workorder', 'Workorder', required=True, ondelete='cascade')
    title = fields.Char('title')
    step_id = fields.Many2one('quality.check', 'Step to change')
    note = fields.Html('New Instruction')
    comment = fields.Char('Comment')
    picture = fields.Binary('Picture')
    change_type = fields.Selection([
        ('update_step', 'Update Current Step'),
        ('remove_step', 'Remove Current Step'),
        ('set_picture', 'Set Picture')], 'Type of Change')

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'step_id' in defaults:
            step = self.env['quality.check'].browse(defaults.get('step_id'))
            defaults['title'] = step.title
        return defaults

    def process(self):
        for wizard in self:
            if wizard.title != wizard.step_id.title:
                wizard.step_id.title = wizard.title
            if wizard.change_type == 'update_step':
                wizard._do_update_step()
            elif wizard.change_type == 'remove_step':
                wizard._do_remove_step()
            elif wizard.change_type == 'set_picture':
                wizard._do_set_picture()

    def _workorder_name(self):
        return self.env.user.name

    def _do_update_step(self, notify_bom=True):
        self.ensure_one()
        self.step_id.note = self.note
        if notify_bom and self.workorder_id.production_id.bom_id:
            body = Markup(_("<b>New Instruction suggested by %s</b><br/>%s<br/><b>Reason: %s</b>")) % (self._workorder_name(), self.note, self.comment)
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('mrp.model_mrp_bom').id,
                'res_id': self.workorder_id.production_id.bom_id.id,
                'user_id': self.workorder_id.product_id.responsible_id.id or SUPERUSER_ID,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('BoM feedback %s (%s)', self.step_id.title, self.workorder_id.production_id.name),
                'note': body,
            })

    def _do_remove_step(self, notify_bom=True):
        self.ensure_one()
        if not self.step_id.point_id and not(self.step_id.test_type.startswith('register_')):
            # remove additionmal step
            self.step_id.workorder_id._change_quality_check('next')
            self.step_id.unlink()

        self.step_id.is_deleted = True
        bom = self.step_id.workorder_id.production_id.bom_id
        if notify_bom and bom:
            body = Markup(_("<b>%s suggests to delete this instruction</b>")) % self._workorder_name()
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('mrp.model_mrp_bom').id,
                'res_id': bom.id,
                'user_id': self.workorder_id.product_id.responsible_id.id or SUPERUSER_ID,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('BoM feedback %s (%s)', self.step_id.title, self.workorder_id.production_id.name),
                'note': body,
            })

    @api.model
    def image_url(self, record, field):
        """ Returns a local url that points to the image field of a given browse record. """
        return '/web/image/%s/%s/%s' % (record._name, record.id, field)

    def _do_set_picture(self, notify_bom):
        self.ensure_one()
        self.step_id.worksheet_document = self.picture
        bom = self.step_id.workorder_id.production_id.bom_id
        if notify_bom and bom:
            body = Markup(_("<b>%s suggests to use this document as instruction</b><br/><img style='max-width: 75%%' class='img-fluid' src=%s/>"))\
                % (self._workorder_name(), self.image_url(self, 'picture'))
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env.ref('mrp.model_mrp_bom').id,
                'res_id': bom.id,
                'user_id': self.workorder_id.product_id.responsible_id.id or SUPERUSER_ID,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('BoM feedback %s (%s)', self.step_id.title, self.workorder_id.production_id.name),
                'note': body,
            })
