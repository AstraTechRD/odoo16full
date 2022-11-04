# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from bisect import bisect_left
from collections import defaultdict
from datetime import datetime
from pytz import utc

from odoo import api, fields, models, _
from odoo.addons.web.controllers.utils import clean_action
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero, relativedelta
from odoo.addons.resource.models.resource import Intervals, sum_intervals, string_to_datetime


class MrpWorkcenter(models.Model):
    _name = 'mrp.workcenter'
    _inherit = 'mrp.workcenter'

    def action_work_order(self):
        if not self.env.context.get('desktop_list_view', False):
            action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.mrp_workorder_action_tablet")
            return action
        else:
            return super(MrpWorkcenter, self).action_work_order()


class MrpProductionWorkcenterLine(models.Model):
    _name = 'mrp.workorder'
    _inherit = ['mrp.workorder', 'barcodes.barcode_events_mixin']

    quality_point_ids = fields.Many2many('quality.point', compute='_compute_quality_point_ids', store=True)
    quality_point_count = fields.Integer('Steps', compute='_compute_quality_point_count')

    check_ids = fields.One2many('quality.check', 'workorder_id')
    finished_product_check_ids = fields.Many2many('quality.check', compute='_compute_finished_product_check_ids')
    quality_check_todo = fields.Boolean(compute='_compute_check')
    quality_check_fail = fields.Boolean(compute='_compute_check')
    quality_alert_ids = fields.One2many('quality.alert', 'workorder_id')
    quality_alert_count = fields.Integer(compute="_compute_quality_alert_count")

    current_quality_check_id = fields.Many2one(
        'quality.check', "Current Quality Check", check_company=True)

    # QC-related fields
    allow_producing_quantity_change = fields.Boolean('Allow Changes to Producing Quantity', default=True)

    is_last_lot = fields.Boolean('Is Last lot', compute='_compute_is_last_lot')
    is_first_started_wo = fields.Boolean('Is The first Work Order', compute='_compute_is_last_unfinished_wo')
    is_last_unfinished_wo = fields.Boolean('Is Last Work Order To Process', compute='_compute_is_last_unfinished_wo', store=False)
    lot_id = fields.Many2one(related='current_quality_check_id.lot_id', readonly=False)
    move_id = fields.Many2one(related='current_quality_check_id.move_id', readonly=False)
    move_line_id = fields.Many2one(related='current_quality_check_id.move_line_id', readonly=False)
    move_line_ids = fields.One2many(related='move_id.move_line_ids')
    quality_state = fields.Selection(related='current_quality_check_id.quality_state', string="Quality State", readonly=False)
    qty_done = fields.Float(related='current_quality_check_id.qty_done', readonly=False)
    test_type_id = fields.Many2one('quality.point.test_type', 'Test Type', related='current_quality_check_id.test_type_id')
    test_type = fields.Char(related='test_type_id.technical_name')
    user_id = fields.Many2one(related='current_quality_check_id.user_id', readonly=False)
    worksheet_page = fields.Integer('Worksheet page')
    picture = fields.Binary(related='current_quality_check_id.picture', readonly=False)
    additional = fields.Boolean(related='current_quality_check_id.additional')

    @api.depends('operation_id')
    def _compute_quality_point_ids(self):
        for workorder in self:
            quality_points = workorder.operation_id.quality_point_ids
            quality_points = quality_points.filtered(lambda qp: not qp.product_ids or workorder.production_id.product_id in qp.product_ids)
            workorder.quality_point_ids = quality_points

    @api.depends('operation_id')
    def _compute_quality_point_count(self):
        for workorder in self:
            quality_point = workorder.operation_id.quality_point_ids
            workorder.quality_point_count = len(quality_point)

    @api.depends('qty_producing', 'qty_remaining')
    def _compute_is_last_lot(self):
        for wo in self:
            precision = wo.production_id.product_uom_id.rounding
            wo.is_last_lot = float_compare(wo.qty_producing, wo.qty_remaining, precision_rounding=precision) >= 0

    @api.depends('production_id.workorder_ids')
    def _compute_is_last_unfinished_wo(self):
        for wo in self:
            wo.is_first_started_wo = all(wo.state != 'done' for wo in (wo.production_id.workorder_ids - wo))
            other_wos = wo.production_id.workorder_ids - wo
            other_states = other_wos.mapped(lambda w: w.state == 'done')
            wo.is_last_unfinished_wo = all(other_states)

    @api.depends('check_ids')
    def _compute_finished_product_check_ids(self):
        for wo in self:
            wo.finished_product_check_ids = wo.check_ids.filtered(lambda c: c.finished_product_sequence == wo.qty_produced)

    def write(self, values):
        res = super().write(values)
        if 'qty_producing' in values:
            for wo in self:
                if wo.current_quality_check_id.component_id:
                    wo.current_quality_check_id._update_component_quantity()
        return res

    def action_back(self):
        self.ensure_one()
        if self.is_user_working and self.working_state != 'blocked':
            self.button_pending()
        domain = [('state', 'not in', ['done', 'cancel', 'pending'])]
        if self.env.context.get('from_production_order'):
            action = self.env["ir.actions.actions"]._for_xml_id("mrp.action_mrp_workorder_production_specific")
            action['domain'] = domain
            action['target'] = 'main'
            action['view_id'] = 'mrp.mrp_production_workorder_tree_editable_view'
            action['context'] = {
                'no_breadcrumbs': True,
            }
            if self.env.context.get('from_manufacturing_order'):
                action['context'].update({
                    'search_default_production_id': self.production_id.id
                })
        else:
            # workorder tablet view action should redirect to the same tablet view with same workcenter when WO mark as done.
            action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.mrp_workorder_action_tablet")
            action['domain'] = domain
            action['context'] = {
                'no_breadcrumbs': True,
                'search_default_workcenter_id': self.workcenter_id.id
            }

        return clean_action(action, self.env)

    def action_cancel(self):
        self.mapped('check_ids').filtered(lambda c: c.quality_state == 'none').sudo().unlink()
        return super(MrpProductionWorkcenterLine, self).action_cancel()

    def action_generate_serial(self):
        self.ensure_one()
        self.finished_lot_id = self.env['stock.lot'].create({
            'product_id': self.product_id.id,
            'company_id': self.company_id.id,
            'name': self.env['stock.lot']._get_next_serial(self.company_id, self.product_id) or self.env['ir.sequence'].next_by_code('stock.lot.serial'),
        })

    def _create_subsequent_checks(self):
        """ When processing a step with regiter a consumed material
        that's a lot we will some times need to create a new
        intermediate check.
        e.g.: Register 2 product A tracked by SN. We will register one
        with the current checks but we need to generate a second step
        for the second SN. Same for lot if the user wants to use more
        than one lot.
        """
        # Create another quality check if necessary
        next_check = self.current_quality_check_id.next_check_id
        if next_check.component_id != self.current_quality_check_id.product_id or\
                next_check.point_id != self.current_quality_check_id.point_id:
            # TODO: manage reservation here

            # Creating quality checks
            quality_check_data = {
                'workorder_id': self.id,
                'product_id': self.product_id.id,
                'company_id': self.company_id.id,
                'finished_product_sequence': self.qty_produced,
            }
            if self.current_quality_check_id.point_id:
                quality_check_data.update({
                    'point_id': self.current_quality_check_id.point_id.id,
                    'team_id': self.current_quality_check_id.point_id.team_id.id,
                })
            else:
                quality_check_data.update({
                    'component_id': self.current_quality_check_id.component_id.id,
                    'test_type_id': self.current_quality_check_id.test_type_id.id,
                    'team_id': self.current_quality_check_id.team_id.id,
                })
            move = self.current_quality_check_id.move_id
            quality_check_data.update(self._defaults_from_move(move))
            new_check = self.env['quality.check'].create(quality_check_data)
            new_check._insert_in_chain('after', self.current_quality_check_id)

    def _change_quality_check(self, position):
        """Change the quality check currently set on the workorder `self`.

        The workorder points to a check. A check belongs to a chain.
        This method allows to change the selected check by moving on the checks
        chain according to `position`.

        :param position: Where we need to change the cursor on the check chain
        :type position: string
        """
        self.ensure_one()
        assert position in ['first', 'next', 'previous', 'last']
        checks_to_consider = self.check_ids.filtered(lambda c: c.quality_state == 'none')
        if position == 'first':
            check = checks_to_consider.filtered(lambda check: not check.previous_check_id)
        elif position == 'next':
            check = self.current_quality_check_id.next_check_id
            if not check:
                check = checks_to_consider[:1]
            elif check.quality_state != 'none':
                self.current_quality_check_id = check
                return self._change_quality_check(position='next')
            if check.test_type in ('register_byproducts', 'register_consumed_materials'):
                check._update_component_quantity()
        elif position == 'previous':
            check = self.current_quality_check_id.previous_check_id
        else:
            check = checks_to_consider.filtered(lambda check: not check.next_check_id)
        self.write({
            'allow_producing_quantity_change':
                not check.previous_check_id.filtered(lambda c: c.quality_state != 'fail')
                and all(c.quality_state != 'fail' for c in checks_to_consider)
                and self.is_first_started_wo,
            'current_quality_check_id': check.id,
            'worksheet_page': check.point_id.worksheet_page,
        })

    def action_menu(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.workorder',
            'views': [[self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet_menu').id, 'form']],
            'name': _('Menu'),
            'target': 'new',
            'res_id': self.id,
        }

    def action_add_component(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp_workorder.additional.product',
            'views': [[self.env.ref('mrp_workorder.view_mrp_workorder_additional_product_wizard').id, 'form']],
            'name': _('Add Component'),
            'target': 'new',
            'context': {
                'default_workorder_id': self.id,
                'default_type': 'component',
                'default_company_id': self.company_id.id,
            }
        }

    def action_add_byproduct(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp_workorder.additional.product',
            'views': [[self.env.ref('mrp_workorder.view_mrp_workorder_additional_product_wizard').id, 'form']],
            'name': _('Add By-Product'),
            'target': 'new',
            'context': {
                'default_workorder_id': self.id,
                'default_type': 'byproduct',
            }
        }

    def button_start(self):
        res = super().button_start()
        for check in self.check_ids:
            if check.component_tracking == 'serial' and check.component_id:
                check._update_component_quantity()
        return res

    def action_propose_change(self, change_type, title):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'propose.change',
            'views': [[self.env.ref('mrp_workorder.view_propose_change_wizard').id, 'form']],
            'name': title,
            'target': 'new',
            'context': {
                'default_workorder_id': self.id,
                'default_step_id': self.current_quality_check_id.id,
                'default_change_type': change_type,
            }
        }

    def action_add_step(self):
        self.ensure_one()
        if self.current_quality_check_id:
            team = self.current_quality_check_id.team_id
        else:
            team = self.env['quality.alert.team'].search(['|', ('company_id', '=', self.company_id.id), ('company_id', '=', False)], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'quality.check',
            'views': [[self.env.ref('mrp_workorder.add_quality_check_from_tablet').id, 'form']],
            'name': _('Add a Step'),
            'target': 'new',
            'context': {
                'default_test_type_id': self.env.ref('quality.test_type_instructions').id,
                'default_workorder_id': self.id,
                'default_product_id': self.product_id.id,
                'default_team_id': team.id,
            }
        }

    def _compute_check(self):
        for workorder in self:
            todo = False
            fail = False
            for check in workorder.check_ids:
                if check.quality_state == 'none':
                    todo = True
                elif check.quality_state == 'fail':
                    fail = True
                if fail and todo:
                    break
            workorder.quality_check_fail = fail
            workorder.quality_check_todo = todo

    def _compute_quality_alert_count(self):
        for workorder in self:
            workorder.quality_alert_count = len(workorder.quality_alert_ids)

    def _create_checks(self):
        for wo in self:
            # Track components which have a control point
            processed_move = self.env['stock.move']

            production = wo.production_id

            move_raw_ids = wo.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
            move_finished_ids = wo.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel') and m.product_id != wo.production_id.product_id)
            previous_check = self.env['quality.check']
            for point in wo.quality_point_ids:
                # Check if we need a quality control for this point
                if point.check_execute_now():
                    moves = self.env['stock.move']
                    values = {
                        'production_id': production.id,
                        'workorder_id': wo.id,
                        'point_id': point.id,
                        'team_id': point.team_id.id,
                        'company_id': wo.company_id.id,
                        'product_id': production.product_id.id,
                        # Two steps are from the same production
                        # if and only if the produced quantities at the time they were created are equal.
                        'finished_product_sequence': wo.qty_produced,
                        'previous_check_id': previous_check.id,
                        'worksheet_document': point.worksheet_document,
                    }
                    if point.test_type == 'register_byproducts':
                        moves = move_finished_ids.filtered(lambda m: m.product_id == point.component_id)
                        if not moves:
                            moves = production.move_finished_ids.filtered(lambda m: not m.operation_id and m.product_id == point.component_id)
                    elif point.test_type == 'register_consumed_materials':
                        moves = move_raw_ids.filtered(lambda m: m.product_id == point.component_id)
                        if not moves:
                            moves = production.move_raw_ids.filtered(lambda m: not m.operation_id and m.product_id == point.component_id)
                    else:
                        check = self.env['quality.check'].create(values)
                        previous_check.next_check_id = check
                        previous_check = check
                    # Create 'register ...' checks
                    for move in moves:
                        check_vals = values.copy()
                        check_vals.update(wo._defaults_from_move(move))
                        # Create quality check and link it to the chain
                        check_vals.update({'previous_check_id': previous_check.id})
                        check = self.env['quality.check'].create(check_vals)
                        previous_check.next_check_id = check
                        previous_check = check
                    processed_move |= moves

            # Generate quality checks associated with unreferenced components
            moves_without_check = ((move_raw_ids | move_finished_ids) - processed_move).filtered(lambda move: (move.has_tracking != 'none' and not move.raw_material_production_id.use_auto_consume_components_lots) or move.operation_id)
            quality_team_id = self.env['quality.alert.team'].search(['|', ('company_id', '=', wo.company_id.id), ('company_id', '=', False)], limit=1).id
            for move in moves_without_check:
                values = {
                    'production_id': production.id,
                    'workorder_id': wo.id,
                    'product_id': production.product_id.id,
                    'company_id': wo.company_id.id,
                    'component_id': move.product_id.id,
                    'team_id': quality_team_id,
                    # Two steps are from the same production
                    # if and only if the produced quantities at the time they were created are equal.
                    'finished_product_sequence': wo.qty_produced,
                    'previous_check_id': previous_check.id,
                }
                if move in move_raw_ids:
                    test_type = self.env.ref('mrp_workorder.test_type_register_consumed_materials')
                if move in move_finished_ids:
                    test_type = self.env.ref('mrp_workorder.test_type_register_byproducts')
                values.update({'test_type_id': test_type.id})
                values.update(wo._defaults_from_move(move))
                check = self.env['quality.check'].create(values)
                previous_check.next_check_id = check
                previous_check = check

            # Set default quality_check
            wo._change_quality_check(position='first')

    def _get_byproduct_move_to_update(self):
        moves = super(MrpProductionWorkcenterLine, self)._get_byproduct_move_to_update()
        return moves.filtered(lambda m: m.product_id.tracking == 'none')

    def record_production(self):
        if not self:
            return True

        self.ensure_one()
        self._check_sn_uniqueness()
        self._check_company()
        if any(x.quality_state == 'none' for x in self.check_ids if x.test_type != 'instructions'):
            raise UserError(_('You still need to do the quality checks!'))
        if float_compare(self.qty_producing, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))

        if self.production_id.product_id.tracking != 'none' and not self.finished_lot_id and self.move_raw_ids:
            raise UserError(_('You should provide a lot/serial number for the final product'))

        backorder = False
        # Trigger the backorder process if we produce less than expected
        if float_compare(self.qty_producing, self.qty_remaining, precision_rounding=self.product_uom_id.rounding) == -1 and self.is_first_started_wo:
            backorder = self.production_id._split_productions()[1:]
            for workorder in backorder.workorder_ids:
                if workorder.product_tracking == 'serial':
                    workorder.qty_producing = 1
                else:
                    workorder.qty_producing = workorder.qty_remaining
            self.production_id.product_qty = self.qty_producing
        else:
            if self.operation_id:
                backorder = (self.production_id.procurement_group_id.mrp_production_ids - self.production_id).filtered(
                    lambda p: p.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_id).state not in ('cancel', 'done')
                )[:1]
            else:
                index = list(self.production_id.workorder_ids).index(self)
                backorder = (self.production_id.procurement_group_id.mrp_production_ids - self.production_id).filtered(
                    lambda p: index < len(p.workorder_ids) and p.workorder_ids[index].state not in ('cancel', 'done')
                )[:1]

        self.button_finish()

        if backorder:
            for wo in (self.production_id | backorder).workorder_ids:
                if wo.state in ('done', 'cancel'):
                    continue
                wo.current_quality_check_id.update(wo._defaults_from_move(wo.move_id))
                if wo.move_id:
                    wo.current_quality_check_id._update_component_quantity()
            if not self.env.context.get('no_start_next'):
                if self.operation_id:
                    return backorder.workorder_ids.filtered(lambda wo: wo.operation_id == self.operation_id).open_tablet_view()
                else:
                    index = list(self.production_id.workorder_ids).index(self)
                    return backorder.workorder_ids[index].open_tablet_view()
        return True

    def _defaults_from_move(self, move):
        self.ensure_one()
        vals = {'move_id': move.id}
        move_line_id = move.move_line_ids.filtered(lambda sml: sml._without_quality_checks())[:1]
        if move_line_id:
            vals.update({
                'move_line_id': move_line_id.id,
                'lot_id': move_line_id.lot_id.id,
                'qty_done': move_line_id.reserved_uom_qty or 1.0
            })
        return vals

    # --------------------------
    # Buttons from quality.check
    # --------------------------

    def open_tablet_view(self):
        self.ensure_one()
        if not self.is_user_working and self.working_state != 'blocked' and self.state in ('ready', 'waiting', 'progress', 'pending'):
            self.button_start()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_workorder.tablet_client_action")
        action['target'] = 'fullscreen'
        action['res_id'] = self.id
        action['context'] = {
            'active_id': self.id,
            'from_production_order': self.env.context.get('from_production_order'),
            'from_manufacturing_order': self.env.context.get('from_manufacturing_order')
        }
        return action

    def action_open_manufacturing_order(self):
        action = self.with_context(no_start_next=True).do_finish()
        try:
            with self.env.cr.savepoint():
                res = self.production_id.button_mark_done()
                if res is not True:
                    res['context'] = dict(res['context'], from_workorder=True)
                    return res
        except (UserError, ValidationError) as e:
            # log next activity on MO with error message
            self.production_id.activity_schedule(
                'mail.mail_activity_data_warning',
                note=e.name,
                summary=('The %s could not be closed') % (self.production_id.name),
                user_id=self.env.user.id)
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                'res_id': self.production_id.id,
                'target': 'main',
            }
        return action

    def do_finish(self):
        action = True
        if self.state != 'done':
            action = self.record_production()
        if action is not True:
            return action
        # workorder tree view action should redirect to the same view instead of workorder kanban view when WO mark as done.
        return self.action_back()

    def get_workorder_data(self):
        # order quality check chain
        ele = self.check_ids.filtered(lambda check: not check.previous_check_id)
        sorted_check_list = []
        while ele:
            sorted_check_list += ele.ids
            ele = ele.next_check_id
        data = {
            'mrp.workorder': self.read(self._get_fields_for_tablet(), load=False)[0],
            'quality.check': self.check_ids._get_fields_for_tablet(sorted_check_list),
            'operation': self.operation_id.read(self.operation_id._get_fields_for_tablet())[0] if self.operation_id else {},
            'working_state': self.workcenter_id.working_state,
            'views': {
                'workorder': self.env.ref('mrp_workorder.mrp_workorder_view_form_tablet').id,
                'check': self.env.ref('mrp_workorder.quality_check_view_form_tablet').id,
            },
        }
        return data

    def get_summary_data(self):
        self.ensure_one()
        # show rainbow man only the first time
        show_rainbow = any(not t.date_end for t in self.time_ids)
        self.end_all()
        if any(step.quality_state == 'none' for step in self.check_ids):
            raise UserError(_('You still need to do the quality checks!'))
        last30op = self.env['mrp.workorder'].search_read([
            ('operation_id', '=', self.operation_id.id),
            ('date_finished', '>', fields.datetime.today() - relativedelta(days=30)),
        ], ['duration'], order='duration')
        last30op = [item['duration'] for item in last30op]

        passed_checks = len(list(check.quality_state == 'pass' for check in self.check_ids))
        if passed_checks:
            score = int(3.0 * len(self.check_ids) / passed_checks)
        elif not self.check_ids:
            score = 3
        else:
            score = 0

        return {
            'duration': self.duration,
            'position': bisect_left(last30op, self.duration), # which position regarded other workorders ranked by duration
            'quality_score': score,
            'show_rainbow': show_rainbow,
        }

    def _action_confirm(self):
        res = super()._action_confirm()
        self.filtered(lambda wo: not wo.check_ids)._create_checks()
        return res

    def _update_qty_producing(self, quantity):
        if float_is_zero(quantity, precision_rounding=self.product_uom_id.rounding):
            self.check_ids.unlink()
        super()._update_qty_producing(quantity)

    def _web_gantt_progress_bar_workcenter_id(self, res_ids, start, stop):
        self.env['mrp.workorder'].check_access_rights('read')
        workcenters = self.env['mrp.workcenter'].search([('id', 'in', res_ids)])
        workorders = self.env['mrp.workorder'].search([
            ('workcenter_id', 'in', res_ids),
            ('state', 'not in', ['done', 'cancel']),
            ('date_planned_start', '<=', stop.replace(tzinfo=None)),
            ('date_planned_finished', '>=', start.replace(tzinfo=None)),
        ])
        planned_hours = defaultdict(float)
        workcenters_work_intervals, dummy = workcenters.resource_id._get_valid_work_intervals(start, stop)
        for workorder in workorders:
            max_start = max(start, utc.localize(workorder.date_planned_start))
            min_end = min(stop, utc.localize(workorder.date_planned_finished))
            interval = Intervals([(max_start, min_end, self.env['resource.calendar.attendance'])])
            work_intervals = interval & workcenters_work_intervals[workorder.workcenter_id.resource_id.id]
            planned_hours[workorder.workcenter_id] += sum_intervals(work_intervals)
        work_hours = {
            id: sum_intervals(work_intervals) for id, work_intervals in workcenters_work_intervals.items()
        }
        return {
            workcenter.id: {
                'value': planned_hours[workcenter],
                'max_value': work_hours.get(workcenter.resource_id.id, 0.0),
            }
            for workcenter in workcenters
        }

    def _web_gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'workcenter_id':
            return dict(
                self._web_gantt_progress_bar_workcenter_id(res_ids, start, stop),
                warning=_("This workcenter isn't expected to have open workorders during this period. Work hours :"),
            )
        raise NotImplementedError("This Progress Bar is not implemented.")

    @api.model
    def gantt_progress_bar(self, fields, res_ids, date_start_str, date_stop_str):
        start_utc, stop_utc = string_to_datetime(date_start_str), string_to_datetime(date_stop_str)
        today = datetime.now(utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_utc = max(start_utc, today)
        progress_bars = {}
        for field in fields:
            progress_bars[field] = self._web_gantt_progress_bar(field, res_ids[field], start_utc, stop_utc)
        return progress_bars

    def _get_fields_for_tablet(self):
        """ List of fields on the workorder object that are needed by the tablet
        client action. The purpose of this function is to be overridden in order
        to inject new fields to the client action.
        """
        return [
            'production_id',
            'name',
            'qty_producing',
            'state',
            'company_id',
            'workcenter_id',
            'current_quality_check_id',
            'operation_note',
        ]
