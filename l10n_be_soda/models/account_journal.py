# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError
from lxml import etree
import io


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def create_document_from_attachment(self, attachment_ids=None):
        # OVERRIDE
        journal = self or self.browse(self.env.context.get('default_journal_id'))
        if journal.type == 'general':
            attachments = self.env['ir.attachment'].browse(attachment_ids or [])
            if not attachments:
                raise UserError(_("No attachment was provided"))
            if all(journal._l10n_be_check_soda_format(attachment) for attachment in attachments):
                return journal._l10n_be_parse_soda_file(attachments)
        return super().create_document_from_attachment(attachment_ids)

    def _l10n_be_check_soda_format(self, attachment):
        try:
            return attachment.mimetype in ('application/xml', 'text/xml') and \
                   etree.parse(io.BytesIO(attachment.raw)).getroot().tag == 'SocialDocument'
        except etree.XMLSyntaxError:
            return False

    def _l10n_be_parse_soda_file(self, attachments):
        self.ensure_one()
        moves = self.env['account.move']
        for attachment in attachments:
            parsed_attachment = etree.parse(io.BytesIO(attachment.raw))
            # The document VAT number must match the journal's company's VAT number
            journal_company_vat = self.company_id.vat or self.browse(self.env.context.get('default_journal_id')).company_id.vat
            if parsed_attachment.find('.//EntNum').text != journal_company_vat:
                if len(attachments) == 1:
                    message = _('The SODA Entry could not be created: \n'
                                'The company VAT number found in the document doesn\'t match the one from the company\'s journal.')
                else:
                    message = _('The SODA Entry could not be created: \n'
                                'The company VAT number found in at least one document doesn\'t match the one from the company\'s journal.')
                raise UserError(message)
            # account.move.ref is SocialNumber+SequenceNumber : check that this move has not already been imported
            ref = "%s-%s" % (parsed_attachment.find('.//Source').text, parsed_attachment.find('.//SeqNumber').text)
            existing_move = self.env['account.move'].search([('ref', '=', ref)])
            if existing_move.id:
                raise UserError(_('The entry %s has already been uploaded (%s).', ref, existing_move.name))
            # Retrieve aml's infos
            lines_content = []
            for index, elem in enumerate(parsed_attachment.findall('.//%s' % 'Label')):
                lines_content.append({})
                lines_content[index]['Label'] = elem.text
            for info in ['Debit', 'Credit']:
                for index, elem in enumerate(parsed_attachment.findall('.//%s' % info)):
                    lines_content[index][info] = float(elem.text)
            # Retrieve the account, create it if need be
            for index, account_code in enumerate(parsed_attachment.findall('.//Account')):
                journal_company_id = self.browse(self.env.context.get('default_journal_id')).company_id.id
                account = self.env['account.account'].search([('code', '=', account_code.text), ('company_id', '=', journal_company_id)], limit=1)
                if not account:
                    account = self.env['account.account'].create({
                        'code': account_code.text,
                        'name': '',
                        'company_id': self.company_id.id or self.browse(self.env.context.get('default_journal_id')).company_id.id,
                    })
                lines_content[index]['Account'] = account
            # create the move
            move_vals = {
                'move_type': 'entry',
                'journal_id': self.id or self.browse(self.env.context.get('default_journal_id')).id,
                'ref': ref,
                'line_ids': [(0, 0, {
                    'name': line['Label'],
                    'account_id': line['Account'].id,
                    'debit': line['Debit'],
                    'credit': line['Credit'],
                }) for line in lines_content]
            }
            move = self.env['account.move'].create(move_vals)
            move.message_post(attachment_ids=[attachment.id])
            moves += move

        action_vals = {
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'context': self._context,
        }
        if len(moves) == 1:
            action_vals.update({
                'domain': [('id', '=', moves[0].ids)],
                'views': [[False, "form"]],
                'view_mode': 'form',
                'res_id': moves[0].id,
            })
        else:
            action_vals.update({
                'domain': [('id', 'in', moves.ids)],
                'views': [[False, "list"], [False, "kanban"], [False, "form"]],
                'view_mode': 'list, kanban, form',
            })
        return action_vals
