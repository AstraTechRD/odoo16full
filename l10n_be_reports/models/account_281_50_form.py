# -*- coding: utf-8 -*-

import base64

from odoo import _, fields, models, api
from odoo.exceptions import UserError
from .ONSS_country_mapping import ONSS_COUNTRY_CODE_MAPPING


class Form28150(models.Model):
    _name = "l10n_be.form.281.50"
    _description = "Represents a 281.50 form"
    _inherit = ['mail.thread']

    form_325_id = fields.Many2one(
        'l10n_be.form.325',
        string='Form 325',
        readonly=True,
        required=True,
    )
    state = fields.Selection(
        string='State',
        related='form_325_id.state',
    )
    official_id = fields.Char(
        string='Identification number',
        compute='_compute_official_id', store=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='form_325_id.company_id',
    )
    treatment_type = fields.Selection(
        related='form_325_id.treatment_type',
        readonly=True,
        string="Treatment Type",
        help="This field represents the nature of the form.",
    )
    income_debtor_bce_number = fields.Char(
        string='Income debtor BCE number',
        related='form_325_id.debtor_bce_number',
    )
    reference_year = fields.Integer(
        string='Reference year',
        related='form_325_id.reference_year',
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        required=True,
        help="Partner for which this 281.50 form has been created",
        readonly=True,
    )
    partner_name = fields.Char(
        string='Partner Name',
        help='Name of the partner when the form was created',
        states={'generated': [('readonly', True)]},
        tracking=True,
        compute='_compute_partner_name', store=True, readonly=False,
    )
    partner_address = fields.Char(
        string='Address',
        help='Address of the partner when the form was created',
        states={'generated': [('readonly', True)]},
        tracking=True,
        compute='_compute_partner_address', store=True, readonly=False,
    )
    country_id = fields.Many2one(
        comodel_name='res.country',
        string='Country',
        help='Country of the partner when the form was created',
        states={'generated': [('readonly', True)]},
        tracking=True,
        compute='_compute_country_id', store=True, readonly=False,
    )
    partner_zip = fields.Char(
        string='Zip',
        help='Zip of the partner when the form was created',
        states={'generated': [('readonly', True)]},
        tracking=True,
        compute='_compute_partner_zip', store=True, readonly=False,
    )
    partner_city = fields.Char(
        string='City',
        help='City of the partner when the form was created',
        states={'generated': [('readonly', True)]},
        tracking=True,
        compute='_compute_partner_city', store=True, readonly=False,
    )
    partner_job_position = fields.Char(
        string='Job position',
        states={'generated': [('readonly', True)]},
        tracking=True,
        compute='_compute_partner_job_position', store=True, readonly=False,
    )
    partner_citizen_identification = fields.Char(
        string='Citizen identification number',
        states={'generated': [('readonly', True)]},
        tracking=True,
        compute='_compute_partner_citizen_identification', store=True, readonly=False,
    )
    partner_bce_number = fields.Char(
        string='BCE number',
        states={'generated': [('readonly', True)]},
        tracking=True,
        compute='_compute_partner_bce_number', store=True, readonly=False,
    )
    partner_is_natural_person = fields.Boolean(
        string='Natural person',
        help='Is the partner a natural person? (as opposed to a moral person)',
        compute='_compute_partner_is_natural_person', store=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='form_325_id.currency_id',
    )
    commissions = fields.Monetary(
        string="Commissions",
        default=0.0,
        required=True,
        readonly=True,
    )
    fees = fields.Monetary(
        string="Fees",
        default=0.0,
        required=True,
        readonly=True,
    )
    atn = fields.Monetary(
        string="ATN",
        default=0.0,
        required=True,
        readonly=True,
    )
    exposed_expenses = fields.Monetary(
        string="Exposed expenses",
        default=0.0,
        required=True,
        readonly=True,
    )
    total_remuneration = fields.Monetary(
        string="Total remuneration",
        compute='_compute_total_remuneration',
    )
    paid_amount = fields.Monetary(
        string="Paid amount",
        default=0.0,
        required=True,
        readonly=True,
    )

    def name_get(self):
        return [(record.id, f"{record.reference_year} {record.partner_name}") for record in self]

    @api.depends('state')
    def _compute_official_id(self):
        forms_to_compute = self.filtered(lambda f: f.state == f.state == 'generated')
        if forms_to_compute:
            sequences = self.env['ir.sequence'].search([
                ('code', '=', 'l10n_be.l10n_be.form.281.50'),
                ('company_id', 'in', self.company_id.ids)
            ], order='company_id')

            companies_missing_sequences = self.company_id - sequences.company_id
            if companies_missing_sequences:
                sequences |= self.env['ir.sequence'].create([{
                    'name': 'l10n_be form 281.50',
                    'code': 'l10n_be.l10n_be.form.281.50',
                    'number_next': 1,
                    'number_increment': 1,
                    'company_id': company.id,
                    'use_date_range': True,
                } for company in companies_missing_sequences])

            sequence_per_company = {seq.company_id.id: seq for seq in sequences}

            for form in forms_to_compute:
                sequence = sequence_per_company.get(form.company_id.id)
                form.official_id = sequence.next_by_id(sequence_date=fields.Datetime.to_datetime(str(form.reference_year)))

    @api.depends('commissions', 'fees', 'atn', 'exposed_expenses')
    def _compute_total_remuneration(self):
        for form in self:
            form.total_remuneration = form.commissions + form.fees + form.atn + form.exposed_expenses

    @api.depends('partner_id')
    def _compute_partner_name(self):
        for form in self:
            form.partner_name = form.partner_id.name

    @api.depends('partner_id')
    def _compute_partner_address(self):
        for form in self:
            form.partner_address = form.partner_id._formated_address()

    @api.depends('partner_id')
    def _compute_partner_zip(self):
        for form in self:
            form.partner_zip = form.partner_id.zip

    @api.depends('partner_id')
    def _compute_partner_city(self):
        for form in self:
            form.partner_city = form.partner_id.city

    @api.depends('partner_id')
    def _compute_country_id(self):
        for form in self:
            form.country_id = form.partner_id.country_id.id

    @api.depends('partner_id')
    def _compute_partner_citizen_identification(self):
        for form in self:
            form.partner_citizen_identification = form.partner_id.citizen_identification

    @api.depends('partner_is_natural_person')
    def _compute_partner_bce_number(self):
        for form in self:
            if not form.partner_is_natural_person:
                form.partner_bce_number = form.partner_id._get_bce_number()

    @api.depends('partner_id')
    def _compute_partner_is_natural_person(self):
        for form in self:
            form.partner_is_natural_person = not bool(form.partner_id.is_company)

    @api.depends('partner_id')
    def _compute_partner_country(self):
        for form in self:
            form.partner_country = form.partner_id.country_id

    @api.ondelete(at_uninstall=False)
    def _unlink_only_if_state_not_generated(self):
        if self.filtered(lambda x: x.state == 'generated'):
            raise UserError(_("You can't delete a 281.50 for which its form 325 xml has been generated"))

    def get_dict_values(self):
        self.ensure_one()
        is_partner_from_belgium = self.country_id.code == 'BE'
        sum_control = self.commissions + self.fees + self.atn + self.exposed_expenses + self.total_remuneration + self.paid_amount
        return {
            # F2XXX: info for this 281.XX tax form
            'F2002': self.reference_year,
            'F2005': self.income_debtor_bce_number,
            'F2008': 28150,  # fiche type
            'F2009': int(self.official_id),  # id number of this fiche for this beneficiary
            'F2013': self.partner_name[:41],
            'F2015': self.partner_address,
            'F2016': self.partner_zip if is_partner_from_belgium else '',
            'F2017': self.partner_city,
            'F2028': self.treatment_type,  # fiche treatment: 0 -> ordinary, 1 -> modification, 2 -> adding, 3 -> cancellation
            'F2029': 0,
            'F2105': 0,  # birthplace
            'F2018': ONSS_COUNTRY_CODE_MAPPING.get(self.country_id.code),
            'F2018_display': self.country_id.name,
            'F2112': '' if is_partner_from_belgium else self.partner_zip,
            'F2114': '',  # firstname: full name is set on F2013
            # F50_2XXX: info for this 281.50 tax form
            'F50_2030': '1' if self.partner_is_natural_person else '2',
            'F50_2031': 0 if self.paid_amount != 0 else 1,
            'F50_2059': sum_control,  # Total control : sum 2060 to 2088 for this 281.50 form
            'F50_2060': self.commissions,
            'F50_2061': self.fees,
            'F50_2062': self.atn,
            'F50_2063': self.exposed_expenses,
            'F50_2064': self.total_remuneration,  # Total from 2060 to 2063
            'F50_2065': self.paid_amount,
            'F50_2066': 0,  # irrelevant: sport remuneration
            'F50_2067': 0,  # irrelevant: manager remuneration
            'F50_2099': '',  # further comments concerning amounts from 2060 to 2067
            'F50_2103': '',  # nature of the amounts
            'F50_2107': self.partner_job_position,
            'F50_2109': self.partner_citizen_identification,
            'F50_2110': self.partner_bce_number if is_partner_from_belgium else '',  # KBO/BCE number
        }

    def _get_pdf_file_name(self):
        return f"{self.official_id}-{self.reference_year}-{self.partner_name}-281_50.pdf"

    def _generate_281_50_form_pdf(self):
        """ Function to create the PDF file.
            :param: values_dict All information about the partner
            :return: A PDF file
        """
        self.ensure_one()
        pdf_file, dummy = self.env['ir.actions.report']._render_qweb_pdf("l10n_be_reports.action_report_partner_281_50_pdf", res_ids=self)
        return pdf_file

    def action_download_281_50_individual_pdf(self):
        self.ensure_one()
        self.partner_id.form_file = base64.b64encode(self._generate_281_50_form_pdf())
        return {
            'type': 'ir.actions.act_url',
            'name': _("Download 281.50 Form PDF"),
            'url': f"/web/content/res.partner/{self.partner_id.id}/form_file/{self._get_pdf_file_name()}?download=true"
        }

    def action_open_281_50_view_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.display_name,
            'res_model': 'l10n_be.form.281.50',
            'res_id': self.id,
            'view_mode': 'form',
        }
