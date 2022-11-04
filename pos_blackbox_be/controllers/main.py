# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import pathlib

from markupsafe import Markup

from odoo import http
from odoo.http import request
from odoo.osv.expression import AND

from odoo.addons.point_of_sale.controllers.main import PosController

from odoo.modules import get_module_path

BLACKBOX_MODULES = ['pos_blackbox_be', 'pos_hr_l10n_be']
class GovCertificationController(http.Controller):
    @http.route('/fdm_source', auth='public')
    def handler(self):
        root = pathlib.Path(__file__).parent.parent.parent

        modfiles = [
            p
            for modpath in map(pathlib.Path, map(get_module_path, BLACKBOX_MODULES))
            for p in modpath.glob('**/*')
            if p.is_file()
            if p.suffix not in ('.pot', '.po', '.md', '.sh')
            if '/tests/' not in str(p)
        ]
        modfiles.sort()

        files_data = []
        main_hash = hashlib.sha1()
        for p in modfiles:
            content = p.read_bytes()
            content_hash = hashlib.sha1(content).hexdigest()
            files_data.append({
                'name': p.relative_to(root),
                'size_in_bytes': p.stat().st_size,
                'contents': Markup(content.decode()),
                'hash': content_hash
            })
            main_hash.update(content_hash.encode())

        data = {
            'files': files_data,
            'main_hash': main_hash.hexdigest(),
        }

        return request.render('pos_blackbox_be.fdm_source', data, mimetype='text/plain')

    @http.route("/journal_file/<string:serial>", auth="user")
    def journal_file(self, serial, **kw):
        """ Give the journal file report for a specific blackbox
        serial: e.g. BODO001bd6034a
        """
        logs = request.env["pos_blackbox_be.log"].search([
            ("action", "=", "create"),
            ("model_name", "in", ["pos.order", "pos.order_pro_forma"]),
            ("description", "ilike", serial),
        ], order='id')

        data = {
            'pos_id': serial,
            'logs': logs,
        }

        return request.render("pos_blackbox_be.journal_file", data, mimetype="text/plain")


class BlackboxPOSController(PosController):
    @http.route()
    def pos_web(self, config_id=False, **k):
        response = super(BlackboxPOSController, self).pos_web(**k)

        if response.status_code == 200:
            pos_session = request.env['pos.session']
            domain = [
                    ('state', '=', 'opened'),
                    ('user_id', '=', request.session.uid),
                    ('rescue', '=', False)
                    ]
            if config_id:
                domain = AND([domain, [('config_id', '=', int(config_id))]])
            active_pos_session = pos_session.search(domain, limit=1)
            response.qcontext.update({
                'blackbox': active_pos_session.config_id.blackbox_pos_production_id
            })
        return response
