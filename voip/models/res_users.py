# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


# List of the VoIP-related fields that are configurable by the user using the
# `res.users` form view. Useful to override SELF_READABLE/WRITABLE_FIELDS.
VOIP_USER_CONFIGURATION_FIELDS = [
    'external_device_number',
    'how_to_call_on_mobile',
    'should_auto_reject_incoming_calls',
    'should_call_from_another_device',
    'voip_secret',
    'voip_username',
]

class ResUsers(models.Model):
    _inherit = 'res.users'

    last_seen_phone_call = fields.Many2one('voip.phonecall')
    # --------------------------------------------------------------------------
    # VoIP User Configuration Fields
    # --------------------------------------------------------------------------
    # These fields mirror those defined in `res.users.settings`. The reason they
    # are not directly defined in here is that we want these fields to have
    # different access rights than the rest of the fields of `res.users`. See
    # their definition in `res.users.settings` for comprehensive documentation.
    # --------------------------------------------------------------------------
    external_device_number = fields.Char(related='res_users_settings_id.external_device_number', inverse='_reflect_change_in_res_users_settings', related_sudo=False)
    how_to_call_on_mobile = fields.Selection(related='res_users_settings_id.how_to_call_on_mobile', inverse='_reflect_change_in_res_users_settings', related_sudo=False)
    should_auto_reject_incoming_calls = fields.Boolean(related='res_users_settings_id.should_auto_reject_incoming_calls', inverse='_reflect_change_in_res_users_settings', related_sudo=False)
    should_call_from_another_device = fields.Boolean(related='res_users_settings_id.should_call_from_another_device', inverse='_reflect_change_in_res_users_settings', related_sudo=False)
    voip_secret = fields.Char(related='res_users_settings_id.voip_secret', inverse='_reflect_change_in_res_users_settings', related_sudo=False)
    voip_username = fields.Char(related='res_users_settings_id.voip_username', inverse='_reflect_change_in_res_users_settings', related_sudo=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + VOIP_USER_CONFIGURATION_FIELDS

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + VOIP_USER_CONFIGURATION_FIELDS

    @api.model
    def reset_last_seen_phone_call(self):
        domain = [
            ('user_id', '=', self.env.user.id),
            ('call_date', '!=', False),
            ('in_queue', '=', True),
        ]
        last_call = self.env['voip.phonecall'].search(domain, order='call_date desc', limit=1)
        self.env.user.last_seen_phone_call = last_call.id

    def _init_messaging(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        return {
            **super()._init_messaging(),
            'voipConfig': {
                'mode': get_param('voip.mode', default='demo'),
                'pbxAddress': get_param('voip.pbx_ip', default="localhost"),
                'webSocketUrl': get_param('voip.wsServer', default="ws://localhost"),
            },
        }

    def _reflect_change_in_res_users_settings(self):
        """
        Updates the values of the VoIP User Configuration Fields in `res_users_settings_ids` to have the same values as
        their related fields in `res.users`. If there is no `res.users.settings` record for the user, then the record is
        created.

        This method is intended to be used as an inverse for VoIP Configuration Fields.
        """
        for user in self:
            res_users_settings_record = self.env['res.users.settings']._find_or_create_for_user(user)
            res_users_settings_record.update({
                'external_device_number': user.external_device_number,
                'how_to_call_on_mobile': user.how_to_call_on_mobile,
                'should_auto_reject_incoming_calls': user.should_auto_reject_incoming_calls,
                'should_call_from_another_device': user.should_call_from_another_device,
                'voip_secret': user.voip_secret,
                'voip_username': user.voip_username,
            })
