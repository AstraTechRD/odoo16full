# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, tagged


@tagged('voip')
class TestVoipUserConfig(common.TransactionCase):

    def test_voip_user_config_access_rights(self):
        """
        Tests that users cannot read VoIP configuration of other users.
        """
        voip_user = self.env['res.users'].create({
            'login': "i_love_voip",
            'name': "Handsome VoIP User 😎",
        }).sudo(False)
        settings = voip_user.env['res.users.settings']._find_or_create_for_user(voip_user)
        settings.write({'voip_secret': "Top Secret 🤫"})
        evil_password_stealer = self.env['res.users'].create({
            'login': "i_hate_voip",
            'name': "Evil Password Stealer 👺",
        }).sudo(False)
        voip_user.env.flush_all()
        voip_user.env.invalidate_all()

        self.assertFalse(voip_user.with_user(evil_password_stealer).voip_secret)
