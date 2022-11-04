# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
from random import randint

from odoo import SUPERUSER_ID, _, fields, models
from odoo.exceptions import ValidationError


_logger = logging.getLogger(__name__)

INT_PHONE_NUMBER_FORMAT_REGEX = r'^\+[^+]+$'


class SDDMandate(models.Model):
    _inherit = 'sdd.mandate'

    signed_on = fields.Datetime(
        string="Signed On", help="The date of the signature", readonly=True, copy=False)
    signed_by = fields.Char(
        string="Signed By", help="The name of the signer", readonly=True, copy=False)
    signature = fields.Binary(string="Signature", readonly=True, copy=False)
    phone_number = fields.Char(
        string="Phone Number", help="The phone number used for verification by SMS code",
        readonly=True, copy=False)
    verification_code = fields.Char(string="Verification Code", readonly=True, copy=False)
    verified = fields.Boolean(string="Verified")

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') in ['closed', 'revoked']:
            linked_tokens = self.env['payment.token'].search([('sdd_mandate_id', 'in', self.ids)])
            linked_tokens.active = False
        return res

    def _send_verification_code(self, phone):
        """ Send a verification code to the provided phone number.

        The code allows to verify the ownership of the mandate.
        In Europe, it is required to register a signer' identity with mobile operators.

        Note: self.ensure_one()
        """
        self.ensure_one()

        if self.verified:
            raise ValidationError("SEPA: " + _("This mandate has already been verified."))
        if not re.match(INT_PHONE_NUMBER_FORMAT_REGEX, phone):
            raise ValidationError(
                "SEPA: " + _("The phone number should be in international format.")
            )
        self.write({
            'phone_number': phone.replace(' ', ''),
            'verification_code': randint(1000, 9999)
        })
        _logger.info(
            "sending SMS to %(phone)s with code %(code)s",
            {'phone': self.phone_number, 'code': self.verification_code}
        )
        if not self.env.registry.in_test_mode():
            self.env['sms.api'].sudo()._send_sms(
                [self.phone_number], _("Your confirmation code is %s", self.verification_code)
            )

    def _update_mandate(self, phone=None, code=None, signer=None, signature=None):
        """ Sign and confirm the mandate, then log all changes in the chatter.

        Note: self.ensure_one()
        """
        self.ensure_one()

        self._sign(signer, signature)  # Call _sign first to add the current user as a follower
        self._confirm(phone, code)

        # Log any change in the chatter
        message_list = []
        if signer and signature:
            message_list.append(_("The mandate was signed by %s.", signer))
        if phone and code:
            message_list.append(_("The mandate was verified with phone number %s.", phone))
        if message_list:
            self._message_log(body='<br/>'.join(message_list))

    def _sign(self, signer, signature):
        vals = {
            'signed_on': fields.Datetime.now()
        }
        if signature:
            vals.update({
                'signed_by': signer,
                'signature': signature,
            })
        self.write(vals)
        self.message_subscribe([self.partner_id.id])

    def _confirm(self, phone, code):
        """ Confirm the customer's ownership of the SEPA Direct Debit mandate.

        Confirmation succeeds if the verification codes match. Only the owner can confirm a mandate.
        """
        token_sudo = self.env['payment.token'].sudo().search(
            [('sdd_mandate_id', '=', self.id)], limit=1
        )
        if token_sudo.provider_id.sdd_sms_verification_required:
            if not (code and phone):
                raise ValidationError(
                    "SEPA: " + _("Both the phone number and the verification code are required.")
                )
            if self.phone_number != phone:
                raise ValidationError("SEPA: " + _("The phone number does not match."))
            if self.verification_code != code:
                raise ValidationError("SEPA: " + _("The verification code does not match."))

        template = self.env.ref('payment_sepa_direct_debit.mail_template_sepa_notify_validation')
        self.write({'state': 'active', 'verified': True})
        template.with_user(SUPERUSER_ID).send_mail(self.id)
