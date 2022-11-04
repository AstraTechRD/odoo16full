# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import logging
import mimetypes
import re

from PyPDF2 import PdfFileReader

from odoo import http, models, tools, Command, _
from odoo.http import request, content_disposition
from odoo.addons.iap.tools import iap_tools

_logger = logging.getLogger()


class Sign(http.Controller):

    def get_document_qweb_context(self, sign_request_id, token, **post):
        sign_request = http.request.env['sign.request'].sudo().browse(sign_request_id).exists()
        if not sign_request:
            return request.render('sign.deleted_sign_request')
        current_request_item = sign_request.request_item_ids.filtered(lambda r: r.access_token == token)
        if not current_request_item and sign_request.access_token != token:
            return request.not_found()

        sign_item_types = http.request.env['sign.item.type'].sudo().search_read([])

        # Currently only Signature, Initials, Text are allowed to be added while signing
        edit_while_signing_allowed_type_ids = {
            request.env.ref('sign.sign_item_type_signature').id,
            request.env.ref('sign.sign_item_type_initial').id,
            request.env.ref('sign.sign_item_type_text').id,
        }
        for item_type in sign_item_types:
            item_type['edit_while_signing_allowed'] = item_type['id'] in edit_while_signing_allowed_type_ids

        if current_request_item:
            for item_type in sign_item_types:
                if item_type['auto_field']:
                    try:
                        auto_field = current_request_item.partner_id.mapped(item_type['auto_field'])
                        item_type['auto_value'] = auto_field[0] if auto_field and not isinstance(auto_field, models.BaseModel) else ''
                    except Exception:
                        item_type['auto_value'] = ''
                if item_type['item_type'] in ['signature', 'initial']:
                    signature_field_name = 'sign_signature' if item_type['item_type'] == 'signature' else 'sign_initials'
                    user_signature = current_request_item._get_user_signature(signature_field_name)
                    user_signature_frame = current_request_item._get_user_signature_frame(signature_field_name+'_frame')
                    item_type['auto_value'] = 'data:image/png;base64,%s' % user_signature.decode() if user_signature else False
                    item_type['frame_value'] = 'data:image/png;base64,%s' % user_signature_frame.decode() if user_signature_frame else False

            if current_request_item.state == 'sent':
                """ When signer attempts to sign the request again,
                its localisation should be reset.
                We prefer having no/approximative (from geoip) information
                than having wrong old information (from geoip/browser)
                on the signer localisation.
                """
                current_request_item.write({
                    'latitude': request.geoip.get('latitude', 0.0),
                    'longitude': request.geoip.get('longitude', 0.0),
                })

        item_values = {}
        frame_values = {}
        sr_values = http.request.env['sign.request.item.value'].sudo().search([('sign_request_id', '=', sign_request.id), '|', ('sign_request_item_id', '=', current_request_item.id), ('sign_request_item_id.state', '=', 'completed')])
        for value in sr_values:
            item_values[value.sign_item_id.id] = value.value
            frame_values[value.sign_item_id.id] = value.frame_value

        if sign_request.state != 'shared':
            request.env['sign.log'].sudo().create({
                'sign_request_id': sign_request.id,
                'sign_request_item_id': current_request_item.id,
                'action': 'open',
            })

        return {
            'sign_request': sign_request,
            'current_request_item': current_request_item,
            'state_to_sign_request_items_map': dict(tools.groupby(sign_request.request_item_ids, lambda sri: sri.state)),
            'token': token,
            'nbComments': len(sign_request.message_ids.filtered(lambda m: m.message_type == 'comment')),
            'isPDF': (sign_request.template_id.attachment_id.mimetype.find('pdf') > -1),
            'webimage': re.match('image.*(gif|jpe|jpg|png)', sign_request.template_id.attachment_id.mimetype),
            'hasItems': len(sign_request.template_id.sign_item_ids) > 0,
            'sign_items': sign_request.template_id.sign_item_ids,
            'item_values': item_values,
            'frame_values': frame_values,
            'frame_hash': current_request_item.frame_hash if current_request_item else '',
            'role': current_request_item.role_id.id if current_request_item else 0,
            'role_name': current_request_item.role_id.name if current_request_item else '',
            'readonly': not (current_request_item and current_request_item.state == 'sent' and sign_request.state in ['sent', 'shared']),
            'sign_item_types': sign_item_types,
            'sign_item_select_options': sign_request.template_id.sign_item_ids.mapped('option_ids'),
            'refusal_allowed': sign_request.refusal_allowed and sign_request.state == 'sent',
            'portal': post.get('portal'),
        }

    # -------------
    #  HTTP Routes
    # -------------

    @http.route(['/sign/<share_link>'], type='http', auth='public')
    def share_link(self, share_link, **post):
        """
        This controller is used for retro-compatibility of old shared links. share_link was a token saved on the
        template. We map them to the shared sign request created during upgrade and redirect to the correct URL.
        :param share_link: share
        :return: redirect to the sign_document_from_mail controller
        """
        sign_request_item = request.env['sign.request.item'].sudo().search([('access_token', '=', share_link)], limit=1)
        if not sign_request_item or sign_request_item.sign_request_id.state != 'shared':
            return request.not_found()
        return request.redirect('/sign/document/mail/%s/%s' % (sign_request_item.sign_request_id.id, sign_request_item.access_token))

    @http.route(["/sign/document/mail/<int:id>/<token>"], type='http', auth='public')
    def sign_document_from_mail(self, id, token):
        sign_request = request.env['sign.request'].sudo().browse(id)
        if not sign_request:
            return http.request.render('sign.deleted_sign_request')
        current_request_item = sign_request.request_item_ids.filtered(lambda r: r.access_token == token)
        current_request_item.access_via_link = True
        return request.redirect('/sign/document/%s/%s' % (id, token))

    @http.route(["/sign/document/<int:sign_request_id>/<token>"], type='http', auth='public', website=True)
    def sign_document_public(self, sign_request_id, token, **post):
        document_context = self.get_document_qweb_context(sign_request_id, token, **post)
        if not isinstance(document_context, dict):
            return document_context

        current_request_item = document_context.get('current_request_item')
        if current_request_item and current_request_item.partner_id.lang:
            http.request.env.context = dict(http.request.env.context, lang=current_request_item.partner_id.lang)
        return http.request.render('sign.doc_sign', document_context)

    @http.route(['/sign/download/<int:id>/<token>/<download_type>'], type='http', auth='public')
    def download_document(self, id, token, download_type, **post):
        sign_request = http.request.env['sign.request'].sudo().browse(id).exists()
        if not sign_request or sign_request.access_token != token:
            return http.request.not_found()

        document = None
        if download_type == "log":
            report_action = http.request.env['ir.actions.report'].sudo()
            pdf_content, __ = report_action._render_qweb_pdf(
                'sign.action_sign_request_print_logs',
                sign_request.id,
                data={'format_date': tools.format_date}
            )
            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
                ('Content-Disposition', 'attachment; filename=' + "Certificate.pdf;")
            ]
            return request.make_response(pdf_content, headers=pdfhttpheaders)
        elif download_type == "origin":
            document = sign_request.template_id.attachment_id.datas
        elif download_type == "completed":
            document = sign_request.completed_document
            if not document:
                if sign_request._check_is_encrypted():# if the document is completed but the document is encrypted
                    return request.redirect('/sign/password/%(request_id)s/%(access_token)s' % {'request_id': id, 'access_token': token})
                sign_request._generate_completed_document()
                document = sign_request.completed_document

        if not document:
            # Shouldn't it fall back on 'origin' download type?
            return request.redirect("/sign/document/%(request_id)s/%(access_token)s" % {'request_id': id, 'access_token': token})

        # Avoid to have file named "test file.pdf (V2)" impossible to open on Windows.
        # This line produce: test file (V2).pdf
        extension = '.' + sign_request.template_id.attachment_id.mimetype.replace('application/', '').replace(';base64', '')
        filename = sign_request.reference.replace(extension, '') + extension

        return http.request.make_response(
            base64.b64decode(document),
            headers = [
                ('Content-Type', mimetypes.guess_type(filename)[0] or 'application/octet-stream'),
                ('Content-Disposition', content_disposition(filename))
            ]
        )

    @http.route(['/sign/password/<int:sign_request_id>/<token>'], type='http', auth='public')
    def check_password_page(self, sign_request_id, token, **post):
        values = http.request.params.copy()
        request_item = http.request.env['sign.request.item'].sudo().search([
            ('sign_request_id', '=', sign_request_id),
            ('state', '=', 'completed'),
            ('sign_request_id.access_token', '=', token)], limit=1)
        if not request_item:
            return http.request.not_found()

        if 'password' not in http.request.params:
            return http.request.render('sign.encrypted_ask_password')

        password = http.request.params['password']
        template_id = request_item.sign_request_id.template_id

        old_pdf = PdfFileReader(io.BytesIO(base64.b64decode(template_id.attachment_id.datas)), strict=False, overwriteWarnings=False)
        if old_pdf.isEncrypted and not old_pdf.decrypt(password):
            values['error'] = _("Wrong password")
            return http.request.render('sign.encrypted_ask_password', values)

        request_item.sign_request_id._generate_completed_document(password)
        request_item.sign_request_id._send_completed_document()
        return request.redirect('/sign/document/%(request_id)s/%(access_token)s' % {'request_id': sign_request_id, 'access_token': token})

    # -------------
    #  JSON Routes
    # -------------
    @http.route(["/sign/get_document/<int:id>/<token>"], type='json', auth='user')
    def get_document(self, id, token):
        return http.Response(template='sign._doc_sign', qcontext=self.get_document_qweb_context(id, token)).render()

    @http.route(["/sign/update_user_signature"], type="json", auth="user")
    def update_signature(self, sign_request_id, role, signature_type=None, datas=None, frame_datas=None):
        sign_request_item_sudo = http.request.env['sign.request.item'].sudo().search([('sign_request_id', '=', sign_request_id), ('role_id', '=', role)], limit=1)
        user = http.request.env.user
        allowed = sign_request_item_sudo.partner_id.id == user.partner_id.id
        if not allowed or signature_type not in ['sign_signature', 'sign_initials'] or not user:
            return False
        user[signature_type] = datas[datas.find(',') + 1:]
        if frame_datas:
            user[signature_type+'_frame'] = frame_datas[frame_datas.find(',') + 1:]
        return True

    @http.route(['/sign/new_partners'], type='json', auth='user')
    def new_partners(self, partners=[]):
        ResPartner = http.request.env['res.partner']
        pIDs = []
        for p in partners:
            existing = ResPartner.search([('email', '=', p[1])], limit=1)
            pIDs.append(existing.id if existing else ResPartner.create({'name': p[0], 'email': p[1]}).id)
        return pIDs

    @http.route(['/sign/send_public/<int:id>/<token>'], type='json', auth='public')
    def make_public_user(self, id, token, name=None, mail=None):
        sign_request = http.request.env['sign.request'].sudo().search([('id', '=', id), ('access_token', '=', token)])
        if not sign_request or len(sign_request.request_item_ids) != 1 or sign_request.request_item_ids.partner_id:
            return False

        ResPartner = http.request.env['res.partner'].sudo()
        partner = ResPartner.search([('email', '=', mail)], limit=1)
        if not partner:
            partner = ResPartner.create({'name': name, 'email': mail})

        new_sign_request = sign_request.with_user(sign_request.create_uid).with_context(no_sign_mail=True).copy({
            'reference': sign_request.reference.replace('-%s' % _("Shared"), ''),
            'request_item_ids': [Command.create({
                'partner_id': partner.id,
                'role_id': sign_request.request_item_ids[0].role_id.id,
            })],
            'state': 'sent',
        })
        return {"requestID": new_sign_request.id, "requestToken": new_sign_request.access_token, "accessToken": new_sign_request.request_item_ids[0].access_token}

    @http.route([
        '/sign/send-sms/<int:id>/<token>/<phone_number>',
        ], type='json', auth='public')
    def send_sms(self, id, token, phone_number):
        request_item = http.request.env['sign.request.item'].sudo().search([('sign_request_id', '=', id), ('access_token', '=', token), ('state', '=', 'sent')], limit=1)
        if not request_item:
            return False
        if request_item.role_id.auth_method == 'sms':
            request_item.sms_number = phone_number
            try:
                request_item._send_sms()
            except iap_tools.InsufficientCreditError:
                _logger.warning('Unable to send SMS: no more credits')
                request_item.sign_request_id.activity_schedule(
                    'mail.mail_activity_data_todo',
                    note=_("%s couldn't sign the document due to an insufficient credit error.", request_item.partner_id.display_name),
                    user_id=request_item.sign_request_id.create_uid.id
                )
                return False
        return True

    def _validate_auth_method(self, request_item_sudo, sms_token=None):
        if request_item_sudo.role_id.auth_method == 'sms':
            has_sms_credits = request.env['iap.account'].sudo().get_credits('sms') > 0  # credits > 0 because the credit was already spent
            # if there are no sms credits, we still allow the user to sign it
            if not sms_token and not has_sms_credits:
                request_item_sudo.signed_without_extra_auth = True
                return {'success': True}
            if not sms_token or sms_token != request_item_sudo.sms_token:
                return {
                    'success': False,
                    'sms': True
                }
            request_item_sudo.sign_request_id._message_log(
                body=_('%s validated the signature by SMS with the phone number %s.') % (request_item_sudo.partner_id.display_name, request_item_sudo.sms_number)
            )
            return {'success': True}
        return {'success': False}

    @http.route([
        '/sign/sign/<int:sign_request_id>/<token>',
        '/sign/sign/<int:sign_request_id>/<token>/<sms_token>'
    ], type='json', auth='public')
    def sign(self, sign_request_id, token, sms_token=False, signature=None, **kwargs):
        request_item_sudo = http.request.env['sign.request.item'].sudo().search([
            ('sign_request_id', '=', sign_request_id),
            ('access_token', '=', token),
            ('state', '=', 'sent')
        ], limit=1)

        if not request_item_sudo:
            return {'success': False}

        result = {'success': True}
        if request_item_sudo.role_id.auth_method:
            result = self._validate_auth_method(request_item_sudo, sms_token=sms_token)
            if not result.get('success'):
                return result

        sign_user = request.env['res.users'].sudo().search([('partner_id', '=', request_item_sudo.partner_id.id)], limit=1)
        if sign_user:
            # sign as a known user
            request_item_sudo = request_item_sudo.with_user(sign_user).sudo()

        request_item_sudo._edit_and_sign(signature, **kwargs)
        return result

    @http.route(['/sign/refuse/<int:sign_request_id>/<token>'], type='json', auth='public')
    def refuse(self, sign_request_id, token, refusal_reason=""):
        request_item = request.env["sign.request.item"].sudo().search(
            [
                ("sign_request_id", "=", sign_request_id),
                ("access_token", "=", token),
                ("state", "=", "sent"),
                ("sign_request_id.refusal_allowed", "=", True),
            ],
            limit=1,
        )
        if not request_item:
            return False

        refuse_user = request.env['res.users'].sudo().search([('partner_id', '=', request_item.partner_id.id)], limit=1)
        if refuse_user:
            # refuse as a known user
            request_item = request_item.with_user(refuse_user).sudo()
        request_item._refuse(refusal_reason)
        return True

    @http.route(['/sign/password/<int:sign_request_id>'], type='json', auth='public')
    def check_password(self, sign_request_id, password=None):
        request_item = http.request.env['sign.request.item'].sudo().search([
            ('sign_request_id', '=', sign_request_id),
            ('state', '=', 'completed')], limit=1)
        if not request_item:
            return False
        template_id = request_item.sign_request_id.template_id

        old_pdf = PdfFileReader(io.BytesIO(base64.b64decode(template_id.attachment_id.datas)), strict=False, overwriteWarnings=False)
        if old_pdf.isEncrypted and not old_pdf.decrypt(password):
            return False

        # if the password is correct, we generate document and send it
        request_item.sign_request_id._generate_completed_document(password)
        request_item.sign_request_id._send_completed_document()
        return True

    @http.route(['/sign/encrypted/<int:sign_request_id>'], type='json', auth='public')
    def check_encrypted(self, sign_request_id):
        request_item = http.request.env['sign.request.item'].sudo().search([('sign_request_id', '=', sign_request_id)], limit=1)
        if not request_item:
            return False

        # we verify that the document is completed by all signor
        if request_item.sign_request_id.nb_total != request_item.sign_request_id.nb_closed:
            return False
        template_id = request_item.sign_request_id.template_id

        old_pdf = PdfFileReader(io.BytesIO(base64.b64decode(template_id.attachment_id.datas)), strict=False, overwriteWarnings=False)
        return True if old_pdf.isEncrypted else False

    @http.route(['/sign/save_location/<int:id>/<token>'], type='json', auth='public')
    def save_location(self, id, token, latitude=0, longitude=0):
        sign_request_item = http.request.env['sign.request.item'].sudo().search([('sign_request_id', '=', id), ('access_token', '=', token)], limit=1)
        sign_request_item.write({'latitude': latitude, 'longitude': longitude})

    @http.route("/sign/render_assets_pdf_iframe", type="json", auth="public")
    def render_assets_pdf_iframe(self, **kw):
        context = {'debug': kw.get('debug')} if 'debug' in kw else {}
        return request.env['ir.ui.view'].sudo()._render_template('sign.compiled_assets_pdf_iframe', context)

    @http.route(['/sign/has_sms_credits'], type='json', auth='public')
    def has_sms_credits(self):
        return request.env['iap.account'].sudo().get_credits('sms') >= 1

    def has_warning_for_service(self, roles, service_name):
        templates_using_service_roles = request.env['sign.template'].sudo().search([
            ('sign_item_ids.responsible_id', 'in', roles.ids)
        ])
        if templates_using_service_roles:
            requests_in_progress = request.env['sign.request'].sudo().search([
                ('template_id', 'in', templates_using_service_roles.ids),
                ('state', 'in', ['shared', 'sent'])
            ])

            if requests_in_progress and request.env['iap.account'].sudo().get_credits(service_name) < 20:
                return True
        return False

    def get_iap_credit_warnings(self):
        warnings = []
        roles_with_sms = request.env['sign.item.role'].sudo().search([('auth_method', '=', 'sms')])
        if roles_with_sms:
            if self.has_warning_for_service(roles_with_sms, 'sms'):
                warnings.append({
                    'iap_url': request.env['iap.account'].sudo().get_credits_url('sms'),
                    'auth_method': 'SMS'
                })
        return warnings

    @http.route("/sign/check_iap_credits", type="json", auth="user")
    def check_iap_credits(self):
        warnings = self.get_iap_credit_warnings()
        if warnings:
            return {
                'html': request.env['ir.qweb']._render('sign.sign_iap_credits_banner', {
                    'warnings': warnings
                })
            }
        return {}
