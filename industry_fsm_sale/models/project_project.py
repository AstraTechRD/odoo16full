# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class Project(models.Model):
    _inherit = "project.project"

    allow_material = fields.Boolean("Products on Tasks", compute="_compute_allow_material", store=True, readonly=False)
    allow_quotations = fields.Boolean(
        "Extra Quotations", compute="_compute_allow_quotations", store=True, readonly=False)
    allow_billable = fields.Boolean(
         compute='_compute_allow_billable', store=True, readonly=False)
    sale_line_id = fields.Many2one(
        compute="_compute_sale_line_id", store=True, readonly=False)

    _sql_constraints = [
        ('material_imply_billable', "CHECK((allow_material = 't' AND allow_billable = 't') OR (allow_material = 'f'))", 'The material can be allowed only when the task can be billed.'),
        ('fsm_imply_task_rate', "CHECK((is_fsm = 't' AND sale_line_id IS NULL) OR (is_fsm = 'f'))", 'An FSM project must be billed at task rate or employee rate.'),
        ('timesheet_product_required_if_billable_and_timesheets_and_fsm_projects', """
            CHECK(
                (allow_billable = 't' AND allow_timesheets = 't' AND is_fsm = 't' AND timesheet_product_id IS NOT NULL)
                OR (allow_billable IS NOT TRUE)
                OR (allow_timesheets IS NOT TRUE)
                OR (is_fsm IS NOT TRUE)
                OR (allow_billable IS NULL)
                OR (allow_timesheets IS NULL)
                OR (is_fsm IS NULL)
            )""", 'The timesheet product is required when the fsm project can be billed and timesheets are allowed.'),
    ]

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'allow_quotations' in fields_list and 'allow_quotations' not in defaults and defaults.get('is_fsm'):
            defaults['allow_quotations'] = self.env.user.has_group('industry_fsm.group_fsm_quotation_from_task')
        return defaults

    @api.depends('is_fsm')
    def _compute_allow_quotations(self):
        if not self.env.user.has_group('industry_fsm.group_fsm_quotation_from_task'):
            self.allow_quotations = False
        else:
            for project in self:
                project.allow_quotations = project.is_fsm

    @api.depends('is_fsm', 'allow_material')
    def _compute_allow_billable(self):
        for project in self:
            project.allow_billable = project.allow_billable or project.is_fsm or project.allow_material

    @api.depends('allow_billable', 'is_fsm')
    def _compute_allow_material(self):
        for project in self:
            project.allow_material = project.allow_billable and project.is_fsm

    def flush_model(self, fnames=None):
        if fnames is not None:
            # force 'allow_billable' and 'allow_material' to be flushed
            # altogether in order to satisfy the SQL constraint above
            fnames = set(fnames)
            if 'allow_billable' in fnames or 'allow_material' in fnames:
                fnames.add('allow_billable')
                fnames.add('allow_material')
        return super().flush_model(fnames)

    def flush_recordset(self, fnames=None):
        if fnames is not None:
            # force 'allow_billable' and 'allow_material' to be flushed
            # altogether in order to satisfy the SQL constraint above
            fnames = set(fnames)
            if 'allow_billable' in fnames or 'allow_material' in fnames:
                fnames.add('allow_billable')
                fnames.add('allow_material')
        return super().flush_recordset(fnames)

    @api.depends('sale_line_id', 'sale_line_employee_ids', 'allow_billable', 'is_fsm')
    def _compute_pricing_type(self):
        fsm_projects = self.filtered(lambda project: project.allow_billable and project.is_fsm)
        for fsm_project in fsm_projects:
            if fsm_project.sale_line_employee_ids:
                fsm_project.update({'pricing_type': 'employee_rate'})
            else:
                fsm_project.update({'pricing_type': 'task_rate'})
        super(Project, self - fsm_projects)._compute_pricing_type()

    def _search_pricing_type(self, operator, value):
        domain = super()._search_pricing_type(operator, value)
        if value == 'fixed_rate':
            fsm_domain = [('is_fsm', operator, False)]
            if operator == '=':
                domain = expression.AND([fsm_domain, domain])
            else:
                domain = expression.OR([fsm_domain, domain])
        elif value in ['task_rate', 'employee_rate']:
            fsm_domain = [
                ('is_fsm', '=', True),
                ('allow_billable', '=', True),
                ('sale_line_employee_ids', '!=' if value == 'employee_rate' else '=', False),
            ]
            if operator == '=':
                domain = expression.OR([fsm_domain, domain])
            else:
                fsm_domain = expression.normalize_domain(fsm_domain)
                fsm_domain.insert(0, expression.NOT_OPERATOR)
                domain = expression.AND([expression.distribute_not(fsm_domain), domain])
        return domain

    @api.depends('is_fsm')
    def _compute_sale_line_id(self):
        # We cannot have a SOL in the fsm project
        fsm_projects = self.filtered('is_fsm')
        fsm_projects.update({'sale_line_id': False})
        super(Project, self - fsm_projects)._compute_sale_line_id()

    @api.depends('partner_id', 'pricing_type', 'is_fsm')
    def _compute_display_create_order(self):
        fsm_projects = self.filtered('is_fsm')
        fsm_projects.update({'display_create_order': False})
        super(Project, self - fsm_projects)._compute_display_create_order()

    @api.depends('sale_line_employee_ids.sale_line_id', 'sale_line_id')
    def _compute_partner_id(self):
        basic_projects = self.filtered(lambda project: not project.is_fsm)
        super(Project, basic_projects)._compute_partner_id()

    def _get_profitability_sale_order_items_domain(self, domain=None):
        quotation_projects = self.filtered('allow_quotations')
        if quotation_projects:
            include_additional_sale_orders = [('order_id', 'in', quotation_projects._get_additional_quotations([('state', 'in', ['sale', 'done'])]).ids)]
            domain = include_additional_sale_orders \
                if domain is None \
                else expression.OR([domain, include_additional_sale_orders])
        return super()._get_profitability_sale_order_items_domain(domain)

    def _get_additional_quotations_query(self, domain=None):
        if domain is None:
            domain = []
        SaleOrder = self.env['sale.order']
        query = SaleOrder._where_calc(expression.AND([domain, [('task_id', '!=', False)]]))
        SaleOrder._apply_ir_rules(query, 'read')
        query.join(
            SaleOrder._table, 'task_id',
            'project_task', 'id',
            'task_id',
            '{rhs}."project_id" in (%s)', (','.join(map(str, self.ids)),),
        )
        return query

    def _get_additional_quotations(self, domain=None):
        return self.env['sale.order'].browse(self._get_additional_quotations_query(domain))

    def _get_sale_order_items_query(self, domain_per_model=None):
        basic_project_domain = [('is_fsm', '=', False)]  # when the project is a fsm one, no SOL is linked to that project.
        employee_mapping_domain = [('project_id.is_fsm', '=', False)]
        if domain_per_model is None:
            domain_per_model = {
                'project.project': basic_project_domain,
                'project.sale.line.employee.map': employee_mapping_domain,
            }
        else:
            domain_per_model['project.project'] = expression.AND([
                domain_per_model.get('project.project', []),
                basic_project_domain,
            ])
            domain_per_model['project.sale.line.employee.map'] = expression.AND([
                domain_per_model.get('project.sale.line.employee.map', []),
                employee_mapping_domain,
            ])
        return super()._get_sale_order_items_query(domain_per_model)
