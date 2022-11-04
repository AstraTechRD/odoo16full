# -*- coding: utf-8 -*-

import base64
import zipfile
import io
import json
import logging
import os
from contextlib import ExitStack

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request, content_disposition
from odoo.tools.translate import _
from odoo.tools import image_process

from werkzeug.exceptions import Forbidden

logger = logging.getLogger(__name__)


class ShareRoute(http.Controller):

    # util methods #################################################################################

    def _get_file_response(self, res_id, share_id=None, share_token=None, field='raw'):
        """ returns the http response to download one file. """
        record = request.env['documents.document'].browse(int(res_id))

        if share_id:
            share = request.env['documents.share'].sudo().browse(int(share_id))
            record = share._get_documents_and_check_access(share_token, [int(res_id)], operation='read')
        if not record or not record.exists():
            raise request.not_found()

        return request.env['ir.binary']._get_stream_from(record, field).get_response()

    def _get_downloadable_documents(self, documents):
        """ to override to filter out documents that cannot be downloaded """
        return documents

    def _make_zip(self, name, documents):
        """returns zip files for the Document Inspector and the portal.

        :param name: the name to give to the zip file.
        :param documents: files (documents.document) to be zipped.
        :return: a http response to download a zip file.
        """
        # TODO: zip on-the-fly while streaming instead of loading the
        #       entire zip in memory and sending it all at once.

        stream = io.BytesIO()
        try:
            with zipfile.ZipFile(stream, 'w') as doc_zip:
                for document in self._get_downloadable_documents(documents):
                    if document.type != 'binary':
                        continue
                    binary_stream = request.env['ir.binary']._get_stream_from(document, 'raw')
                    doc_zip.writestr(
                        binary_stream.download_name,
                        binary_stream.read(),  # Cf Todo: this is bad
                        compress_type=zipfile.ZIP_DEFLATED
                    )
        except zipfile.BadZipfile:
            logger.exception("BadZipfile exception")

        content = stream.getvalue()  # Cf Todo: this is bad
        headers = [
            ('Content-Type', 'zip'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Length', len(content)),
            ('Content-Disposition', content_disposition(name))
        ]
        return request.make_response(content, headers)

    # Download & upload routes #####################################################################

    @http.route('/documents/upload_attachment', type='http', methods=['POST'], auth="user")
    def upload_document(self, folder_id, ufile, tag_ids, document_id=False, partner_id=False, owner_id=False, res_id=False, res_model=False):
        files = request.httprequest.files.getlist('ufile')
        result = {'success': _("All files uploaded")}
        tag_ids = tag_ids.split(',') if tag_ids else []
        if document_id:
            document = request.env['documents.document'].browse(int(document_id))
            ufile = files[0]
            try:
                data = base64.encodebytes(ufile.read())
                mimetype = ufile.content_type
                document.write({
                    'name': ufile.filename,
                    'datas': data,
                    'mimetype': mimetype,
                })
            except Exception as e:
                logger.exception("Fail to upload document %s" % ufile.filename)
                result = {'error': str(e)}
        else:
            vals_list = []
            for ufile in files:
                try:
                    mimetype = ufile.content_type
                    datas = base64.encodebytes(ufile.read())
                    vals = {
                        'name': ufile.filename,
                        'mimetype': mimetype,
                        'datas': datas,
                        'folder_id': int(folder_id),
                        'tag_ids': tag_ids,
                        'partner_id': int(partner_id)
                    }
                    if owner_id:
                        vals['owner_id'] = int(owner_id)
                    if res_id and res_model:
                        vals['res_id'] = res_id
                        vals['res_model'] = res_model
                    vals_list.append(vals)
                except Exception as e:
                    logger.exception("Fail to upload document %s" % ufile.filename)
                    result = {'error': str(e)}
            cids = request.httprequest.cookies.get('cids', str(request.env.user.company_id.id))
            allowed_company_ids = [int(cid) for cid in cids.split(',')]
            documents = request.env['documents.document'].with_context(allowed_company_ids=allowed_company_ids).create(vals_list)
            result['ids'] = documents.ids

        return json.dumps(result)

    @http.route('/documents/pdf_split', type='http', methods=['POST'], auth="user")
    def pdf_split(self, new_files=None, ufile=None, archive=False, vals=None):
        """Used to split and/or merge pdf documents.

        The data can come from different sources: multiple existing documents
        (at least one must be provided) and any number of extra uploaded files.

        :param new_files: the array that represents the new pdf structure:
            [{
                'name': 'New File Name',
                'new_pages': [{
                    'old_file_type': 'document' or 'file',
                    'old_file_index': document_id or index in ufile,
                    'old_page_number': 5,
                }],
            }]
        :param ufile: extra uploaded files that are not existing documents
        :param archive: whether to archive the original documents
        :param vals: values for the create of the new documents.
        """
        vals = json.loads(vals)
        new_files = json.loads(new_files)
        # find original documents
        document_ids = set()
        for new_file in new_files:
            for page in new_file['new_pages']:
                if page['old_file_type'] == 'document':
                    document_ids.add(page['old_file_index'])
        documents = request.env['documents.document'].browse(document_ids)

        with ExitStack() as stack:
            files = request.httprequest.files.getlist('ufile')
            open_files = [stack.enter_context(io.BytesIO(file.read())) for file in files]

            # merge together data from existing documents and from extra uploads
            document_id_index_map = {}
            current_index = len(open_files)
            for document in documents:
                open_files.append(stack.enter_context(io.BytesIO(base64.b64decode(document.datas))))
                document_id_index_map[document.id] = current_index
                current_index += 1

            # update new_files structure with the new indices from documents
            for new_file in new_files:
                for page in new_file['new_pages']:
                    if page.pop('old_file_type') == 'document':
                        page['old_file_index'] = document_id_index_map[page['old_file_index']]

            # apply the split/merge
            new_documents = documents._pdf_split(new_files=new_files, open_files=open_files, vals=vals)

        # archive original documents if needed
        if archive == 'true':
            documents.write({'active': False})

        response = request.make_response(json.dumps(new_documents.ids), [('Content-Type', 'application/json')])
        return response

    @http.route(['/documents/content/<int:id>'], type='http', auth='user')
    def documents_content(self, id):
        return self._get_file_response(id)

    @http.route(['/documents/pdf_content/<int:document_id>'], type='http', auth='user')
    def documents_pdf_content(self, document_id):
        """
        This route is used to fetch the content of a pdf document to make it's thumbnail.
        404 not found is returned if the user does not hadocument_idve the rights to write on the document.
        """
        record = request.env['documents.document'].browse(int(document_id))
        try:
            # We have to check that we can actually read the attachment as well.
            # Since we could have a document with an attachment linked to another record to which
            # we don't have access to.
            if record.attachment_id:
                record.attachment_id.check('read')
            record.check_access_rule('write')
        except AccessError:
            raise Forbidden()
        return self._get_file_response(document_id)

    @http.route(['/documents/image/<int:res_id>',
                 '/documents/image/<int:res_id>/<int:width>x<int:height>',
                 ], type='http', auth="public")
    def content_image(self, res_id=None, field='datas', share_id=None, width=0, height=0, crop=False, share_token=None, **kwargs):
        record = request.env['documents.document'].browse(int(res_id))
        if share_id:
            share = request.env['documents.share'].sudo().browse(int(share_id))
            record = share._get_documents_and_check_access(share_token, [int(res_id)], operation='read')
        if not record or not record.exists():
            raise request.not_found()

        return request.env['ir.binary']._get_image_stream_from(
            record, field, width=int(width), height=int(height), crop=crop
        ).get_response()

    @http.route(['/document/zip'], type='http', auth='user')
    def get_zip(self, file_ids, zip_name, **kw):
        """route to get the zip file of the selection in the document's Kanban view (Document inspector).
        :param file_ids: if of the files to zip.
        :param zip_name: name of the zip file.
        """
        ids_list = [int(x) for x in file_ids.split(',')]
        env = request.env
        response = self._make_zip(zip_name, env['documents.document'].browse(ids_list))
        return response

    @http.route(["/document/download/all/<int:share_id>/<access_token>"], type='http', auth='public')
    def share_download_all(self, access_token=None, share_id=None):
        """
        :param share_id: id of the share, the name of the share will be the name of the zip file share.
        :param access_token: share access token
        :returns the http response for a zip file if the token and the ID are valid.
        """
        env = request.env
        try:
            share = env['documents.share'].sudo().browse(share_id)
            documents = share._get_documents_and_check_access(access_token, operation='read')
            if documents:
                return self._make_zip((share.name or 'unnamed-link') + '.zip', documents)
            else:
                return request.not_found()
        except Exception:
            logger.exception("Failed to zip share link id: %s" % share_id)
        return request.not_found()

    @http.route([
        "/document/avatar/<int:share_id>/<access_token>",
        "/document/avatar/<int:share_id>/<access_token>/<document_id>",
    ], type='http', auth='public')
    def get_avatar(self, access_token=None, share_id=None, document_id=None):
        """
        :param share_id: id of the share.
        :param access_token: share access token
        :returns the picture of the share author for the front-end view.
        """
        try:
            env = request.env
            share = env['documents.share'].sudo().browse(share_id)
            if share._get_documents_and_check_access(access_token, document_ids=[], operation='read') is not False:
                user_id = share.create_uid.id if not document_id else env['documents.document'].sudo().browse(int(document_id)).owner_id.id
                image = env['res.users'].sudo().browse(user_id).avatar_128

                if not image:
                    return env['ir.binary']._image_placeholder()

                return base64.b64decode(image)
            else:
                return request.not_found()
        except Exception:
            logger.exception("Failed to download portrait")
        return request.not_found()

    @http.route(["/document/thumbnail/<int:share_id>/<access_token>/<int:id>"],
                type='http', auth='public')
    def get_thumbnail(self, id=None, access_token=None, share_id=None):
        """
        :param id:  id of the document
        :param access_token: token of the share link
        :param share_id: id of the share link
        :return: the thumbnail of the document for the portal view.
        """
        try:
            thumbnail = self._get_file_response(id, share_id=share_id, share_token=access_token, field='thumbnail')
            return thumbnail
        except Exception:
            logger.exception("Failed to download thumbnail id: %s" % id)
        return request.not_found()

    # single file download route.
    @http.route(["/document/download/<int:share_id>/<access_token>/<int:id>"],
                type='http', auth='public')
    def download_one(self, id=None, access_token=None, share_id=None, **kwargs):
        """
        used to download a single file from the portal multi-file page.

        :param id: id of the file
        :param access_token:  token of the share link
        :param share_id: id of the share link
        :return: a portal page to preview and download a single file.
        """
        try:
            document = self._get_file_response(id, share_id=share_id, share_token=access_token, field='raw')
            return document or request.not_found()
        except Exception:
            logger.exception("Failed to download document %s" % id)

        return request.not_found()

    # Upload file(s) route.
    @http.route(["/document/upload/<int:share_id>/<token>/",
                 "/document/upload/<int:share_id>/<token>/<int:document_id>"],
                type='http', auth='public', methods=['POST'], csrf=False)
    def upload_attachment(self, share_id, token, document_id=None, **kwargs):
        """
        Allows public upload if provided with the right token and share_Link.

        :param share_id: id of the share.
        :param token: share access token.
        :param document_id: id of a document request to directly upload its content
        :return if files are uploaded, recalls the share portal with the updated content.
        """
        share = http.request.env['documents.share'].sudo().browse(share_id)
        if not share.can_upload or (not document_id and share.action != 'downloadupload'):
            return http.request.not_found()

        available_documents = share._get_documents_and_check_access(
            token, [document_id] if document_id else [], operation='write')
        folder = share.folder_id
        folder_id = folder.id or False
        button_text = share.name or _('Share link')
        chatter_message = _('''<b> File uploaded by: </b> %s <br/>
                               <b> Link created by: </b> %s <br/>
                               <a class="btn btn-primary" href="/web#id=%s&model=documents.share&view_type=form" target="_blank">
                                  <b>%s</b>
                               </a>
                             ''') % (
                http.request.env.user.name,
                share.create_uid.name,
                share_id,
                button_text,
            )
        Documents = request.env['documents.document']
        if document_id and available_documents:
            if available_documents.type != 'empty':
                return http.request.not_found()
            try:
                max_upload_size = Documents.get_document_max_upload_limit()
                file = request.httprequest.files.getlist('requestFile')[0]
                data = file.read()
                if max_upload_size and (len(data) > int(max_upload_size)):
                    # TODO return error when converted to json
                    return logger.exception("File is too Large.")
                mimetype = file.content_type
                write_vals = {
                    'mimetype': mimetype,
                    'name': file.filename,
                    'type': 'binary',
                    'datas': base64.b64encode(data),
                }
            except Exception:
                logger.exception("Failed to read uploaded file")
            else:
                available_documents.with_context(binary_field_real_user=http.request.env.user).write(write_vals)
                available_documents.message_post(body=chatter_message)
        elif not document_id and available_documents is not False:
            try:
                max_upload_size = Documents.get_document_max_upload_limit()
                for file in request.httprequest.files.getlist('files'):
                    data = file.read()
                    if max_upload_size and (len(data) > int(max_upload_size)):
                        # TODO return error when converted to json
                        return logger.exception("File is too Large.")
                    mimetype = file.content_type
                    document_dict = {
                        'mimetype': mimetype,
                        'name': file.filename,
                        'datas': base64.b64encode(data),
                        'tag_ids': [(6, 0, share.tag_ids.ids)],
                        'partner_id': share.partner_id.id,
                        'owner_id': share.owner_id.id,
                        'folder_id': folder_id,
                    }
                    document = Documents.with_user(share.create_uid).with_context(binary_field_real_user=http.request.env.user).create(document_dict)
                    document.message_post(body=chatter_message)
                    if share.activity_option:
                        document.documents_set_activity(settings_record=share)

            except Exception:
                logger.exception("Failed to upload document")
        else:
            return http.request.not_found()
        return """<script type='text/javascript'>
                    window.open("/document/share/%s/%s", "_self");
                </script>""" % (share_id, token)

    # Frontend portals #############################################################################

    # share portals route.
    @http.route(['/document/share/<int:share_id>/<token>'], type='http', auth='public')
    def share_portal(self, share_id=None, token=None):
        """
        Leads to a public portal displaying downloadable files for anyone with the token.

        :param share_id: id of the share link
        :param token: share access token
        """
        try:
            share = http.request.env['documents.share'].sudo().browse(share_id)
            available_documents = share._get_documents_and_check_access(token, operation='read')
            if available_documents is False:
                if share._check_token(token):
                    options = {
                        'expiration_date': share.date_deadline,
                        'author': share.create_uid.name,
                    }
                    return request.render('documents.not_available', options)
                else:
                    return request.not_found()

            options = {
                'base_url': share.get_base_url(),
                'token': str(token),
                'upload': share.action == 'downloadupload',
                'share_id': str(share.id),
                'author': share.create_uid.name,
            }
            if share.type == 'ids' and len(available_documents) == 1:
                if self._get_downloadable_documents(available_documents) == available_documents:
                    document = self._get_file_response(available_documents[0].id, share_id=share.id, share_token=str(token), field='raw')
                    return document or request.not_found()
                options.update(document=available_documents[0], request_upload=True)
                return request.render('documents.share_single', options)
            else:
                options.update(all_button='binary' in [document.type for document in available_documents],
                               document_ids=available_documents,
                               request_upload=share.action == 'downloadupload' or share.type == 'ids')
                return request.render('documents.share_page', options)
        except Exception:
            logger.exception("Failed to generate the multi file share portal")
        return request.not_found()
