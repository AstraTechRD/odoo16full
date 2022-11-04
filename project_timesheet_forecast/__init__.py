# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, SUPERUSER_ID
from . import models
from . import report

def _uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    role_menu = env.ref('planning.planning_menu_schedule_by_role', raise_if_not_found=False)
    if role_menu:
        role_menu.action = env.ref('planning.planning_action_schedule_by_role')
