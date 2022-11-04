# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, SUPERUSER_ID
from . import models
from . import controllers
from . import report

def post_init(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if 'is_fsm' in env['project.project']:
        env['project.project'].search([('is_fsm', '=', True)]).write({'allow_forecast': False})

def _uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    resource_menu = env.ref('planning.planning_menu_schedule_by_resource', raise_if_not_found=False)
    if resource_menu:
        resource_menu.action = env.ref('planning.planning_action_schedule_by_resource')
