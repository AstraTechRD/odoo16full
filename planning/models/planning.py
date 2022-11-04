# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import date, datetime, timedelta, time
from dateutil.relativedelta import relativedelta
import logging
import pytz
import uuid
from math import ceil, modf
from random import randint

from odoo import api, fields, models, _
from odoo.addons.resource.models.resource import Intervals, sum_intervals, string_to_datetime
from odoo.addons.resource.models.resource_mixin import timezone_datetime
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_utils, format_datetime

_logger = logging.getLogger(__name__)


def days_span(start_datetime, end_datetime):
    if not isinstance(start_datetime, datetime):
        raise ValueError
    if not isinstance(end_datetime, datetime):
        raise ValueError
    end = datetime.combine(end_datetime, datetime.min.time())
    start = datetime.combine(start_datetime, datetime.min.time())
    duration = end - start
    return duration.days + 1


class Planning(models.Model):
    _name = 'planning.slot'
    _description = 'Planning Shift'
    _order = 'start_datetime desc, id desc'
    _rec_name = 'name'
    _check_company_auto = True

    def _default_start_datetime(self):
        return datetime.combine(fields.Date.context_today(self), time.min)

    def _default_end_datetime(self):
        return datetime.combine(fields.Date.context_today(self), time.max)

    name = fields.Text('Note')
    resource_id = fields.Many2one('resource.resource', 'Resource', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", group_expand='_read_group_resource_id')
    resource_type = fields.Selection(related='resource_id.resource_type')
    employee_id = fields.Many2one('hr.employee', 'Employee', compute='_compute_employee_id', store=True)
    work_email = fields.Char("Work Email", related='employee_id.work_email')
    work_address_id = fields.Many2one(related='employee_id.address_id', store=True)
    work_location_id = fields.Many2one(related='employee_id.work_location_id')
    department_id = fields.Many2one(related='employee_id.department_id', store=True)
    user_id = fields.Many2one('res.users', string="User", related='resource_id.user_id', store=True, readonly=True)
    manager_id = fields.Many2one(related='employee_id.parent_id', store=True)
    job_title = fields.Char(related='employee_id.job_title')
    company_id = fields.Many2one('res.company', string="Company", required=True, compute="_compute_planning_slot_company_id", store=True, readonly=False)
    role_id = fields.Many2one('planning.role', string="Role", compute="_compute_role_id", store=True, readonly=False, copy=True, group_expand='_read_group_role_id',
        help="Define the roles your resources perform (e.g. Chef, Bartender, Waiter...). Create open shifts for the roles you need to complete a mission. Then, assign those open shifts to the resources that are available.")
    color = fields.Integer("Color", compute='_compute_color')
    was_copied = fields.Boolean("This Shift Was Copied From Previous Week", default=False, readonly=True)
    access_token = fields.Char("Security Token", default=lambda self: str(uuid.uuid4()), required=True, copy=False, readonly=True)

    start_datetime = fields.Datetime(
        "Start Date", compute='_compute_datetime', store=True, readonly=False, required=True,
        copy=True)
    end_datetime = fields.Datetime(
        "End Date", compute='_compute_datetime', store=True, readonly=False, required=True,
        copy=True)
    # UI fields and warnings
    allow_self_unassign = fields.Boolean('Let Employee Unassign Themselves', related='company_id.planning_allow_self_unassign')
    self_unassign_days_before = fields.Integer(
        "Days before shift for unassignment",
        related="company_id.planning_self_unassign_days_before"
    )
    unassign_deadline = fields.Datetime('Deadline for unassignment', compute="_compute_unassign_deadline")
    is_unassign_deadline_passed = fields.Boolean('Is unassignement deadline not past', compute="_compute_is_unassign_deadline_passed")
    is_assigned_to_me = fields.Boolean('Is This Shift Assigned To The Current User', compute='_compute_is_assigned_to_me')
    conflicting_slot_ids = fields.Many2many('planning.slot', compute='_compute_overlap_slot_count')
    overlap_slot_count = fields.Integer('Overlapping Slots', compute='_compute_overlap_slot_count', search='_search_overlap_slot_count')
    is_past = fields.Boolean('Is This Shift In The Past?', compute='_compute_past_shift')

    # time allocation
    allocation_type = fields.Selection([
        ('planning', 'Planning'),
        ('forecast', 'Forecast')
    ], compute='_compute_allocation_type')
    allocated_hours = fields.Float("Allocated Time", compute='_compute_allocated_hours', store=True, readonly=False)
    allocated_percentage = fields.Float("Allocated Time %", default=100,
        compute='_compute_allocated_percentage', store=True, readonly=False,
        group_operator="avg")
    working_days_count = fields.Float("Working Days", compute='_compute_working_days_count', store=True)
    duration = fields.Float("Duration", compute="_compute_slot_duration")

    # publication and sending
    publication_warning = fields.Boolean(
        "Modified Since Last Publication", default=False, compute='_compute_publication_warning',
        store=True, readonly=True, copy=False,
        help="If checked, it means that the shift contains has changed since its last publish.")
    state = fields.Selection([
            ('draft', 'Draft'),
            ('published', 'Published'),
    ], string='Status', default='draft')
    # template dummy fields (only for UI purpose)
    template_creation = fields.Boolean("Save as Template", store=False, inverse='_inverse_template_creation')
    template_autocomplete_ids = fields.Many2many('planning.slot.template', store=False, compute='_compute_template_autocomplete_ids')
    template_id = fields.Many2one('planning.slot.template', string='Shift Templates', compute='_compute_template_id', readonly=False, store=True)
    template_reset = fields.Boolean()
    previous_template_id = fields.Many2one('planning.slot.template')
    allow_template_creation = fields.Boolean(string='Allow Template Creation', compute='_compute_allow_template_creation')

    # Recurring (`repeat_` fields are none stored, only used for UI purpose)
    recurrency_id = fields.Many2one('planning.recurrency', readonly=True, index=True, ondelete="set null", copy=False)
    repeat = fields.Boolean("Repeat", compute='_compute_repeat', inverse='_inverse_repeat', copy=True,
        help="Modifications made to a shift only impact the current shift and not the other ones that are part of the recurrence. The same goes when deleting a recurrent shift. Disable this option to stop the recurrence.\n"
        "To avoid polluting your database and performance issues, shifts are only created for the next 6 months. They are then gradually created as time passes by in order to always get shifts 6 months ahead. This value can be modified from the settings of Planning, in debug mode.")
    repeat_interval = fields.Integer("Repeat every", default=1, compute='_compute_repeat_interval', inverse='_inverse_repeat', copy=True)
    repeat_unit = fields.Selection([
        ('day', 'Days'),
        ('week', 'Weeks'),
        ('month', 'Months'),
        ('year', 'Years'),
    ], default='week', compute='_compute_repeat_unit', inverse='_inverse_repeat', required=True)
    repeat_type = fields.Selection([('forever', 'Forever'), ('until', 'Until'), ('x_times', 'Number of Repetitions')],
        string='Repeat Type', default='forever', compute='_compute_repeat_type', inverse='_inverse_repeat', copy=True)
    repeat_until = fields.Date("Repeat Until", compute='_compute_repeat_until', inverse='_inverse_repeat', copy=True)
    repeat_number = fields.Integer("Repetitions", default=1, compute='_compute_repeat_number', inverse='_inverse_repeat', copy=True)
    confirm_delete = fields.Boolean('Confirm Slots Deletion', compute='_compute_confirm_delete')

    is_hatched = fields.Boolean(compute='_compute_is_hatched')

    _sql_constraints = [
        ('check_start_date_lower_end_date', 'CHECK(end_datetime > start_datetime)', 'The end date of a shift should be after its start date.'),
        ('check_allocated_hours_positive', 'CHECK(allocated_hours >= 0)', 'Allocated hours and allocated time percentage cannot be negative.'),
    ]

    @api.depends('role_id.color', 'resource_id.color')
    def _compute_color(self):
        for slot in self:
            slot.color = slot.role_id.color or slot.resource_id.color

    @api.depends('repeat_until', 'repeat_number')
    def _compute_confirm_delete(self):
        for slot in self:
            if slot.recurrency_id and slot.repeat_until and slot.repeat_number:
                recurrence_end_dt = slot.repeat_until or slot.recurrency_id._get_recurrence_last_datetime()
                slot.confirm_delete = fields.Date.to_date(recurrence_end_dt) > slot.repeat_until
            else:
                slot.confirm_delete = False

    @api.constrains('repeat_until')
    def _check_repeat_until(self):
        if any([slot.repeat_until and slot.repeat_until < slot.start_datetime.date() for slot in self]):
            raise UserError(_("The recurrence's end date should fall after the shift's start date."))

    @api.onchange('repeat_until')
    def _onchange_repeat_until(self):
        self._check_repeat_until()

    @api.depends('resource_id.company_id')
    def _compute_planning_slot_company_id(self):
        for slot in self:
            slot.company_id = slot.resource_id.company_id or slot.company_id or slot.env.company

    @api.depends('start_datetime')
    def _compute_past_shift(self):
        now = fields.Datetime.now()
        for slot in self:
            slot.is_past = slot.end_datetime < now if slot.end_datetime else False

    @api.depends('resource_id.employee_id', 'resource_type')
    def _compute_employee_id(self):
        for slot in self:
            slot.employee_id = slot.resource_id.with_context(active_test=False).employee_id if slot.resource_type == 'user' else False

    @api.depends('employee_id', 'template_id')
    def _compute_role_id(self):
        for slot in self:
            if not slot.role_id:
                if slot.employee_id.default_planning_role_id:
                    slot.role_id = slot.employee_id.default_planning_role_id
                else:
                    slot.role_id = False

            if slot.template_id:
                slot.previous_template_id = slot.template_id
                if slot.template_id.role_id:
                    slot.role_id = slot.template_id.role_id
            elif slot.previous_template_id and not slot.template_id and slot.previous_template_id.role_id == slot.role_id:
                slot.role_id = False

    @api.depends('state')
    def _compute_is_hatched(self):
        for slot in self:
            slot.is_hatched = slot.state == 'draft'

    @api.depends('user_id')
    def _compute_is_assigned_to_me(self):
        for slot in self:
            slot.is_assigned_to_me = slot.user_id == self.env.user

    @api.depends('start_datetime', 'end_datetime')
    def _compute_allocation_type(self):
        for slot in self:
            if slot.start_datetime and slot.end_datetime and slot._get_slot_duration() < 24:
                slot.allocation_type = 'planning'
            else:
                slot.allocation_type = 'forecast'

    @api.depends('start_datetime', 'end_datetime', 'employee_id.resource_calendar_id', 'allocated_hours')
    def _compute_allocated_percentage(self):
        # [TW:Cyclic dependency] allocated_hours,allocated_percentage
        # As allocated_hours and allocated percentage have some common dependencies, and are dependant one from another, we have to make sure
        # they are computed in the right order to get rid of undeterministic computation.
        #
        # Allocated percentage must only be recomputed if allocated_hours has been modified by the user and not in any other cases.
        # If allocated hours have to be recomputed, the allocated percentage have to keep its current value.
        # Hence, we stop the computation of allocated percentage if allocated hours have to be recomputed.
        allocated_hours_field = self._fields['allocated_hours']
        slots = self.filtered(lambda slot: not self.env.is_to_compute(allocated_hours_field, slot) and slot.start_datetime and slot.end_datetime and slot.start_datetime != slot.end_datetime)
        if not slots:
            return
        # if there are at least one slot having start or end date, call the _get_valid_work_intervals
        start_utc = pytz.utc.localize(min(slots.mapped('start_datetime')))
        end_utc = pytz.utc.localize(max(slots.mapped('end_datetime')))
        resource_work_intervals, calendar_work_intervals = slots.resource_id \
            .filtered(lambda r: not r.flexible_hours) \
            ._get_valid_work_intervals(start_utc, end_utc, calendars=slots.company_id.resource_calendar_id)
        for slot in slots:
            if not slot.resource_id and slot.allocation_type == 'planning' or slot.resource_id.flexible_hours:
                slot.allocated_percentage = 100 * slot.allocated_hours / slot._calculate_slot_duration()
            else:
                work_hours = slot._get_duration_over_period(
                    pytz.utc.localize(slot.start_datetime),
                    pytz.utc.localize(slot.end_datetime),
                    resource_work_intervals, calendar_work_intervals,
                    has_allocated_hours=False,
                )
                slot.allocated_percentage = 100 * slot.allocated_hours / work_hours if work_hours else 100

    @api.depends(
        'start_datetime', 'end_datetime', 'resource_id.calendar_id',
        'company_id.resource_calendar_id', 'allocated_percentage', 'resource_id.flexible_hours')
    def _compute_allocated_hours(self):
        percentage_field = self._fields['allocated_percentage']
        self.env.remove_to_compute(percentage_field, self)
        planning_slots = self.filtered(
            lambda s:
                (s.allocation_type == 'planning' or not s.company_id)
                and not s.resource_id
                or s.resource_id.flexible_hours
        )
        slots_with_calendar = self - planning_slots
        for slot in planning_slots:
            # for each planning slot, compute the duration
            ratio = slot.allocated_percentage / 100.0 or 1
            slot.allocated_hours = slot._calculate_slot_duration() * ratio
        if slots_with_calendar:
            # for forecasted slots, compute the conjunction of the slot resource's work intervals and the slot.
            unplanned_slots_with_calendar = slots_with_calendar.filtered_domain([
                '|', ('start_datetime', "=", False), ('end_datetime', "=", False),
            ])
            # Unplanned slots will have allocated hours set to 0.0 as there are no enough information
            # to compute the allocated hours (start or end datetime are mandatory for this computation)
            for slot in unplanned_slots_with_calendar:
                slot.allocated_hours = 0.0
            planned_slots_with_calendar = slots_with_calendar - unplanned_slots_with_calendar
            if not planned_slots_with_calendar:
                return
            # if there are at least one slot having start or end date, call the _get_valid_work_intervals
            start_utc = pytz.utc.localize(min(planned_slots_with_calendar.mapped('start_datetime')))
            end_utc = pytz.utc.localize(max(planned_slots_with_calendar.mapped('end_datetime')))
            # work intervals per resource are retrieved with a batch
            resource_work_intervals, calendar_work_intervals = slots_with_calendar.resource_id._get_valid_work_intervals(
                start_utc, end_utc, calendars=slots_with_calendar.company_id.resource_calendar_id
            )
            for slot in planned_slots_with_calendar:
                slot.allocated_hours = slot._get_duration_over_period(
                    pytz.utc.localize(slot.start_datetime), pytz.utc.localize(slot.end_datetime),
                    resource_work_intervals, calendar_work_intervals, has_allocated_hours=False
                )

    @api.depends('start_datetime', 'end_datetime', 'resource_id')
    def _compute_working_days_count(self):
        slots_per_calendar = defaultdict(set)
        planned_dates_per_calendar_id = defaultdict(lambda: (datetime.max, datetime.min))
        for slot in self:
            if not slot.employee_id:
                slot.working_days_count = 0
                continue
            slots_per_calendar[slot.resource_id.calendar_id].add(slot.id)
            datetime_begin, datetime_end = planned_dates_per_calendar_id[slot.resource_id.calendar_id.id]
            datetime_begin = min(datetime_begin, slot.start_datetime)
            datetime_end = max(datetime_end, slot.end_datetime)
            planned_dates_per_calendar_id[slot.resource_id.calendar_id.id] = datetime_begin, datetime_end
        for calendar, slot_ids in slots_per_calendar.items():
            slots = self.env['planning.slot'].browse(list(slot_ids))
            if not calendar:
                slots.working_days_count = 0
                continue
            datetime_begin, datetime_end = planned_dates_per_calendar_id[calendar.id]
            datetime_begin = timezone_datetime(datetime_begin)
            datetime_end = timezone_datetime(datetime_end)
            resources = slots.resource_id
            day_total = calendar._get_resources_day_total(datetime_begin, datetime_end, resources)
            intervals = calendar._work_intervals_batch(datetime_begin, datetime_end, resources)
            for slot in slots:
                slot.working_days_count = calendar._get_days_data(
                    intervals[slot.resource_id.id] & Intervals([(
                        timezone_datetime(slot.start_datetime),
                        timezone_datetime(slot.end_datetime),
                        self.env['resource.calendar.attendance']
                    )]),
                    day_total[slot.resource_id.id]
                )['days']

    @api.depends('start_datetime', 'end_datetime', 'resource_id')
    def _compute_overlap_slot_count(self):
        if self.ids:
            self.flush_model(['start_datetime', 'end_datetime', 'resource_id'])
            query = """
                SELECT S1.id,ARRAY_AGG(DISTINCT S2.id) as conflict_ids FROM
                    planning_slot S1, planning_slot S2
                WHERE
                    S1.start_datetime < S2.end_datetime
                    AND S1.end_datetime > S2.start_datetime
                    AND S1.id <> S2.id AND S1.resource_id = S2.resource_id
                    AND S1.allocated_percentage + S2.allocated_percentage > 100
                    and S1.id in %s
                GROUP BY S1.id;
            """
            self.env.cr.execute(query, (tuple(self.ids),))
            overlap_mapping = dict(self.env.cr.fetchall())
            for slot in self:
                slot_result = overlap_mapping.get(slot.id, [])
                slot.overlap_slot_count = len(slot_result)
                slot.conflicting_slot_ids = [(6, 0, slot_result)]
        else:
            # Allow fetching overlap without id if there is only one record
            # This is to allow displaying the warning when creating a new record without having an ID yet
            if len(self) == 1 and self.employee_id and self.start_datetime and self.end_datetime:
                query = """
                    SELECT ARRAY_AGG(s.id) as conflict_ids
                      FROM planning_slot s
                     WHERE s.employee_id = %s
                       AND s.start_datetime < %s
                       AND s.end_datetime > %s
                       AND s.allocated_percentage + %s > 100
                """
                self.env.cr.execute(query, (self.employee_id.id, self.end_datetime,
                                            self.start_datetime, self.allocated_percentage))
                overlaps = self.env.cr.dictfetchall()
                if overlaps[0]['conflict_ids']:
                    self.overlap_slot_count = len(overlaps[0]['conflict_ids'])
                    self.conflicting_slot_ids = [(6, 0, overlaps[0]['conflict_ids'])]
                else:
                    self.overlap_slot_count = False
            else:
                self.overlap_slot_count = False

    @api.model
    def _search_overlap_slot_count(self, operator, value):
        if operator not in ['=', '>'] or not isinstance(value, int) or value != 0:
            raise NotImplementedError(_('Operation not supported, you should always compare overlap_slot_count to 0 value with = or > operator.'))

        query = """
            SELECT S1.id
            FROM planning_slot S1
            INNER JOIN planning_slot S2 ON S1.resource_id = S2.resource_id AND S1.id <> S2.id
            WHERE
                S1.start_datetime < S2.end_datetime
                AND S1.end_datetime > S2.start_datetime
                AND S1.allocated_percentage + S2.allocated_percentage > 100
        """
        operator_new = (operator == ">") and "inselect" or "not inselect"
        return [('id', operator_new, (query, ()))]

    @api.depends('start_datetime', 'end_datetime')
    def _compute_slot_duration(self):
        for slot in self:
            slot.duration = slot._get_slot_duration()

    def _get_slot_duration(self):
        """Return the slot (effective) duration expressed in hours.
        """
        self.ensure_one()
        if not self.start_datetime:
            return False
        return (self.end_datetime - self.start_datetime).total_seconds() / 3600.0

    def _get_domain_template_slots(self):
        domain = []
        if self.resource_type == 'material':
            domain += [('role_id', '=', False)]
        elif self.role_id:
            domain += ['|', ('role_id', '=', self.role_id.id), ('role_id', '=', False)]
        elif self.employee_id and self.employee_id.sudo().planning_role_ids:
            domain += ['|', ('role_id', 'in', self.employee_id.sudo().planning_role_ids.ids), ('role_id', '=', False)]
        return domain

    @api.depends('role_id', 'employee_id')
    def _compute_template_autocomplete_ids(self):
        domain = self._get_domain_template_slots()
        templates = self.env['planning.slot.template'].search(domain, order='start_time', limit=10)
        self.template_autocomplete_ids = templates + self.template_id

    @api.depends('employee_id', 'role_id', 'start_datetime', 'end_datetime', 'allocated_hours')
    def _compute_template_id(self):
        for slot in self.filtered(lambda s: s.template_id):
            slot.previous_template_id = slot.template_id
            slot.template_reset = False
            if slot._different_than_template():
                slot.template_id = False
                slot.previous_template_id = False
                slot.template_reset = True

    def _different_than_template(self, check_empty=True):
        self.ensure_one()
        if not self.start_datetime:
            return True
        template_fields = self._get_template_fields().items()
        for template_field, slot_field in template_fields:
            if self.template_id[template_field] or not check_empty:
                if template_field == 'start_time':
                    h = int(self.template_id.start_time)
                    m = round(modf(self.template_id.start_time)[0] * 60.0)
                    slot_time = self[slot_field].astimezone(pytz.timezone(self._get_tz()))
                    if slot_time.hour != h or slot_time.minute != m:
                        return True
                else:
                    if self[slot_field] != self.template_id[template_field]:
                        return True
        return False

    @api.depends('template_id', 'role_id', 'allocated_hours', 'start_datetime', 'end_datetime')
    def _compute_allow_template_creation(self):
        for slot in self:
            if not (slot.start_datetime and slot.end_datetime):
                slot.allow_template_creation = False
                continue

            values = self._prepare_template_values()
            domain = [(x, '=', values[x]) for x in values.keys()]
            existing_templates = self.env['planning.slot.template'].search(domain, limit=1)
            slot.allow_template_creation = not existing_templates and slot._different_than_template(check_empty=False)

    @api.depends('recurrency_id')
    def _compute_repeat(self):
        for slot in self:
            if slot.recurrency_id:
                slot.repeat = True
            else:
                slot.repeat = False

    @api.depends('recurrency_id.repeat_interval')
    def _compute_repeat_interval(self):
        recurrency_slots = self.filtered('recurrency_id')
        for slot in recurrency_slots:
            if slot.recurrency_id:
                slot.repeat_interval = slot.recurrency_id.repeat_interval
        (self - recurrency_slots).update(self.default_get(['repeat_interval']))

    @api.depends('recurrency_id.repeat_until')
    def _compute_repeat_until(self):
        for slot in self:
            if slot.recurrency_id:
                slot.repeat_until = slot.recurrency_id.repeat_until
            else:
                slot.repeat_until = False

    @api.depends('recurrency_id.repeat_number', 'repeat_type')
    def _compute_repeat_number(self):
        recurrency_slots = self.filtered('recurrency_id')
        for slot in recurrency_slots:
            slot.repeat_number = slot.recurrency_id.repeat_number
        (self - recurrency_slots).update(self.default_get(['repeat_number']))

    @api.depends('recurrency_id.repeat_unit')
    def _compute_repeat_unit(self):
        non_recurrent_slots = self.env['planning.slot']
        for slot in self:
            if slot.recurrency_id:
                slot.repeat_unit = slot.recurrency_id.repeat_unit
            else:
                non_recurrent_slots += slot
        non_recurrent_slots.update(self.default_get(['repeat_unit']))

    @api.depends('recurrency_id.repeat_type')
    def _compute_repeat_type(self):
        recurrency_slots = self.filtered('recurrency_id')
        for slot in recurrency_slots:
            if slot.recurrency_id:
                slot.repeat_type = slot.recurrency_id.repeat_type
        (self - recurrency_slots).update(self.default_get(['repeat_type']))

    def _inverse_repeat(self):
        for slot in self:
            if slot.repeat and not slot.recurrency_id.id:  # create the recurrence
                repeat_until = False
                repeat_number = 0
                if slot.repeat_type == "until":
                    repeat_until = datetime.combine(fields.Date.to_date(slot.repeat_until), datetime.max.time())
                    repeat_until = repeat_until.replace(tzinfo=pytz.timezone(slot.company_id.resource_calendar_id.tz or 'UTC')).astimezone(pytz.utc).replace(tzinfo=None)
                if slot.repeat_type == 'x_times':
                    repeat_number = slot.repeat_number
                recurrency_values = {
                    'repeat_interval': slot.repeat_interval,
                    'repeat_unit': slot.repeat_unit,
                    'repeat_until': repeat_until,
                    'repeat_number': repeat_number,
                    'repeat_type': slot.repeat_type,
                    'company_id': slot.company_id.id,
                }
                recurrence = self.env['planning.recurrency'].create(recurrency_values)
                slot.recurrency_id = recurrence
                slot.recurrency_id._repeat_slot()
            # user wants to delete the recurrence
            # here we also check that we don't delete by mistake a slot of which the repeat parameters have been changed
            elif not slot.repeat and slot.recurrency_id.id and (
                slot.repeat_unit == slot.recurrency_id.repeat_unit and
                slot.repeat_type == slot.recurrency_id.repeat_type and
                slot.repeat_until == slot.recurrency_id.repeat_until and
                slot.repeat_number == slot.recurrency_id.repeat_number and
                slot.repeat_interval == slot.recurrency_id.repeat_interval
            ):
                slot.recurrency_id._delete_slot(slot.end_datetime)
                slot.recurrency_id.unlink()  # will set recurrency_id to NULL

    def _inverse_template_creation(self):
        PlanningTemplate = self.env['planning.slot.template']
        for slot in self.filtered(lambda s: s.template_creation):
            values = slot._prepare_template_values()
            domain = [(x, '=', values[x]) for x in values.keys()]
            existing_templates = PlanningTemplate.search(domain, limit=1)
            if not existing_templates:
                template = PlanningTemplate.create(values)
                slot.write({'template_id': template.id, 'previous_template_id': template.id})
            else:
                slot.write({'template_id': existing_templates.id})

    @api.model
    def _calculate_start_end_dates(self,
                                 start_datetime,
                                 end_datetime,
                                 resource_id,
                                 template_id,
                                 previous_template_id,
                                 template_reset):

        def convert_datetime_timezone(dt, tz):
            return dt and pytz.utc.localize(dt).astimezone(tz)

        resource = resource_id or self.env.user.employee_id.resource_id
        company = self.company_id or self.env.company
        employee = resource_id.employee_id if resource_id.resource_type == 'user' else False
        user_tz = pytz.timezone(self.env.user.tz
                                or employee and employee.tz
                                or resource_id.tz
                                or self._context.get('tz')
                                or self.env.user.company_id.resource_calendar_id.tz
                                or 'UTC')

        if start_datetime and end_datetime and not template_id:
            # Transform the current column's start/end_datetime to the user's timezone from UTC
            current_start = convert_datetime_timezone(start_datetime, user_tz)
            current_end = convert_datetime_timezone(end_datetime, user_tz)
            # Look at the work intervals to examine whether the current start/end_datetimes are inside working hours
            calendar_id = resource.calendar_id if resource else company.resource_calendar_id
            work_interval = calendar_id._work_intervals_batch(current_start, current_end)[False]
            intervals = [(date_start, date_stop) for date_start, date_stop, attendance in work_interval]
            if not intervals:
                # If we are outside working hours, we do not edit the start/end_datetime
                # Return the start/end times back at UTC and remove the tzinfo from the object
                return (current_start.astimezone(pytz.utc).replace(tzinfo=None),
                        current_end.astimezone(pytz.utc).replace(tzinfo=None))

        # start_datetime and end_datetime are from 00:00 to 23:59 in user timezone
        # Converted in UTC, it gives an offset for any other timezone, _convert_datetime_timezone removes the offset
        start = convert_datetime_timezone(start_datetime, user_tz) if start_datetime else user_tz.localize(self._default_start_datetime())
        end = convert_datetime_timezone(end_datetime, user_tz) if end_datetime else user_tz.localize(self._default_end_datetime())

        # Get start and end in resource timezone so that it begins/ends at the same hour of the day as it would be in the user timezone
        # This is needed because _adjust_to_calendar takes start as datetime for the start of the day and end as end time for the end of the day
        # This can lead to different results depending on the timezone difference between the current user and the resource.
        # Example:
        # The user is in Europe/Brussels timezone (CET, UTC+1)
        # The resource is Asia/Krasnoyarsk timezone (IST, UTC+7)
        # The resource has two shifts during the day:
        #       - Morning shift: 8 to 12
        #       - Afternoon shift: 13 to 17
        # When the user selects a day to plan a shift for the resource, he expects to have the shift scheduled according to the resource's calendar given a search range between 00:00 and 23:59
        # The datetime received from the frontend is in the user's timezone meaning that the search interval will be between 23:00 and 22:59 in UTC
        # If the datetime is not adjusted to the resource's calendar beforehand, _adjust_to_calendar and _get_closest_work_time will shift the time to the resource's timezone.
        # The datetime given to _get_closest_work_time will be 6 AM once shifted in the resource's timezone. This will properly find the start of the morning shift at 8AM
        # For the afternoon shift, _get_closest_work_time will search the end of the shift that is close to 6AM the day after.
        # The closest shift found based on the end datetime will be the morning shift meaning that the work_interval_end will be the end of the morning shift the following day.
        if resource:
            work_interval_start, work_interval_end = resource._adjust_to_calendar(start.replace(tzinfo=pytz.timezone(resource.tz)), end.replace(tzinfo=pytz.timezone(resource.tz)), compute_leaves=False)[resource]
            start, end = (work_interval_start or start, work_interval_end or end)

        if not previous_template_id and not template_reset:
            start = start.astimezone(pytz.utc).replace(tzinfo=None)
            end = end.astimezone(pytz.utc).replace(tzinfo=None)

        if template_id and start_datetime:
            h = int(template_id.start_time)
            m = round(modf(template_id.start_time)[0] * 60.0)
            start = pytz.utc.localize(start_datetime).astimezone(pytz.timezone(resource.tz) if
                                                                 resource else user_tz)
            start = start.replace(hour=int(h), minute=int(m))
            start = start.astimezone(pytz.utc).replace(tzinfo=None)

            h, m = divmod(template_id.duration, 1)
            delta = timedelta(hours=int(h), minutes=int(m * 60))
            end = start + delta
        return (start, end)

    @api.depends('template_id')
    def _compute_datetime(self):
        for slot in self.filtered(lambda s: s.template_id):
            slot.start_datetime, slot.end_datetime = self._calculate_start_end_dates(slot.start_datetime,
                                                                                     slot.end_datetime,
                                                                                     slot.resource_id,
                                                                                     slot.template_id,
                                                                                     slot.previous_template_id,
                                                                                     slot.template_reset)

    @api.depends(lambda self: self._get_fields_breaking_publication())
    def _compute_publication_warning(self):
        for slot in self:
            slot.publication_warning = slot.resource_id and slot.resource_type != 'material' and slot.state == 'published'

    def _company_working_hours(self, start, end):
        company = self.company_id or self.env.company
        work_interval = company.resource_calendar_id._work_intervals_batch(start, end)[False]
        intervals = [(date_start, date_stop) for date_start, date_stop, attendance in work_interval]
        start_datetime, end_datetime = (start, end)
        if intervals and (end_datetime-start_datetime).days == 0: # Then we want the first working day and keep the end hours of this day
            start_datetime = intervals[0][0]
            end_datetime = [stop for start, stop in intervals if stop.date() == start_datetime.date()][-1]
        elif intervals and (end_datetime-start_datetime).days >= 0:
            start_datetime = intervals[0][0]
            end_datetime = intervals[-1][1]

        return (start_datetime, end_datetime)

    @api.depends('self_unassign_days_before', 'start_datetime')
    def _compute_unassign_deadline(self):
        slots_with_date = self.filtered('start_datetime')
        (self - slots_with_date).unassign_deadline = False
        for slot in slots_with_date:
            slot.unassign_deadline = fields.Datetime.subtract(slot.start_datetime, days=slot.self_unassign_days_before)

    @api.depends('unassign_deadline')
    def _compute_is_unassign_deadline_passed(self):
        slots_with_date = self.filtered('unassign_deadline')
        (self - slots_with_date).is_unassign_deadline_passed = False
        for slot in slots_with_date:
            slot.is_unassign_deadline_passed = slot.unassign_deadline < fields.Datetime.now()

    # Used in report
    def _group_slots_by_resource(self):
        grouped_slots = defaultdict(self.browse)
        for slot in self.sorted(key=lambda s: s.resource_id.name or ''):
            grouped_slots[slot.resource_id] |= slot
        return grouped_slots

    # ----------------------------------------------------
    # ORM overrides
    # ----------------------------------------------------

    @api.model
    def _read_group_fields_nullify(self):
        return ['working_days_count']

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        res = super().read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
        if lazy:
            return res

        null_fields = [f for f in self._read_group_fields_nullify() if any(f2.startswith(f) for f2 in fields)]
        if null_fields:
            for r in res:
                for f in null_fields:
                    if r[f] == 0:
                        r[f] = False
        return res

    @api.model
    def default_get(self, fields_list):
        res = super(Planning, self).default_get(fields_list)

        if res.get('resource_id'):
            resource_id = self.env['resource.resource'].browse(res.get('resource_id'))
            template_id, previous_template_id = [res.get(key) for key in ['template_id', 'previous_template_id']]
            template_id = template_id and self.env['planning.slot.template'].browse(template_id)
            previous_template_id = template_id and self.env['planning.slot.template'].browse(previous_template_id)
            res['start_datetime'], res['end_datetime'] = self._calculate_start_end_dates(res.get('start_datetime'),
                                                                                       res.get('end_datetime'),
                                                                                       resource_id,
                                                                                       template_id,
                                                                                       previous_template_id,
                                                                                       res.get('template_reset'))
        else:
            if 'start_datetime' in fields_list:
                start_datetime = fields.Datetime.from_string(res.get('start_datetime')) if res.get('start_datetime') else self._default_start_datetime()
                end_datetime = fields.Datetime.from_string(res.get('end_datetime')) if res.get('end_datetime') else self._default_end_datetime()
                start = pytz.utc.localize(start_datetime)
                end = pytz.utc.localize(end_datetime) if end_datetime else self._default_end_datetime()
                opening_hours = self._company_working_hours(start, end)
                res['start_datetime'] = opening_hours[0].astimezone(pytz.utc).replace(tzinfo=None)

                if 'end_datetime' in fields_list:
                    res['end_datetime'] = opening_hours[1].astimezone(pytz.utc).replace(tzinfo=None)

        return res

    def _init_column(self, column_name):
        """ Initialize the value of the given column for existing rows.
            Overridden here because we need to generate different access tokens
            and by default _init_column calls the default method once and applies
            it for every record.
        """
        if column_name != 'access_token':
            super(Planning, self)._init_column(column_name)
        else:
            query = """
                UPDATE %(table_name)s
                SET access_token = md5(md5(random()::varchar || id::varchar) || clock_timestamp()::varchar)::uuid::varchar
                WHERE access_token IS NULL
            """ % {'table_name': self._table}
            self.env.cr.execute(query)

    def name_get(self):
        group_by = self.env.context.get('group_by', [])
        field_list = [fname for fname in self._name_get_fields() if fname not in group_by]

        # Sudo as a planning manager is not able to read private project if he is not project manager.
        self = self.sudo()
        result = []
        for slot in self:
            # label part, depending on context `groupby`
            name_values = [
                self._fields[fname].convert_to_display_name(slot[fname], slot) if fname != 'resource_id' else slot.resource_id.name
                for fname in field_list
                if slot[fname]
            ][:3]  # limit to 3 labels
            name = ' - '.join(name_values) or slot.resource_id.name

            # add unicode bubble to tell there is a note
            if slot.name:
                name = u'%s \U0001F4AC' % name

            result.append([slot.id, name or ''])
        return result

    @api.model_create_multi
    def create(self, vals_list):
        Resource = self.env['resource.resource']
        for vals in vals_list:
            if vals.get('resource_id'):
                resource = Resource.browse(vals.get('resource_id'))
                if not vals.get('company_id'):
                    vals['company_id'] = resource.company_id.id
                if resource.resource_type == 'material':
                    vals['state'] = 'published'
            if not vals.get('company_id'):
                vals['company_id'] = self.env.company.id
        return super().create(vals_list)

    def write(self, values):
        if 'resource_id' in values and self.env['resource.resource'].browse(values['resource_id']).resource_type == 'material':
            values['state'] = 'published'
        # detach planning entry from recurrency
        if any(fname in values.keys() for fname in self._get_fields_breaking_recurrency()) and not values.get('recurrency_id'):
            values.update({'recurrency_id': False})
        result = super(Planning, self).write(values)
        # recurrence
        if any(key in ('repeat', 'repeat_unit', 'repeat_type', 'repeat_until', 'repeat_interval', 'repeat_number') for key in values):
            # User is trying to change this record's recurrence so we delete future slots belonging to recurrence A
            # and we create recurrence B from now on w/ the new parameters
            for slot in self:
                if slot.recurrency_id and values.get('repeat') is None:
                    repeat_type = values.get('repeat_type') or slot.recurrency_id.repeat_type
                    repeat_until = values.get('repeat_until') or slot.recurrency_id.repeat_until
                    repeat_number = values.get('repeat_number', 0) or slot.repeat_number
                    if repeat_type == 'until':
                        repeat_until = datetime.combine(fields.Date.to_date(repeat_until), datetime.max.time())
                        repeat_until = repeat_until.replace(tzinfo=pytz.timezone(slot.company_id.resource_calendar_id.tz or 'UTC')).astimezone(pytz.utc).replace(tzinfo=None)
                    recurrency_values = {
                        'repeat_interval': values.get('repeat_interval') or slot.recurrency_id.repeat_interval,
                        'repeat_unit': values.get('repeat_unit') or slot.recurrency_id.repeat_unit,
                        'repeat_until': repeat_until if repeat_type == 'until' else False,
                        'repeat_number': repeat_number,
                        'repeat_type': repeat_type,
                        'company_id': slot.company_id.id,
                    }
                    slot.recurrency_id.write(recurrency_values)
                    if slot.repeat_type == 'x_times':
                        recurrency_values['repeat_until'] = slot.recurrency_id._get_recurrence_last_datetime()
                    end_datetime = slot.end_datetime if values.get('repeat_unit') else recurrency_values.get('repeat_until')
                    slot.recurrency_id._delete_slot(end_datetime)
                    slot.recurrency_id._repeat_slot()
        return result

    # ----------------------------------------------------
    # Actions
    # ----------------------------------------------------

    def action_unlink(self):
        self.unlink()
        return {'type': 'ir.actions.act_window_close'}

    def action_see_overlaping_slots(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'planning.slot',
            'name': _('Shifts in Conflict'),
            'view_mode': 'gantt,list,form',
            'context': {
                'initialDate': min(self.mapped('start_datetime')),
                'search_default_conflict_shifts': True,
                'search_default_resource_id': self.resource_id.ids
            }
        }

    def action_self_assign(self):
        """ Allow planning user to self assign open shift. """
        self.ensure_one()
        # user must at least 'read' the shift to self assign (Prevent any user in the system (portal, ...) to assign themselves)
        if not self.check_access_rights('read', raise_exception=False):
            raise AccessError(_("You don't have the right to self assign."))
        if self.resource_id:
            raise UserError(_("You can not assign yourself to an already assigned shift."))
        return self.sudo().write({'resource_id': self.env.user.employee_id.resource_id.id if self.env.user.employee_id else False})

    def action_self_unassign(self):
        """ Allow planning user to self unassign from a shift, if the feature is activated """
        self.ensure_one()
        # The following condition will check the read access on planning.slot, and that user must at least 'read' the
        # shift to self unassign. Prevent any user in the system (portal, ...) to unassign any shift.
        if not self.allow_self_unassign:
            raise UserError(_("The company does not allow you to self unassign."))
        if self.is_unassign_deadline_passed:
            raise UserError(_("The deadline for unassignment has passed."))
        if self.employee_id != self.env.user.employee_id:
            raise UserError(_("You can not unassign another employee than yourself."))
        return self.sudo().write({'resource_id': False})

    # ----------------------------------------------------
    # Gantt - Calendar view
    # ----------------------------------------------------

    @api.model
    def gantt_unavailability(self, start_date, end_date, scale, group_bys=None, rows=None):
        start_datetime = fields.Datetime.from_string(start_date)
        end_datetime = fields.Datetime.from_string(end_date)
        resource_ids = set()

        # function to "mark" top level rows concerning resources
        # the propagation of that item to subrows is taken care of in the traverse function below
        def tag_resource_rows(rows):
            for row in rows:
                group_bys = row.get('groupedBy')
                res_id = row.get('resId')
                if group_bys:
                    # if resource_id is the first grouping attribute, we mark the row
                    if group_bys[0] == 'resource_id' and res_id:
                        resource_id = res_id
                        resource_ids.add(resource_id)
                        row['resource_id'] = resource_id
                    # else we recursively traverse the rows where resource_id appears in the group_by
                    elif 'resource_id' in group_bys:
                        tag_resource_rows(row.get('rows'))

        tag_resource_rows(rows)
        resources = self.env['resource.resource'] \
            .browse(resource_ids) \
            .filtered(lambda r: not r.flexible_hours)
        leaves_mapping = resources._get_unavailable_intervals(start_datetime, end_datetime)
        company_leaves = self.env.company.resource_calendar_id._unavailable_intervals(start_datetime.replace(tzinfo=pytz.utc), end_datetime.replace(tzinfo=pytz.utc))

        # function to recursively replace subrows with the ones returned by func
        def traverse(func, row):
            new_row = dict(row)
            if new_row.get('resource_id'):
                for sub_row in new_row.get('rows'):
                    sub_row['resource_id'] = new_row['resource_id']
            new_row['rows'] = [traverse(func, row) for row in new_row.get('rows')]
            return func(new_row)

        cell_dt = timedelta(hours=1) if scale in ['day', 'week'] else timedelta(hours=12)

        # for a single row, inject unavailability data
        def inject_unavailability(row):
            new_row = dict(row)

            calendar = company_leaves
            if row.get('resource_id'):
                resource_id = self.env['resource.resource'].browse(row.get('resource_id'))
                if resource_id:
                    if resource_id.flexible_hours:
                        return new_row
                    calendar = leaves_mapping[resource_id.id]

            # remove intervals smaller than a cell, as they will cause half a cell to turn grey
            # ie: when looking at a week, a employee start everyday at 8, so there is a unavailability
            # like: 2019-05-22 20:00 -> 2019-05-23 08:00 which will make the first half of the 23's cell grey
            notable_intervals = filter(lambda interval: interval[1] - interval[0] >= cell_dt, calendar)
            new_row['unavailabilities'] = [{'start': interval[0], 'stop': interval[1]} for interval in notable_intervals]
            return new_row

        return [traverse(inject_unavailability, row) for row in rows]

    @api.model
    def get_unusual_days(self, date_from, date_to=None):
        return self.env.user.employee_id._get_unusual_days(date_from, date_to)

    # ----------------------------------------------------
    # Period Duplication
    # ----------------------------------------------------

    @api.model
    def action_copy_previous_week(self, date_start_week, view_domain):
        date_end_copy = datetime.strptime(date_start_week, DEFAULT_SERVER_DATETIME_FORMAT)
        date_start_copy = date_end_copy - relativedelta(days=7)
        domain = [
            ('recurrency_id', '=', False),
            ('was_copied', '=', False)
        ]
        for dom in view_domain:
            if dom in ['|', '&', '!']:
                domain.append(dom)
            elif dom[0] == 'start_datetime':
                domain.append(('start_datetime', '>=', date_start_copy))
            elif dom[0] == 'end_datetime':
                domain.append(('end_datetime', '<=', date_end_copy))
            else:
                domain.append(tuple(dom))
        slots_to_copy = self.search(domain)

        new_slot_values = []
        new_slot_values = slots_to_copy._copy_slots(date_start_copy, date_end_copy, relativedelta(days=7))
        slots_to_copy.write({'was_copied': True})
        if new_slot_values:
            self.create(new_slot_values)
            return True
        return False

    # ----------------------------------------------------
    # Sending Shifts
    # ----------------------------------------------------

    def get_employees_without_work_email(self):
        """ Check if the employees to send the slot have a work email set.

            This method is used in a rpc call.

            :returns: a dictionnary containing the all needed information to continue the process.
                Returns None, if no employee or all employees have an email set.
        """
        self.ensure_one()
        if not self.employee_id.check_access_rights('write', raise_exception=False):
            return None
        employees = self.employee_id or self._get_employees_to_send_slot()
        employee_ids_without_work_email = employees.filtered(lambda employee: not employee.work_email).ids
        if not employee_ids_without_work_email:
            return None
        context = dict(self._context)
        context['force_email'] = True
        context['form_view_ref'] = 'planning.hr_employee_view_form_simplified'
        return {
            'relation': 'hr.employee',
            'res_ids': employee_ids_without_work_email,
            'context': context,
        }

    def _get_employees_to_send_slot(self):
        self.ensure_one()
        if not self.employee_id or not self.employee_id.work_email:
            domain = [('company_id', '=', self.company_id.id), ('work_email', '!=', False)]
            if self.role_id:
                domain = expression.AND([
                    domain,
                    ['|', ('planning_role_ids', '=', False), ('planning_role_ids', 'in', self.role_id.id)]])
            return self.env['hr.employee'].sudo().search(domain)
        return self.employee_id

    def _get_notification_action(self, notif_type, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': notif_type,
                'message': message,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_planning_publish(self):
        notif_type = "success"
        unpublished_shifts = self.filtered(lambda shift: shift.state == 'draft')
        if not unpublished_shifts:
            notif_type = "warning"
            message = _('There are no shifts to publish.')
        else:
            message = _('The shifts have successfully been published.')
            unpublished_shifts.action_publish()
        return self._get_notification_action(notif_type, message)

    def action_planning_publish_and_send(self):
        notif_type = "success"
        start, end = min(self.mapped('start_datetime')), max(self.mapped('end_datetime'))
        if all(shift.state == 'published' for shift in self) or not start or not end:
            notif_type = "warning"
            message = _('There are no shifts to publish and send.')
        else:
            planning = self.env['planning.planning'].create({
                'start_datetime': start,
                'end_datetime': end,
                'slot_ids': [(6, 0, self.ids)],
            })
            planning._send_planning()
            message = _('The shifts have successfully been published and sent.')
        return self._get_notification_action(notif_type, message)

    def action_send(self):
        self.ensure_one()
        if not self.employee_id or not self.employee_id.work_email:
            self.state = 'published'
        employee_ids = self._get_employees_to_send_slot()
        self._send_slot(employee_ids, self.start_datetime, self.end_datetime)
        message = _("The shift has successfully been sent.")
        return self._get_notification_action('success', message)

    def action_publish(self):
        self.write({
            'state': 'published',
            'publication_warning': False,
        })
        return True

    def action_unpublish(self):
        if not self.env.user.has_group('planning.group_planning_manager'):
            raise AccessError(_('You are not allowed to reset to draft shifts.'))
        published_shifts = self.filtered(lambda shift: shift.state == 'published' and shift.resource_type != 'material')
        if published_shifts:
            published_shifts.write({'state': 'draft', 'publication_warning': False,})
            notif_type = "success"
            message = _('The shifts have been successfully reset to draft.')
        else:
            notif_type = "warning"
            message = _('There are no shifts to reset to draft.')
        return self._get_notification_action(notif_type, message)

    # ----------------------------------------------------
    # Business Methods
    # ----------------------------------------------------

    def _calculate_slot_duration(self):
        self.ensure_one()
        period = self.end_datetime - self.start_datetime
        slot_duration = period.total_seconds() / 3600
        max_duration = (period.days + 1) * self.company_id.resource_calendar_id.hours_per_day
        if not max_duration or max_duration >= slot_duration:
            return slot_duration
        return max_duration

    # ----------------------------------------------------
    # Copy Slots
    # ----------------------------------------------------

    def _add_delta_with_dst(self, start, delta):
        """
        Add to start, adjusting the hours if needed to account for a shift in the local timezone between the
        start date and the resulting date (typically, because of DST)

        :param start: origin date in UTC timezone, but without timezone info (a naive date)
        :return resulting date in the UTC timezone (a naive date)
        """
        try:
            tz = pytz.timezone(self._get_tz())
        except pytz.UnknownTimeZoneError:
            tz = pytz.UTC
        start = start.replace(tzinfo=pytz.utc).astimezone(tz).replace(tzinfo=None)
        result = start + delta
        return tz.localize(result).astimezone(pytz.utc).replace(tzinfo=None)

    def _get_half_day_interval(self, values):
        """
            This method computes the afternoon and/or the morning whole interval where the planning slot exists.
            The resulting interval frames the slot in a bigger interval beginning before the slot (max 11:59:59 sooner)
            and finishing later (max 11:59:59 later)

            :param values: a dict filled in with new planning.slot vals
            :return an interval
        """
        return Intervals([(
            self._get_half_day_datetime(values['start_datetime']),
            self._get_half_day_datetime(values['end_datetime'], end=True),
            self.env['resource.calendar.attendance']
        )])

    def _get_half_day_datetime(self, dt, end=False):
        """
            This method computes a datetime in order to frame the slot in a bigger interval begining at midnight or
            noon and ending at midnight or noon.

            This method returns :
            - If end is False : Greatest datetime between midnight and noon that is sooner than the `dt` datetime;
            - Otherwise : Lowest datetime between midnight and noon that is later than the `dt` datetime.

            :param dt: input datetime
            :param end: wheter the dt is the end, resp. the start, of the interval if set, resp. not set.
            :return a datetime
        """
        self.ensure_one()
        tz = pytz.timezone(self._get_tz())
        localized_dt = pytz.utc.localize(dt).astimezone(tz)
        midday = localized_dt.replace(hour=12, minute=0, second=0)
        if end:
            return midday if midday > localized_dt else (localized_dt.replace(hour=0, minute=0, second=0) + timedelta(days=1))
        return midday if midday < localized_dt else localized_dt.replace(hour=0, minute=0, second=0)

    def _init_remaining_hours_to_plan(self, remaining_hours_to_plan):
        """
            Inits the remaining_hours_to_plan dict for a given slot and returns wether
            there are enough remaining hours.

            :return a bool representing wether or not there are still hours remaining
        """
        self.ensure_one()
        return True

    def _update_remaining_hours_to_plan_and_values(self, remaining_hours_to_plan, values):
        """
            Update the remaining_hours_to_plan with the allocated hours of the slot in `values`
            and returns wether there are enough remaining hours.

            If remaining_hours is strictly positive, and the allocated hours of the slot in `values` is
            higher than remaining hours, than update the values in order to consume at most the
            number of remaining_hours still available.

            :return a bool representing wether or not there are still hours remaining
        """
        self.ensure_one()
        return True

    def _get_split_slot_values(self, values, intervals, remaining_hours_to_plan, unassign=False):
        """
            Generates and returns slots values within the given intervals

            The slot in values, which represents a forecast planning slot, is split in multiple parts
            filling the (available) intervals.

            :return a vals list of the slot to create
        """
        self.ensure_one()
        splitted_slot_values = []
        for start_inter, end_inter, _resource in intervals:
            new_slot_vals = {
                **values,
                'start_datetime': start_inter.astimezone(pytz.utc).replace(tzinfo=None),
                'end_datetime': end_inter.astimezone(pytz.utc).replace(tzinfo=None),
                'allocated_hours': float_utils.float_round(
                    (((end_inter - start_inter).total_seconds() / 3600.0) * (self.allocated_percentage / 100.0)),
                    precision_digits=2
                ),
            }
            if not self._update_remaining_hours_to_plan_and_values(remaining_hours_to_plan, new_slot_vals):
                return splitted_slot_values
            if unassign:
                new_slot_vals['resource_id'] = False
            splitted_slot_values.append(new_slot_vals)
        return splitted_slot_values

    def _copy_slots(self, start_dt, end_dt, delta):
        """
            Copy slots planned between `start_dt` and `end_dt`, after a `delta`

            Takes into account the resource calendar and the slots already planned.
            All the slots will be copied, whatever the value of was_copied is.

            :return a vals list of the slot to create
        """
        # 1) Retrieve all the slots of the new period and create intervals within the slots will have to be unassigned (resource_slots_intervals),
        #    add it to `unavailable_intervals_per_resource`
        # 2) Retrieve all the calendars for the resource and their validity intervals (intervals within which the calendar is valid for the resource)
        # 3) For each calendar, retrieve the attendances and the leaves. Add attendances by resource in `attendance_intervals_per_resource` and
        #    the leaves by resource in `unavailable_intervals_per_resource`
        # 4) For each slot, check if the slot is at least within an attendance and outside a company leave :
        #    - If it is a planning :
        #       - Copy it if the resource is available
        #       - Copy and unassign it if the resource isn't available
        #    - Otherwise :
        #       - Split it and assign the part within resource work intervals
        #       - Split it and unassign the part within resource leaves and outside company leaves
        resource_per_calendar = defaultdict(lambda: self.env['resource.resource'])
        resource_calendar_validity_intervals = defaultdict(dict)
        attendance_intervals_per_resource = defaultdict(Intervals)  # key: resource, values: attendance intervals
        unavailable_intervals_per_resource = defaultdict(Intervals)  # key: resource, values: unavailable intervals
        attendance_intervals_per_calendar = defaultdict(Intervals)  # key: calendar, values: attendance intervals (used for company calendars)
        leave_intervals_per_calendar = defaultdict(Intervals)  # key: calendar, values: leave intervals (used for company calendars)
        new_slot_values = []
        # date utils variable
        start_dt_delta = start_dt + delta
        end_dt_delta = end_dt + delta
        start_dt_delta_utc = pytz.utc.localize(start_dt_delta)
        end_dt_delta_utc = pytz.utc.localize(end_dt_delta)
        # 1)
        # Search for all resource slots already planned
        resource_slots = self.search([
            ('start_datetime', '>=', start_dt_delta),
            ('end_datetime', '<=', end_dt_delta),
            ('resource_id', 'in', self.resource_id.ids)
        ])
        # And convert it into intervals
        for slot in resource_slots:
            unavailable_intervals_per_resource[slot.resource_id] |= Intervals([(
                pytz.utc.localize(slot.start_datetime),
                pytz.utc.localize(slot.end_datetime),
                self.env['resource.calendar.leaves'])])
        # 2)
        resource_calendar_validity_intervals = self.resource_id.sudo()._get_calendars_validity_within_period(
            start_dt_delta_utc, end_dt_delta_utc)
        for slot in self:
            if slot.resource_id:
                for calendar in resource_calendar_validity_intervals[slot.resource_id.id]:
                    resource_per_calendar[calendar] |= slot.resource_id
            company_calendar_id = slot.company_id.resource_calendar_id
            resource_per_calendar[company_calendar_id] |= self.env['resource.resource']  # ensures the company_calendar will be in resource_per_calendar keys.
        # 3)
        for calendar, resources in resource_per_calendar.items():
            # For each calendar, retrieves the work intervals of every resource
            attendances = calendar._attendance_intervals_batch(
                start_dt_delta_utc,
                end_dt_delta_utc,
                resources=resources
            )
            leaves = calendar._leave_intervals_batch(
                start_dt_delta_utc,
                end_dt_delta_utc,
                resources=resources
            )
            attendance_intervals_per_calendar[calendar] = attendances[False]
            leave_intervals_per_calendar[calendar] = leaves[False]
            for resource in resources:
                # for each resource, adds his/her attendances and unavailabilities for this calendar, during the calendar validity interval.
                attendance_intervals_per_resource[resource] |= (attendances[resource.id] & resource_calendar_validity_intervals[resource.id][calendar])
                unavailable_intervals_per_resource[resource] |= (leaves[resource.id] & resource_calendar_validity_intervals[resource.id][calendar])
        # 4)
        remaining_hours_to_plan = {}
        for slot in self:
            if not slot._init_remaining_hours_to_plan(remaining_hours_to_plan):
                continue
            values = slot.copy_data(default={'state': 'draft'})[0]
            if not values.get('start_datetime') or not values.get('end_datetime'):
                continue
            values['start_datetime'] = slot._add_delta_with_dst(values['start_datetime'], delta)
            values['end_datetime'] = slot._add_delta_with_dst(values['end_datetime'], delta)
            interval = Intervals([(
                pytz.utc.localize(values.get('start_datetime')),
                pytz.utc.localize(values.get('end_datetime')),
                self.env['resource.calendar.attendance']
            )])
            company_calendar = slot.company_id.resource_calendar_id
            # Check if interval is contained in the resource work interval
            attendance_resource = attendance_intervals_per_resource[slot.resource_id] if slot.resource_id else attendance_intervals_per_calendar[company_calendar]
            attendance_interval_resource = interval & attendance_resource
            # Check if interval is contained in the company attendances interval
            attendance_interval_company = interval & attendance_intervals_per_calendar[company_calendar]
            # Check if interval is contained in the company leaves interval
            unavailable_interval_company = interval & leave_intervals_per_calendar[company_calendar]
            if slot.allocation_type == 'planning' and not unavailable_interval_company and not attendance_interval_resource:
                # If the slot is not a forecast and there are no expected attendance, neither a company leave
                # check if the slot is planned during an afternoon or a morning during which the resource/company works/is opened

                # /!\ Name of such attendance is an "Extended Attendance", see hereafter
                interval = slot._get_half_day_interval(values)  # Get the afternoon and/or the morning whole interval where the planning slot exists.
                attendance_interval_resource = interval & attendance_resource
                attendance_interval_company = interval & attendance_intervals_per_calendar[company_calendar]
                unavailable_interval_company = interval & leave_intervals_per_calendar[company_calendar]
            unavailable_interval_resource = unavailable_interval_company if not slot.resource_id else (interval & unavailable_intervals_per_resource[slot.resource_id])
            if (attendance_interval_resource - unavailable_interval_company) or (attendance_interval_company - unavailable_interval_company):
                # Either the employee has, at least, some attendance that are not during the company unavailability
                # Either the company has, at least, some attendance that are not during the company unavailability

                if slot.allocation_type == 'planning':
                    # /!\ It can be an "Extended Attendance" (see hereabove), and the slot may be unassigned.
                    if unavailable_interval_resource or not attendance_interval_resource:
                        # if the slot is during an resourece unavailability, or the employee is not attending during the slot
                        if slot.resource_type != 'user':
                            # if the resource is not an employee and the resource is not available, do not copy it nor unassign it
                            continue
                        values['resource_id'] = False
                    if not slot._update_remaining_hours_to_plan_and_values(remaining_hours_to_plan, values):
                        # make sure the hours remaining are enough
                        continue
                    new_slot_values.append(values)
                else:
                    if attendance_interval_resource:
                        # if the resource has attendances, at least during a while of the future slot lifetime,
                        # 1) Work interval represents the availabilities of the employee
                        # 2) The unassigned intervals represents the slots where the employee should be unassigned
                        #    (when the company is not unavailable and the employee is unavailable)
                        work_interval_employee = (attendance_interval_resource - unavailable_interval_resource)
                        unassigned_interval = unavailable_interval_resource - unavailable_interval_company
                        split_slot_values = slot._get_split_slot_values(values, work_interval_employee, remaining_hours_to_plan)
                        if slot.resource_type == 'user':
                            split_slot_values += slot._get_split_slot_values(values, unassigned_interval, remaining_hours_to_plan, unassign=True)
                    elif slot.resource_type != 'user':
                        # If the resource type is not user and the slot can not be assigned to the resource, do not copy not unassign it
                        continue
                    else:
                        # When the employee has no attendance at all, we are in the case where the employee has a calendar different than the
                        # company (or no more calendar), so the slot will be unassigned
                        unassigned_interval = attendance_interval_company - unavailable_interval_company
                        split_slot_values = slot._get_split_slot_values(values, unassigned_interval, remaining_hours_to_plan, unassign=True)
                    # merge forecast slots in order to have visually bigger slots
                    new_slot_values += self._merge_slots_values(split_slot_values, unassigned_interval)
        return new_slot_values

    def _name_get_fields(self):
        """ List of fields that can be displayed in the name_get """
        return ['resource_id', 'role_id']

    def _get_fields_breaking_publication(self):
        """ Fields list triggering the `publication_warning` to True when updating shifts """
        return [
            'resource_id',
            'resource_type',
            'start_datetime',
            'end_datetime',
            'role_id',
        ]

    def _get_fields_breaking_recurrency(self):
        """Returns the list of field which when changed should break the relation of the forecast
            with it's recurrency
        """
        return [
            'resource_id',
            'role_id',
        ]

    @api.model
    def _get_template_fields(self):
        # key -> field from template
        # value -> field from slot
        return {'role_id': 'role_id', 'start_time': 'start_datetime', 'duration': 'duration'}

    def _get_tz(self):
        return (self.env.user.tz
                or self.employee_id.tz
                or self.resource_id.tz
                or self._context.get('tz')
                or self.company_id.resource_calendar_id.tz
                or 'UTC')

    def _prepare_template_values(self):
        """ extract values from shift to create a template """
        # compute duration w/ tzinfo otherwise DST will not be taken into account
        destination_tz = pytz.timezone(self._get_tz())
        start_datetime = pytz.utc.localize(self.start_datetime).astimezone(destination_tz)
        end_datetime = pytz.utc.localize(self.end_datetime).astimezone(destination_tz)

        # convert time delta to hours and minutes
        total_seconds = (end_datetime - start_datetime).total_seconds()
        m, s = divmod(total_seconds, 60)
        h, m = divmod(m, 60)

        return {
            'start_time': start_datetime.hour + start_datetime.minute / 60.0,
            'duration': h + (m / 60.0),
            'role_id': self.role_id.id
        }

    def _read_group_resource_id(self, resources, domain, order):
        dom_tuples = [(dom[0], dom[1]) for dom in domain if isinstance(dom, list) and len(dom) == 3]
        resource_ids = self.env.context.get('filter_resource_ids', False)
        if resource_ids:
            return self.env['resource.resource'].search([('id', 'in', resource_ids)], order=order)
        if self.env.context.get('planning_expand_resource') and ('start_datetime', '<=') in dom_tuples and ('end_datetime', '>=') in dom_tuples:
            if ('resource_id', '=') in dom_tuples or ('resource_id', 'ilike') in dom_tuples:
                filter_domain = self._expand_domain_m2o_groupby(domain, 'resource_id')
                return self.env['resource.resource'].search(filter_domain, order=order)
            filters = self._expand_domain_dates(domain)
            resources = self.env['planning.slot'].search(filters).mapped('resource_id')
            return resources.search([('id', 'in', resources.ids)], order=order)
        return resources

    def _read_group_role_id(self, roles, domain, order):
        dom_tuples = [(dom[0], dom[1]) for dom in domain if isinstance(dom, list) and len(dom) == 3]
        if self._context.get('planning_expand_role') and ('start_datetime', '<=') in dom_tuples and ('end_datetime', '>=') in dom_tuples:
            if ('role_id', '=') in dom_tuples or ('role_id', 'ilike') in dom_tuples:
                filter_domain = self._expand_domain_m2o_groupby(domain, 'role_id')
                return self.env['planning.role'].search(filter_domain, order=order)
            filters = expression.AND([[('role_id.active', '=', True)], self._expand_domain_dates(domain)])
            return self.env['planning.slot'].search(filters).mapped('role_id')
        return roles

    @api.model
    def _expand_domain_m2o_groupby(self, domain, filter_field=False):
        filter_domain = []
        for dom in domain:
            if dom[0] == filter_field:
                field = self._fields[dom[0]]
                if field.type == 'many2one' and len(dom) == 3:
                    if dom[1] == '=':
                        filter_domain = expression.OR([filter_domain, [('id', dom[1], dom[2])]])
                    elif dom[1] == 'ilike':
                        rec_name = self.env[field.comodel_name]._rec_name
                        filter_domain = expression.OR([filter_domain, [(rec_name, dom[1], dom[2])]])
        return filter_domain

    def _expand_domain_dates(self, domain):
        filters = []
        for dom in domain:
            if len(dom) == 3 and dom[0] == 'start_datetime' and dom[1] == '<=':
                max_date = dom[2] if dom[2] else datetime.now()
                max_date = max_date if isinstance(max_date, date) else datetime.strptime(max_date, '%Y-%m-%d %H:%M:%S')
                max_date = max_date + timedelta(days=7)
                filters.append((dom[0], dom[1], max_date))
            elif len(dom) == 3 and dom[0] == 'end_datetime' and dom[1] == '>=':
                min_date = dom[2] if dom[2] else datetime.now()
                min_date = min_date if isinstance(min_date, date) else datetime.strptime(min_date, '%Y-%m-%d %H:%M:%S')
                min_date = min_date - timedelta(days=7)
                filters.append((dom[0], dom[1], min_date))
            else:
                filters.append(dom)
        return filters

    @api.model
    def _format_datetime_to_user_tz(self, datetime_without_tz, record_env, tz=None, lang_code=False):
        return format_datetime(record_env, datetime_without_tz, tz=tz, dt_format='short', lang_code=lang_code)

    def _send_slot(self, employee_ids, start_datetime, end_datetime, include_unassigned=True, message=None):
        if not include_unassigned:
            self = self.filtered(lambda s: s.resource_id)
        if not self:
            return False

        employee_with_backend = employee_ids.filtered(lambda e: e.user_id and e.user_id.has_group('planning.group_planning_user'))
        employee_without_backend = employee_ids - employee_with_backend
        planning = False
        if len(self) > 1 or employee_without_backend:
            planning = self.env['planning.planning'].create({
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'include_unassigned': include_unassigned,
                'slot_ids': [(6, 0, self.ids)],
            })
        if len(self) > 1:
            return planning._send_planning(message=message, employees=employee_ids)

        self.ensure_one()

        template = self.env.ref('planning.email_template_slot_single')
        employee_url_map = {**employee_without_backend.sudo()._planning_get_url(planning), **employee_with_backend._slot_get_url(self)}

        view_context = dict(self._context)
        view_context.update({
            'open_shift_available': not self.employee_id,
            'mail_subject': _('Planning: new open shift available on'),
        })

        if self.employee_id:
            employee_ids = self.employee_id
            if self.allow_self_unassign:
                if employee_ids.filtered(lambda e: e.user_id and e.user_id.has_group('planning.group_planning_user')):
                    unavailable_link = '/planning/unassign/%s/%s' % (self.employee_id.sudo().employee_token, self.id)
                else:
                    unavailable_link = '/planning/%s/%s/unassign/%s?message=1' % (planning.access_token, self.employee_id.sudo().employee_token, self.id)
                view_context.update({'unavailable_link': unavailable_link})
            view_context.update({'mail_subject': _('Planning: new shift on')})

        mails_to_send_ids = []
        for employee in employee_ids.filtered(lambda e: e.work_email):
            if not self.employee_id and employee in employee_with_backend:
                view_context.update({'available_link': '/planning/assign/%s/%s' % (employee.sudo().employee_token, self.id)})
            elif not self.employee_id:
                view_context.update({'available_link': '/planning/%s/%s/assign/%s?message=1' % (planning.access_token, employee.sudo().employee_token, self.id)})
            start_datetime = self._format_datetime_to_user_tz(self.start_datetime, employee.env, tz=employee.tz, lang_code=employee.user_partner_id.lang)
            end_datetime = self._format_datetime_to_user_tz(self.end_datetime, employee.env, tz=employee.tz, lang_code=employee.user_partner_id.lang)
            unassign_deadline = self._format_datetime_to_user_tz(self.unassign_deadline, employee.env, tz=employee.tz, lang_code=employee.user_partner_id.lang)
            # update context to build a link for view in the slot
            view_context.update({
                'link': employee_url_map[employee.id],
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'employee_name': employee.name,
                'work_email': employee.work_email,
                'unassign_deadline': unassign_deadline
            })
            mail_id = template.with_context(view_context).send_mail(self.id, email_layout_xmlid='mail.mail_notification_light')
            mails_to_send_ids.append(mail_id)

        mails_to_send = self.env['mail.mail'].sudo().browse(mails_to_send_ids)
        if mails_to_send:
            mails_to_send.send()

        self.write({
            'state': 'published',
            'publication_warning': False,
        })

    # ---------------------------------------------------
    # Slots generation/copy
    # ---------------------------------------------------

    @api.model
    def _merge_slots_values(self, slots_to_merge, unforecastable_intervals):
        """
            Return a list of merged slots

            - `slots_to_merge` is a sorted list of slots
            - `unforecastable_intervals` are the intervals where the employee cannot work

            Example:
                slots_to_merge = [{
                    'start_datetime': '2021-08-01 08:00:00',
                    'end_datetime': '2021-08-01 12:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }, {
                    'start_datetime': '2021-08-01 13:00:00',
                    'end_datetime': '2021-08-01 17:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }, {
                    'start_datetime': '2021-08-02 08:00:00',
                    'end_datetime': '2021-08-02 12:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }, {
                    'start_datetime': '2021-08-03 08:00:00',
                    'end_datetime': '2021-08-03 12:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }, {
                    'start_datetime': '2021-08-04 13:00:00',
                    'end_datetime': '2021-08-04 17:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }]
                unforecastable = Intervals([(
                    datetime.datetime(2021, 8, 2, 13, 0, 0, tzinfo='UTC')',
                    datetime.datetime(2021, 8, 2, 17, 0, 0, tzinfo='UTC')',
                    self.env['resource.calendar.attendance'],
                )])

                result : [{
                    'start_datetime': '2021-08-01 08:00:00',
                    'end_datetime': '2021-08-02 12:00:00',
                    'employee_id': 1,
                    'allocated_hours': 12.0,
                }, {
                    'start_datetime': '2021-08-03 08:00:00',
                    'end_datetime': '2021-08-03 12:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }, {
                    'start_datetime': '2021-08-04 13:00:00',
                    'end_datetime': '2021-08-04 17:00:00',
                    'employee_id': 1,
                    'allocated_hours': 4.0,
                }]

            :return list of merged slots
        """
        if not slots_to_merge:
            return slots_to_merge
        # resulting vals_list of the merged slots
        new_slots_vals_list = []
        # accumulator for mergeable slots
        sum_allocated_hours = 0
        to_merge = []
        # invariants for mergeable slots
        common_allocated_percentage = slots_to_merge[0]['allocated_percentage']
        resource_id = slots_to_merge[0].get('resource_id')
        start_datetime = slots_to_merge[0]['start_datetime']
        previous_end_datetime = start_datetime
        for slot in slots_to_merge:
            mergeable = True
            if (not slot['start_datetime']
               or common_allocated_percentage != slot['allocated_percentage']
               or resource_id != slot['resource_id']
               or (slot['start_datetime'] - previous_end_datetime).total_seconds() > 3600 * 24):
                # last condition means the elapsed time between the previous end time and the
                # start datetime of the current slot should not be bigger than 24hours
                # if it's the case, then the slot can not be merged.
                mergeable = False
            if mergeable:
                end_datetime = slot['end_datetime']
                interval = Intervals([(
                    pytz.utc.localize(start_datetime),
                    pytz.utc.localize(end_datetime),
                    self.env['resource.calendar.attendance']
                )])
                if not (interval & unforecastable_intervals):
                    sum_allocated_hours += slot['allocated_hours']
                    if (end_datetime - start_datetime).total_seconds() < 3600 * 24:
                        # If the elapsed time between the first start_datetime and the
                        # current end_datetime is not higher than 24hours,
                        # slots cannot be merged as it won't be a forecast
                        to_merge.append(slot)
                    else:
                        to_merge = [{
                            **slot,
                            'start_datetime': start_datetime,
                            'allocated_hours': sum_allocated_hours,
                        }]
                else:
                    mergeable = False
            if not mergeable:
                new_slots_vals_list += to_merge
                to_merge = [slot]
                start_datetime = slot['start_datetime']
                common_allocated_percentage = slot['allocated_percentage']
                resource_id = slot.get('resource_id')
                sum_allocated_hours = slot['allocated_hours']
            previous_end_datetime = slot['end_datetime']
        new_slots_vals_list += to_merge
        return new_slots_vals_list

    def _get_duration_over_period(self, start_utc, stop_utc, work_intervals, calendar_intervals, has_allocated_hours=True):
        assert start_utc.tzinfo and stop_utc.tzinfo
        self.ensure_one()
        start, stop = start_utc.replace(tzinfo=None), stop_utc.replace(tzinfo=None)
        if has_allocated_hours and self.start_datetime >= start and self.end_datetime <= stop:
            return self.allocated_hours
        # if the slot goes over the gantt period, compute the duration only within
        # the gantt period
        ratio = self.allocated_percentage / 100.0 or 1
        start = max(start_utc, pytz.utc.localize(self.start_datetime))
        end = min(stop_utc, pytz.utc.localize(self.end_datetime))
        slot_interval = Intervals([(
            start, end, self.env['resource.calendar.attendance']
        )])
        if self.resource_id:
            working_intervals = work_intervals[self.resource_id.id]
        else:
            working_intervals = calendar_intervals[self.company_id.resource_calendar_id.id]
        return sum_intervals(slot_interval & working_intervals) * ratio

    def _gantt_progress_bar_resource_id(self, res_ids, start, stop):
        start_naive, stop_naive = start.replace(tzinfo=None), stop.replace(tzinfo=None)

        resources = self.env['resource.resource'].search([('id', 'in', res_ids)])
        planning_slots = self.env['planning.slot'].search([
            ('resource_id', 'in', res_ids),
            ('start_datetime', '<=', stop_naive),
            ('end_datetime', '>=', start_naive),
        ])
        planned_hours_mapped = defaultdict(float)
        resource_work_intervals, calendar_work_intervals = resources.sudo()._get_valid_work_intervals(start, stop)
        for slot in planning_slots:
            planned_hours_mapped[slot.resource_id.id] += slot._get_duration_over_period(
                start, stop, resource_work_intervals, calendar_work_intervals
            )
        # Compute employee work hours based on its work intervals.
        work_hours = {
            resource_id: sum_intervals(work_intervals)
            for resource_id, work_intervals in resource_work_intervals.items()
        }
        return {
            resource.id: {
                'is_material_resource': resource.resource_type == 'material',
                'value': planned_hours_mapped[resource.id],
                'max_value': work_hours.get(resource.id, 0.0),
                'employee_id': resource.employee_id.id,
            }
            for resource in resources
        }

    def _gantt_progress_bar(self, field, res_ids, start, stop):
        if field == 'resource_id':
            return dict(
                self._gantt_progress_bar_resource_id(res_ids, start, stop),
                warning=_("As there is no running contract during this period, this resource is not expected to work a shift. Planned hours:")
            )
        raise NotImplementedError("This Progress Bar is not implemented.")

    @api.model
    def gantt_progress_bar(self, fields, res_ids, date_start_str, date_stop_str):
        if not self.user_has_groups("base.group_user"):
            return {field: {} for field in fields}

        start_utc, stop_utc = string_to_datetime(date_start_str), string_to_datetime(date_stop_str)

        progress_bars = {}
        for field in fields:
            progress_bars[field] = self._gantt_progress_bar(field, res_ids[field], start_utc, stop_utc)

        return progress_bars

class PlanningRole(models.Model):
    _name = 'planning.role'
    _description = "Planning Role"
    _order = 'sequence'
    _rec_name = 'name'

    def _get_default_color(self):
        return randint(1, 11)

    active = fields.Boolean('Active', default=True)
    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer("Color", default=_get_default_color)
    resource_ids = fields.Many2many('resource.resource', 'resource_resource_planning_role_rel',
                                    'planning_role_id', 'resource_resource_id', 'Resources')
    sequence = fields.Integer()

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if not default.get('name'):
            default['name'] = _('%s (copy)', self.name)
        return super().copy(default=default)


class PlanningPlanning(models.Model):
    _name = 'planning.planning'
    _description = 'Schedule'

    @api.model
    def _default_access_token(self):
        return str(uuid.uuid4())

    start_datetime = fields.Datetime("Start Date", required=True)
    end_datetime = fields.Datetime("Stop Date", required=True)
    include_unassigned = fields.Boolean("Includes Open Shifts", default=True)
    access_token = fields.Char("Security Token", default=_default_access_token, required=True, copy=False, readonly=True)
    slot_ids = fields.Many2many('planning.slot')
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company,
        help="Company linked to the material resource. Leave empty for the resource to be available in every company.")
    date_start = fields.Date('Date Start', compute='_compute_dates')
    date_end = fields.Date('Date End', compute='_compute_dates')
    allow_self_unassign = fields.Boolean('Let Employee Unassign Themselves', related='company_id.planning_allow_self_unassign')
    self_unassign_days_before = fields.Integer("Days before shift for unassignment", related="company_id.planning_self_unassign_days_before", help="Deadline in days for shift unassignment")

    @api.depends('start_datetime', 'end_datetime')
    @api.depends_context('uid')
    def _compute_dates(self):
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        for planning in self:
            planning.date_start = pytz.utc.localize(planning.start_datetime).astimezone(tz).replace(tzinfo=None)
            planning.date_end = pytz.utc.localize(planning.end_datetime).astimezone(tz).replace(tzinfo=None)

    def _compute_display_name(self):
        """ This override is need to have a human readable string in the email light layout header (`message.record_name`) """
        for planning in self:
            planning.display_name = _('Planning')

    # ----------------------------------------------------
    # Business Methods
    # ----------------------------------------------------

    def _send_planning(self, message=None, employees=False):
        email_from = self.env.user.email or self.env.user.company_id.email or ''
        sent_slots = self.env['planning.slot']
        for planning in self:
            # prepare planning urls, recipient employees, ...
            slots = planning.slot_ids
            slots_open = slots.filtered(lambda slot: not slot.resource_id) if planning.include_unassigned else 0

            # extract planning URLs
            employees = employees or slots.mapped('employee_id')
            employee_url_map = employees.sudo()._planning_get_url(planning)

            # send planning email template with custom domain per employee
            template = self.env.ref('planning.email_template_planning_planning', raise_if_not_found=False)
            template_context = {
                'slot_unassigned_count': slots_open and len(slots_open),
                'slot_total_count': slots and len(slots),
                'message': message,
            }
            if template:
                # /!\ For security reason, we only given the public employee to render mail template
                for employee in self.env['hr.employee.public'].browse(employees.ids):
                    if employee.work_email:
                        template_context['employee'] = employee
                        template_context['start_datetime'] = planning.date_start
                        template_context['end_datetime'] = planning.date_end
                        template_context['planning_url'] = employee_url_map[employee.id]
                        template_context['assigned_new_shift'] = bool(slots.filtered(lambda slot: slot.employee_id.id == employee.id))
                        template.with_context(**template_context).send_mail(planning.id, email_values={'email_to': employee.work_email, 'email_from': email_from}, email_layout_xmlid='mail.mail_notification_light')
            sent_slots |= slots
        # mark as sent
        sent_slots.write({
            'state': 'published',
            'publication_warning': False
        })
        return True
