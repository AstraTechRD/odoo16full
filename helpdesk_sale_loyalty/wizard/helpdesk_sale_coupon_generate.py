# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _

class HelpdeskSaleCouponGenerate(models.TransientModel):
    _name = "helpdesk.sale.coupon.generate"
    _description = 'Generate Sales Coupon from Helpdesk'


    def _get_default_program(self):
        return self.env['loyalty.program'].search([('applies_on', '=', 'current'), ('trigger', '=', 'with_code')], limit=1)

    ticket_id = fields.Many2one('helpdesk.ticket')
    company_id = fields.Many2one(related="ticket_id.company_id")
    program = fields.Many2one('loyalty.program', string="Coupon Program", default=_get_default_program,
        domain=lambda self: [('applies_on', '=', 'current'), ('trigger', '=', 'with_code'), '|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])

    def generate_coupon(self):
        """Generates a coupon for the selected program and the partner linked
        to the ticket
        """
        vals = {
            'partner_id': self.ticket_id.partner_id.id,
            'program_id': self.program.id,
            'points': max(self.program.reward_ids.mapped('required_points')) if self.program.applies_on == 'future' else 0,
        }
        coupon = self.env['loyalty.card'].sudo().create(vals)
        self.ticket_id.coupon_ids |= coupon
        view = self.env.ref('helpdesk_sale_loyalty.loyalty_card_view_form_helpdesk_sale_loyalty', raise_if_not_found=False)
        self.ticket_id.message_post_with_view(
            'helpdesk.ticket_conversion_link', values={'created_record': coupon, 'message': _('Coupon created')},
            subtype_id=self.env.ref('mail.mt_note').id, author_id=self.env.user.partner_id.id
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'loyalty.card',
            'res_id': coupon.id,
            'view_mode': 'form',
            'view_id': view.id,
            'target': 'new',
        }
