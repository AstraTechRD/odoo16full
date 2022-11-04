# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from datetime import timedelta, datetime
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.addons.resource.models.resource import Intervals


class MrpWorkcenter(models.Model):
    _inherit = "mrp.workcenter"

    equipment_ids = fields.One2many(
        'maintenance.equipment', 'workcenter_id', string="Maintenance Equipment",
        check_company=True)

    def _get_unavailability_intervals(self, start_datetime, end_datetime):
        res = super(MrpWorkcenter, self)._get_unavailability_intervals(start_datetime, end_datetime)
        if not self:
            return res
        sql = """
        SELECT workcenter_id, ARRAY_AGG((schedule_date || '|' || schedule_date + INTERVAL '1h' * duration)) as date_intervals
        FROM maintenance_request
        LEFT JOIN maintenance_equipment
        ON maintenance_request.equipment_id = maintenance_equipment.id
            WHERE
            schedule_date IS NOT NULL
            AND duration IS NOT NULL
            AND equipment_id IS NOT NULL
            AND maintenance_equipment.workcenter_id IS NOT NULL
            AND maintenance_equipment.workcenter_id IN %s
            AND (schedule_date, schedule_date + INTERVAL '1h' * duration) OVERLAPS (%s, %s)
        GROUP BY maintenance_equipment.workcenter_id;
        """
        self.env.cr.execute(sql, [tuple(self.ids), fields.Datetime.to_string(start_datetime.astimezone()), fields.Datetime.to_string(end_datetime.astimezone())])
        res_maintenance = defaultdict(list)
        for wc_row in self.env.cr.dictfetchall():
            res_maintenance[wc_row.get('workcenter_id')] = [
                [fields.Datetime.to_datetime(i) for i in intervals.split('|')]
                for intervals in wc_row.get('date_intervals')
            ]

        for wc_id in self.ids:
            intervals_previous_list = [(s.timestamp(), e.timestamp(), self.env['maintenance.request']) for s, e in res[wc_id]]
            intervals_maintenances_list = [(m[0].timestamp(), m[1].timestamp(), self.env['maintenance.request']) for m in res_maintenance[wc_id]]
            final_intervals_wc = Intervals(intervals_previous_list + intervals_maintenances_list)
            res[wc_id] = [(datetime.fromtimestamp(s), datetime.fromtimestamp(e)) for s, e, _ in final_intervals_wc]
        return res


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"
    _check_company_auto = True

    expected_mtbf = fields.Integer(string='Expected MTBF', help='Expected Mean Time Between Failure')
    mtbf = fields.Integer(compute='_compute_maintenance_request', string='MTBF', help='Mean Time Between Failure, computed based on done corrective maintenances.')
    mttr = fields.Integer(compute='_compute_maintenance_request', string='MTTR', help='Mean Time To Repair')
    estimated_next_failure = fields.Date(compute='_compute_maintenance_request', string='Estimated time before next failure (in days)', help='Computed as Latest Failure Date + MTBF')
    latest_failure_date = fields.Date(compute='_compute_maintenance_request', string='Latest Failure Date')
    workcenter_id = fields.Many2one(
        'mrp.workcenter', string='Work Center', check_company=True)

    @api.depends('effective_date', 'maintenance_ids.stage_id', 'maintenance_ids.close_date', 'maintenance_ids.request_date')
    def _compute_maintenance_request(self):
        for equipment in self:
            maintenance_requests = equipment.maintenance_ids.filtered(lambda x: x.maintenance_type == 'corrective' and x.stage_id.done)
            mttr_days = 0
            for maintenance in maintenance_requests:
                if maintenance.stage_id.done and maintenance.close_date:
                    mttr_days += (maintenance.close_date - maintenance.request_date).days
            equipment.mttr = len(maintenance_requests) and (mttr_days / len(maintenance_requests)) or 0
            maintenance = maintenance_requests.sorted(lambda x: x.request_date)
            if len(maintenance) >= 1:
                equipment.mtbf = (maintenance[-1].request_date - equipment.effective_date).days / len(maintenance)
            equipment.latest_failure_date = maintenance and maintenance[-1].request_date or False
            if equipment.mtbf:
                equipment.estimated_next_failure = equipment.latest_failure_date + relativedelta(days=equipment.mtbf)
            else:
                equipment.estimated_next_failure = False

    def button_mrp_workcenter(self):
        self.ensure_one()
        return {
            'name': _('work centers'),
            'view_mode': 'form',
            'res_model': 'mrp.workcenter',
            'view_id': self.env.ref('mrp.mrp_workcenter_view').id,
            'type': 'ir.actions.act_window',
            'res_id': self.workcenter_id.id,
            'context': {
                'default_company_id': self.company_id.id
            }
        }


class MaintenanceRequest(models.Model):
    _inherit = "maintenance.request"
    _check_company_auto = True

    production_id = fields.Many2one(
        'mrp.production', string='Manufacturing Order', check_company=True)
    workorder_id = fields.Many2one(
        'mrp.workorder', string='Work Order', check_company=True)
    production_company_id = fields.Many2one(string='Production Company', related='production_id.company_id')
    company_id = fields.Many2one(domain="[('id', '=?', production_company_id)]")


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    maintenance_count = fields.Integer(compute='_compute_maintenance_count', string="Number of maintenance requests")
    request_ids = fields.One2many('maintenance.request', 'production_id')

    @api.depends('request_ids')
    def _compute_maintenance_count(self):
        for production in self:
            production.maintenance_count = len(production.request_ids)

    def button_maintenance_req(self):
        self.ensure_one()
        return {
            'name': _('New Maintenance Request'),
            'view_mode': 'form',
            'res_model': 'maintenance.request',
            'type': 'ir.actions.act_window',
            'context': {
                'default_company_id': self.company_id.id,
                'default_production_id': self.id,
            },
            'domain': [('production_id', '=', self.id)],
        }

    def open_maintenance_request_mo(self):
        self.ensure_one()
        action = {
            'name': _('Maintenance Requests'),
            'view_mode': 'kanban,tree,form,pivot,graph,calendar',
            'res_model': 'maintenance.request',
            'type': 'ir.actions.act_window',
            'context': {
                'default_company_id': self.company_id.id,
                'default_production_id': self.id,
            },
            'domain': [('production_id', '=', self.id)],
        }
        if self.maintenance_count == 1:
            production = self.env['maintenance.request'].search([('production_id', '=', self.id)])
            action['view_mode'] = 'form'
            action['res_id'] = production.id
        return action


class MrpProductionWorkcenterLine(models.Model):
    _inherit = "mrp.workorder"

    def button_maintenance_req(self):
        self.ensure_one()
        return {
            'name': _('New Maintenance Request'),
            'view_mode': 'form',
            'views': [(self.env.ref('mrp_maintenance.maintenance_request_view_form_inherit_mrp').id, 'form')],
            'res_model': 'maintenance.request',
            'type': 'ir.actions.act_window',
            'context': {
                'default_company_id': self.company_id.id,
                'default_workorder_id': self.id,
                'default_production_id': self.production_id.id,
                'discard_on_footer_button': True,
            },
            'target': 'new',
            'domain': [('workorder_id', '=', self.id)]
        }
