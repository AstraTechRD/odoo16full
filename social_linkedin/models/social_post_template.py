# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class SocialPostTemplate(models.Model):
    _inherit = 'social.post.template'

    display_linkedin_preview = fields.Boolean('Display LinkedIn Preview', compute='_compute_display_linkedin_preview')
    linkedin_preview = fields.Html('LinkedIn Preview', compute='_compute_linkedin_preview')

    @api.depends('message', 'account_ids.media_id.media_type')
    def _compute_display_linkedin_preview(self):
        for post in self:
            post.display_linkedin_preview = (
                post.message and
                'linkedin' in post.account_ids.media_id.mapped('media_type'))

    @api.depends(lambda self: ['message', 'image_ids'] + self._get_post_message_modifying_fields())
    def _compute_linkedin_preview(self):
        for post in self:
            post.linkedin_preview = self.env['ir.qweb']._render('social_linkedin.linkedin_preview', {
                **post._prepare_preview_values("instagram"),
                'message': post._prepare_post_content(
                    post.message,
                    'linkedin',
                    **{field: post[field] for field in post._get_post_message_modifying_fields()}),
                'images': [
                    image.with_context(bin_size=False).datas
                    for image in post.image_ids.sorted(lambda image: image._origin.id or image.id, reverse=True)
                ],
            })
