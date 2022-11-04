# -*- coding: utf-8 -*-

from . import controllers
from . import models

from odoo import api, SUPERUSER_ID

def _documents_project_post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['project.project'].search([('use_documents', '=', True)])._create_missing_folders()
