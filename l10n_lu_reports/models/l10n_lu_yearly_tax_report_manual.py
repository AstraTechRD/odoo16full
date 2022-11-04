# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from .l10n_lu_tax_report_data import YEARLY_FIELDS_MAPPING

class L10nLuYearlyTaxReportManual(models.Model):
    """
    This wizard is used to store the data typical of Luxembourg's yearly tax report
    that can't be automatically inferred, but must be manually entered by the user.
    """
    _name = 'l10n_lu.yearly.tax.report.manual'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Annual Tax Report'

    # ==== DEFAULTS ====
    def _get_default_company_ids(self):
        options = self.env.ref('l10n_lu.tax_report')._get_options()
        if options.get('multi_company'):
            return [c['id'] for c in options['multi_company']]
        return self.env.company.ids if self.env.company.account_fiscal_country_id.code == "LU" else []

    # ==== XML generation fields ====
    report_data = fields.Binary('Report file', readonly=True, attachment=False)
    filename = fields.Char(string='Filename', size=256, readonly=True)
    # ==== Business fields ====
    appendix_ids = fields.One2many(
        string="Appendix fields",
        comodel_name="l10n_lu_reports.report.appendix.expenditures",
        inverse_name="report_id",
        required=True,
        readonly=False,
        tracking=True,
        store=True,
        compute="_compute_monthly_totals_breakdown_annex",
    )
    state = fields.Selection(string="Status", selection=[("not_exported", "Not exported"), ("exported", "Exported")], copy=False, default="not_exported", required=True, tracking=True)
    year = fields.Char(required=True, default=lambda self: fields.Date.today().year - 1, states={'exported': [('readonly', True)]}, tracking=True)
    avg_nb_employees = fields.Float(string="Average number of employees for the fiscal year",
                                    compute="_compute_avg_nb_employees", states={'exported': [('readonly', True)]}, tracking=True)
    avg_nb_employees_with_salary = fields.Float("  - with salary or wage", states={'exported': [('readonly', True)]}, tracking=True)
    avg_nb_employees_with_no_salary = fields.Float("  - with no salary (family members)")
    phone_number = fields.Char(string="Phone number for contacting the declaring person", size=30, states={'exported': [('readonly', True)]}, tracking=True)
    books_records_documents = fields.Char(
        string="Books, records and documents",
        help="Taxable persons established in Luxembourg: place of storage of books, records and documents the keeping, "
             "drafting and issuing of which are required by the modified VAT law of 12 February 1979 and its "
             "implementing provisions, when this place of storage is outside of the territory of Luxemburg (Art. 65)",
        size=30, states={'exported': [('readonly', True)]}, tracking=True
    )
    submitted_rcs = fields.Boolean(string="Annual accounts submitted to the Trade and Companies Register (RCS)", states={'exported': [('readonly', True)]}, tracking=True)
    company_ids = fields.Many2many('res.company', string="Companies", required=True, default=_get_default_company_ids)

    def name_get(self):
        result = []
        for r in self:
            result.append((r.id, _('Yearly Tax Report Manual Data') + ' (' + ', '.join(r.company_ids.mapped('name')) + ') ' + r.year))
        return result

    @api.depends("avg_nb_employees_with_salary", "avg_nb_employees_with_no_salary")
    def _compute_avg_nb_employees(self):
        self.avg_nb_employees = self.avg_nb_employees_with_no_salary + self.avg_nb_employees_with_salary

    # Yearly report fields: some fields in the yearly report are splits of fields in the monthly report;
    # since the taxes + tax tags in the LU localization are based on the monthly report,
    # there is no way to know how to split the amounts from the monthly report to the yearly report without user input.
    # Field 472 (Sales/Receipts) split
    report_section_001 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_002 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_003 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_004 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_005 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_206 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_007 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # Field 455 (Application of goods) split
    report_section_008 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_009 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Field 456 (Non-business use of goods and supply of services free of charge) split
    report_section_010 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_011 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Field 457 (Intra-community supply) split
    report_section_013 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_202 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Field 458 (Input tax invoiced by other taxable persons)
    report_section_077 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_081 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_085 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Field 459 (Due in respect of IC acquisition of goods)
    report_section_078 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_082 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_086 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Field 460 (Due or paid in respect of importation of goods)
    report_section_079 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_083 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_087 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Field 461 (Due under the reverse charge)
    report_section_404 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_405 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_406 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Names and addresses to be specified
    # Accountant (A9)
    report_section_397 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_398 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_399 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    # Lessor (A18)
    report_section_400 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_401 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_402 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    # Monthly totals
    # Add _compute to some of the inherited fields (monthly totals) because otherwise initially they are set to 0 and are not prefilled
    # This allows prefilling monthly totals without depending on the account.tax.report values that are not accessible from the form view of this model
    # These fields are not stored because storing causes compute method to be called when the form is saved
    # And the account.tax.report does not contain the necessary lines then, and the fields are set to 0 even though they shouldn't be
    report_section_472 = fields.Float(compute="_compute_monthly_totals")
    report_section_472_rest = fields.Float(compute="_compute_totals")
    report_section_455 = fields.Float(compute="_compute_monthly_totals")
    report_section_455_rest = fields.Float(compute="_compute_totals")
    report_section_456 = fields.Float(compute="_compute_monthly_totals")
    report_section_456_rest = fields.Float(compute="_compute_totals")
    report_section_457 = fields.Float(compute="_compute_monthly_totals")
    report_section_457_rest = fields.Float(compute="_compute_totals")
    report_section_458 = fields.Float(compute="_compute_monthly_totals")
    report_section_458_rest = fields.Float(compute="_compute_totals")
    report_section_459 = fields.Float(compute="_compute_monthly_totals")
    report_section_459_rest = fields.Float(compute="_compute_totals")
    report_section_460 = fields.Float(compute="_compute_monthly_totals")
    report_section_460_rest = fields.Float(compute="_compute_totals")
    report_section_461 = fields.Float(compute="_compute_monthly_totals")
    report_section_461_rest = fields.Float(compute="_compute_totals")
    # Field 457 (Intra-community supply) - field 203 is missing in the previous module
    report_section_203 = fields.Float(readonly=False, states={'exported': [('readonly', True)]}, tracking=True, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Total Adjustment of deductions
    report_section_098 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_099 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_229 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_100 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # Annex
    # Total operational expenditures
    # Gross salaries (6)
    report_section_239 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_240 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_114 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_192 = fields.Float(tracking=True, compute="_compute_192")
    report_section_193 = fields.Float(tracking=True, compute="_compute_193")
    # of which productive salaries
    report_section_241 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_242 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_243 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Gross wages (6)
    report_section_244 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_245 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_246 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Occasional salaries
    report_section_247 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_248 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_249 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Compulsory social security contributions (employer's share) (7)
    report_section_250 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_251 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_252 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Accident insurance
    report_section_253 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_254 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_255 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Commissions
    report_section_256 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_257 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_258 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_259 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Staff travel and representation expenses
    report_section_260 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_261 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_262 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_263 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Custom
    report_section_264 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_265 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_266 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_267 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_268 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Accounting and bookkeeping fees (8)
    report_section_269 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_270 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_271 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_272 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Custom
    report_section_273 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_274 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_275 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_276 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_277 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Custom
    report_section_278 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_279 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_280 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_281 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_282 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Employer's travel and representation expenses
    report_section_283 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_284 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_183 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_184 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Electricity
    report_section_285 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_286 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_287 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_288 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Gas
    report_section_289 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_290 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_291 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_292 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Water
    report_section_293 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_294 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_295 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_296 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Heating
    report_section_297 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_298 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_299 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_300 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Telecommunications
    report_section_301 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_302 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_303 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_304 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # 18a) Renting/leasing of immovable property with application of VAT (8)
    report_section_305 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_306 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_185 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_186 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # 18b) Renting/leasing of immovable property without application of VAT (8)
    report_section_307 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_308 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_309 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # 18c) c) Renting/leasing of permanently installed equipment and machinery
    report_section_310 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_311 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_312 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_313 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Fire insurance
    report_section_314 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_315 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Property tax
    report_section_316 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_317 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Custom
    report_section_318 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_319 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_320 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Custom
    report_section_321 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_322 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_323 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Business tax
    report_section_324 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Licensing (cabaretage) tax and other taxes
    report_section_325 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Interest paid for long-term debts
    report_section_326 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Interest paid for short-term debts
    report_section_327 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Other financial costs
    report_section_328 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_329 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Stock and business equipment insurance
    report_section_330 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Public and professional third party liability insurance
    report_section_331 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Office expenses
    report_section_332 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_333 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Cleaning and maintenance of business premises
    report_section_334 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_335 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Fees and subscriptions paid to professional associations and learned societies
    report_section_336 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Papers and periodicals for business purposes
    report_section_337 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_338 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # 34a) Expenses for work carried out by sub-contractors
    report_section_115 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_187 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # 34b) Expenses for other work carried out by third parties
    report_section_188 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_189 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Shipping and transport expenses
    report_section_343 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_344 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Work clothes
    report_section_345 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_346 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Advertising and publicity
    report_section_347 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_348 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Packaging
    report_section_349 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_350 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Repair and maintenance of equipment and machinery
    report_section_351 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_352 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Other repairs
    report_section_353 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_354 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # New acquisitions (tools and equipment) if their cost can be fully allocated to the year of acquisition or creation pursuant to Article 34 of Income Tax Law
    report_section_355 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_356 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Custom
    report_section_357 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_358 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_359 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Total 'Appendix to Operational expenditures' (brought forward from Operational expenditures) (9)
    report_section_361 = fields.Float(tracking=True, compute='_compute_appendix_total')
    report_section_362 = fields.Float(tracking=True, compute='_compute_appendix_total')
    # Car expenses
    report_section_190 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    report_section_191 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True, readonly=False, store=True, compute="_compute_monthly_totals_breakdown_annex")
    # Assessment total of the taxable amount (10) for non-business use of assets allocated to business (Art.16/a) (to be carried forward to point
    # 1. Motor vehicles
    # a) Values
    # 1) Book (net asset) value at the beginning of the financial year
    report_section_363 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 2) Acquisitions during the financial year
    report_section_364 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 3) Sales during the financial year
    report_section_365 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 4) Depreciation during the financial year (11) (to be carried forward to b)5))
    report_section_366 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 5) Book (net asset) value at the end of the financial year
    report_section_367 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_381 = fields.Float(tracking=True, compute="_compute_new_totals")
    report_section_382 = fields.Float(tracking=True, compute="_compute_new_totals")
    # b) Total of expenses during the financial year
    # 1) Fuel (petrol, diesel) and lubricants
    report_section_368 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_369 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # LPG
    report_section_372 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_373 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 2) Repairs and servicing
    report_section_374 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_375 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 3) Tyres, etc.
    report_section_376 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_377 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 4) Leasing / renting
    report_section_378 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_379 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 5) Depreciation (11) (brought forward from a)4))
    report_section_380 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # c) Number of km travelled during the financial year
    # km travelled
    report_section_383 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # non-business portion (km)
    report_section_384 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # non-business portion (in %)
    report_section_385 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # Non-business part of expenditures for motor vehicules (VAT excluded) (385x381)
    report_section_386 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # Other assets:
    report_section_387 = fields.Char(size=30, states={'exported': [('readonly', True)]}, tracking=True)
    report_section_388 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_389 = fields.Float(tracking=True, compute="_compute_new_totals")
    # C.Supplies carried out within the scope of the special arrangement of art. 56sexies
    # 1. Services supplied by the declaring person himself as a registered taxpayer in Luxembourg
    report_section_106 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 2. Services to be declared and taxed by the registered taxpayer in Luxembourg, which have been supplied by fixed establishments located in other Member States
    report_section_107 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_166 = fields.Float(tracking=True, compute="_compute_new_totals")
    # D. Total entry of stock for business purposes (all amounts VAT excluded) (12)
    # not falling within the scope of Art. 56ter-1 and 56ter-2 of which goods for resale
    report_section_155 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_154 = fields.Float(tracking=True, compute="_compute_new_totals")
    report_section_148 = fields.Float(tracking=True, compute="_compute_new_totals")
    report_section_129 = fields.Float(tracking=True, compute="_compute_new_totals")
    # 1.Purchases of goods (within the territory of Luxembourg or abroad and subsequently brought to Luxembourg) which give rise to a chargeable event for the supplier or for the taxable person acquiring the goods
    # a)Purchases within the country (13)
    # 1) Purchases other than manufactured tobacco rate of
    report_section_771 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_772 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_774 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_773 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_124 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_394 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_128 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_197 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 2) Manufactured tobacco
    report_section_130 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_131 = fields.Float(tracking=True, compute="_compute_new_totals")
    # b)Intra-Community acquisitions
    # 1) Acquisitions other than manufactured tobacco
    # rate of
    report_section_776 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_777 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_778 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_134 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_153 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_136 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_198 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_137 = fields.Float(tracking=True, compute="_compute_new_totals")
    # 2) Manufactured tobacco (15)
    report_section_138 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_139 = fields.Float(tracking=True, compute="_compute_new_totals")
    # c)Imports (16)
    # 1) Imports other than manufactured tobacco
    # rate of
    report_section_781 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_782 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_783 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_142 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_149 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_144 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_199 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_145 = fields.Float(tracking=True, compute="_compute_new_totals")
    # 2) Manufactured tobacco (15)
    report_section_146 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_147 = fields.Float(tracking=True, compute="_compute_new_totals")
    # Purchases of goods (within the territory of Luxembourg or abroad and subsequently brought to Luxembourg) which don't give rise to a chargeable event neither for the supplier nor for the taxable person acquiring the goods
    report_section_150 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # Purchases of goods abroad which are not brought to Luxembourg
    report_section_151 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # E. Stock / Miscellaneous (amounts VAT excluded)
    # 1.Total stock and tobacco
    # a) Stock not falling within the scope of Art. 56ter-1 and 56ter-2 and manufactured tobacco referred to in b) excluded
    # rate of
    report_section_791 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_792 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_793 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_794 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_797 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_798 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_795 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_796 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_158 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_171 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_396 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True) # Custom
    report_section_162 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_175 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_200 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True) # exempt
    report_section_201 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_163 = fields.Float(tracking=True, compute="_compute_new_totals")
    report_section_176 = fields.Float(tracking=True, compute="_compute_new_totals")
    report_section_177 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # 2) goods produced inhouse
    report_section_165 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # which of total under 1.a) is
    # 1) stock for resale
    report_section_164 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_178 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # b) Manufactured tobacco in stock
    report_section_167 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_168 = fields.Float(tracking=True, compute="_compute_new_totals")
    report_section_180 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_181 = fields.Float(tracking=True, compute="_compute_new_totals")
    # Work in progress (VAT excluded)
    report_section_116 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_117 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # Receivables from clients (VAT excluded)
    report_section_118 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_119 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    # Payments made on account by clients (VAT excluded)
    report_section_120 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_121 = fields.Float(states={'exported': [('readonly', True)]}, tracking=True)
    report_section_414 = fields.Float(tracking=True, compute="_compute_appendix")
    report_section_415 = fields.Float(tracking=True, compute="_compute_appendix")
    # ==== Helper fields for views (wrapping fields for cleaner UI) ====
    stock = fields.Boolean(states={'exported': [('readonly', True)]})
    other_purchases = fields.Boolean(states={'exported': [('readonly', True)]})
    other_acquisitions = fields.Boolean(states={'exported': [('readonly', True)]})
    other_imports = fields.Boolean(states={'exported': [('readonly', True)]})

    # ==== Constraints ====
    @api.constrains("company_ids")
    def _check_unique_tax_report(self):
        for record in self:
            domain = [
                ('company_ids', 'in', record.company_ids.ids),
                ('year', '=', record.year)
            ]
            if self.env['l10n_lu.yearly.tax.report.manual'].search_count(domain) > 1:
                raise models.ValidationError(_("Only one tax report data record per year (per company) is allowed!"))

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends(
        "report_section_001", "report_section_002", "report_section_003", "report_section_004", "report_section_005",
        "report_section_007", "report_section_008", "report_section_009", "report_section_010", "report_section_011",
        "report_section_013", "report_section_202", "report_section_077", "report_section_078", "report_section_079",
        "report_section_081", "report_section_082", "report_section_083", "report_section_085", "report_section_086",
        "report_section_087", "report_section_404", "report_section_405", "report_section_406", "report_section_472",
        "report_section_455", "report_section_456", "report_section_457", "report_section_458", "report_section_459",
        "report_section_460", "report_section_461")
    def _compute_totals(self):
        for record in self:
            record.report_section_472_rest = record.report_section_472 - record.report_section_001 - record.report_section_002 - record.report_section_003 - record.report_section_004 - record.report_section_005 - record.report_section_007
            record.report_section_455_rest = record.report_section_455 - record.report_section_008 - record.report_section_009
            record.report_section_456_rest = record.report_section_456 - record.report_section_010 - record.report_section_011
            record.report_section_457_rest = record.report_section_457 - record.report_section_013 - record.report_section_202 - record.report_section_203
            record.report_section_458_rest = record.report_section_458 - record.report_section_077 - record.report_section_081 - record.report_section_085
            record.report_section_459_rest = record.report_section_459 - record.report_section_078 - record.report_section_082 - record.report_section_086
            record.report_section_460_rest = record.report_section_460 - record.report_section_079 - record.report_section_083 - record.report_section_087
            record.report_section_461_rest = record.report_section_461 - record.report_section_404 - record.report_section_405 - record.report_section_406

    @api.depends(
        "report_section_368", "report_section_372", "report_section_374", "report_section_376", "report_section_378",
        "report_section_380", "report_section_369", "report_section_373", "report_section_375", "report_section_377",
        "report_section_379", "report_section_386", "report_section_388", "report_section_106", "report_section_107",
        "report_section_776", "report_section_777", "report_section_778", "report_section_134", "report_section_136",
        "report_section_198", "report_section_138", "report_section_781", "report_section_782", "report_section_783",
        "report_section_142", "report_section_144", "report_section_199", "report_section_146", "report_section_130",
        "report_section_771", "report_section_772", "report_section_774", "report_section_773", "report_section_124",
        "report_section_128", "report_section_197", "report_section_150", "report_section_151", "report_section_791",
        "report_section_793", "report_section_797", "report_section_795", "report_section_158", "report_section_162",
        "report_section_200", "report_section_792", "report_section_794", "report_section_798", "report_section_796",
        "report_section_171", "report_section_175", "report_section_201", "report_section_167", "report_section_180"
    )
    def _compute_new_totals(self):
        for record in self:
            record.report_section_381 = record.report_section_368 + record.report_section_372 + record.report_section_374 + record.report_section_376 + record.report_section_378 + record.report_section_380
            record.report_section_382 = record.report_section_369 + record.report_section_373 + record.report_section_375 + record.report_section_377 + record.report_section_379
            record.report_section_389 = record.report_section_386 + record.report_section_388
            record.report_section_166 = record.report_section_106 + record.report_section_107
            record.report_section_137 = record.report_section_776 + record.report_section_777 + record.report_section_778 + record.report_section_134 + record.report_section_136 + record.report_section_198
            record.report_section_139 = record.report_section_137 + record.report_section_138
            record.report_section_145 = record.report_section_781 + record.report_section_782 + record.report_section_783 + record.report_section_142 + record.report_section_144 + record.report_section_199
            record.report_section_147 = record.report_section_145 + record.report_section_146
            record.report_section_129 = record.report_section_771 + record.report_section_772 + record.report_section_774 + record.report_section_773 + record.report_section_124 + record.report_section_128 + record.report_section_197
            record.report_section_131 = record.report_section_129 + record.report_section_130
            record.report_section_148 = record.report_section_131 + record.report_section_139 + record.report_section_147
            record.report_section_154 = record.report_section_148 + record.report_section_150 + record.report_section_151
            record.report_section_163 = record.report_section_791 + record.report_section_793 + record.report_section_797 + record.report_section_795 + record.report_section_158 + record.report_section_162 + record.report_section_200
            record.report_section_176 = record.report_section_792 + record.report_section_794 + record.report_section_798 + record.report_section_796 + record.report_section_171 + record.report_section_175 + record.report_section_201
            record.report_section_168 = record.report_section_163 + record.report_section_167
            record.report_section_181 = record.report_section_176 + record.report_section_180

    @api.depends(
        "report_section_114", "report_section_246", "report_section_249", "report_section_252", "report_section_255",
        "report_section_258", "report_section_262", "report_section_267", "report_section_271", "report_section_276",
        "report_section_281", "report_section_183", "report_section_287", "report_section_291", "report_section_295",
        "report_section_299", "report_section_303", "report_section_185", "report_section_309", "report_section_312",
        "report_section_315", "report_section_317", "report_section_319", "report_section_322", "report_section_324",
        "report_section_325", "report_section_326", "report_section_327", "report_section_328", "report_section_330",
        "report_section_331", "report_section_332", "report_section_334", "report_section_336", "report_section_337",
        "report_section_115", "report_section_188", "report_section_343", "report_section_345", "report_section_347",
        "report_section_349", "report_section_351", "report_section_353", "report_section_355", "report_section_358",
        "report_section_361", "report_section_190"
    )
    def _compute_192(self):
        for record in self:
            record.report_section_192 = sum([
                record.report_section_114, record.report_section_246, record.report_section_249, record.report_section_252,
                record.report_section_255, record.report_section_258, record.report_section_262, record.report_section_267,
                record.report_section_271, record.report_section_276, record.report_section_281, record.report_section_183,
                record.report_section_287, record.report_section_291, record.report_section_295, record.report_section_299,
                record.report_section_303, record.report_section_185, record.report_section_309, record.report_section_312,
                record.report_section_315, record.report_section_317, record.report_section_319, record.report_section_322,
                record.report_section_324, record.report_section_325, record.report_section_326, record.report_section_327,
                record.report_section_328, record.report_section_330, record.report_section_331, record.report_section_332,
                record.report_section_334, record.report_section_336, record.report_section_337, record.report_section_115,
                record.report_section_188, record.report_section_343, record.report_section_345, record.report_section_347,
                record.report_section_349, record.report_section_351, record.report_section_353, record.report_section_355,
                record.report_section_358, record.report_section_361, record.report_section_190
            ])

    @api.depends(
        "report_section_259", "report_section_263", "report_section_268", "report_section_272", "report_section_277",
        "report_section_282", "report_section_184", "report_section_288", "report_section_292", "report_section_296",
        "report_section_300", "report_section_304", "report_section_186", "report_section_313", "report_section_320",
        "report_section_323", "report_section_329", "report_section_333", "report_section_335", "report_section_338",
        "report_section_187", "report_section_189", "report_section_344", "report_section_346", "report_section_348",
        "report_section_350", "report_section_352", "report_section_354", "report_section_356", "report_section_359",
        "report_section_362", "report_section_191"
    )
    def _compute_193(self):
        for record in self:
            record.report_section_193 = sum([
                record.report_section_259, record.report_section_263, record.report_section_268, record.report_section_272,
                record.report_section_277, record.report_section_282, record.report_section_184, record.report_section_288,
                record.report_section_292, record.report_section_296, record.report_section_300, record.report_section_304,
                record.report_section_186, record.report_section_313, record.report_section_320, record.report_section_323,
                record.report_section_329, record.report_section_333, record.report_section_335, record.report_section_338,
                record.report_section_187, record.report_section_189, record.report_section_344, record.report_section_346,
                record.report_section_348, record.report_section_350, record.report_section_352, record.report_section_354,
                record.report_section_356, record.report_section_359, record.report_section_362, record.report_section_191
            ])

    @api.depends("appendix_ids.report_section_412", "appendix_ids.report_section_413")
    def _compute_appendix(self):
        """
        Computes the total of appendix fields 412 and 413
        report_section_414 is the sum of all entries in column 412
        report_section_415 is the sum of all entries in column 413
        """
        for record in self:
            record.report_section_414 = sum(record.mapped("appendix_ids.report_section_412"))
            record.report_section_415 = sum(record.mapped("appendix_ids.report_section_413"))

    @api.depends("report_section_414", "report_section_415")
    def _compute_appendix_total(self):
        for record in self:
            record.report_section_361 = record.report_section_414
            record.report_section_362 = record.report_section_415

    @api.depends("year", "company_ids")
    def _compute_monthly_totals(self):
        def _set_monthly_totals(record, lines, is_LU=False):
            if is_LU:
                for ln in lines:
                    model, ln_id = report_id._get_model_info_from_id(ln.get('id'))
                    if model == 'account.report.line':
                        line = self.env[model].browse(ln_id)
                        split_line_code = line.code and line.code.split('_')[1]
                        if split_line_code in monthly_totals:
                            record[f'report_section_{split_line_code}'] = ln['columns'][0]['no_format']
            else:
                for mt in monthly_totals:
                    record[f'report_section_{mt}'] += 0

        monthly_totals = {'472', '455', '456', '457', '458', '459', '460', '461'}
        for record in self:
            if record.company_ids:
                report_id = self.env.ref('l10n_lu.tax_report')
                options = report_id.with_context(allowed_company_ids=record.company_ids.ids)._get_options({
                    'date': {
                        'string': self.year,
                        'period_type': 'fiscalyear',
                        'filter': 'custom',
                        'date_from': f'{self.year}-01-01',
                        'date_to': f'{self.year}-12-31',
                        'mode': 'range'
                    },
                })
                if self.env.company.account_fiscal_country_id.code == "LU":
                    lines = report_id._get_lines(options)
                else:
                    lines = self.env.ref('account.generic.tax.report').with_context(allowed_company_ids=record.company_ids.ids)._get_lines(options)
                _set_monthly_totals(record, lines, self.env.company.account_fiscal_country_id.code == "LU")
            else:
                _set_monthly_totals(record, [])

    # Helper for computes
    def _tax_report_get_lines(self):
        """
        Returns the lines of the report grouped by tax > account
        """
        self.ensure_one()
        tax_report = self.env.ref('l10n_lu.tax_report')
        options = tax_report._get_options({
            'date': {
                'string': self.year,
                'period_type': 'fiscalyear',
                'filter': 'custom',
                'date_from': f'{self.year}-01-01',
                'date_to': f'{self.year}-12-31',
                'mode': 'range'
            },
            'tax_report': 'generic_grouped_tax_account',
        })
        report_line_dicts = tax_report._get_lines(options)
        return report_line_dicts

    @api.depends("year", "company_ids")
    def _compute_monthly_totals_breakdown_annex(self):
        monthly_totals_breakdown = {'001', '002', '003', '004', '005', '008', '009', '010', '011', '013',
                                    '202', '203', '077', '081', '085', '078', '082', '086', '079', '083', '087', '404', '405', '406'}

        for record in self:
            for mtb in monthly_totals_breakdown:
                record[f'report_section_{mtb}'] = 0
            report_line_dicts = record._tax_report_get_lines()
            for line in report_line_dicts:
                model, active_id = self.env['account.report']._get_model_info_from_id(line['id'])
                if model == 'account.account':
                    account_code = record.env['account.account'].browse(active_id).code
                    # Match account code ranges with account codes in the report lines
                    # If there is a match, get the corresponding tax code
                    matching = [code for domain, code in YEARLY_FIELDS_MAPPING.items()
                                if int(domain[0]) <= int(account_code) and int(domain[1]) > int(account_code)]
                    for code in matching:
                        # Get the total amount of the tax
                        record[f'report_section_{code}'] += line['columns'][0]['no_format']
            # Add the annex and operational expenditures
            record.appendix_ids = False
            annex_fields = {}
            annex_fields, expenditures_table, _, _ = record.env['l10n_lu.generate.tax.report']._add_annex_fields_expenditures(annex_fields, report_line_dicts, record)
            if expenditures_table:
                record.appendix_ids.create(expenditures_table)
            # Annex totals
            for code, code_value in annex_fields.items():
                record[f'report_section_{code}'] = code_value

    # -------------------------------------------------------------------------
    # ACTION METHODS
    # -------------------------------------------------------------------------
    def action_reset_state(self):
        """
        Sets the XML state back to not exported if a user wants to change the report
        """
        self.ensure_one()
        self.state = 'not_exported'

    def print_xml(self):
        self.ensure_one()
        if self.env.company.account_fiscal_country_id.code != "LU":
            raise UserError(_("The fiscal country of your active company is not Luxembourg. This export is not available for other countries."))
        self.write({'state': 'exported'})
        report = self.env.ref('l10n_lu.tax_report')
        return self.env['l10n_lu.generate.tax.report'].with_context({'report_generation_options': {'report_id':  report.id}}).get_xml(lu_annual_report=self)

    def _lu_get_declarations(self, declaration_template_values):
        """
        Gets the formatted values for LU's tax report.
        Exact format depends on the period (monthly, quarterly, annual(simplified)).
        """
        self.ensure_one()
        options = self.env.ref('l10n_lu.tax_report')._get_options({
            'date': {
                'string': self.year,
                'period_type': 'fiscalyear',
                'filter': 'custom',
                'date_from': f'{self.year}-01-01',
                'date_to': f'{self.year}-12-31',
                'mode': 'range'
            },
            'declaration_type': 'TVA_DECA',
        })
        form = self.env['l10n_lu.tax.report.handler'].get_tax_electronic_report_values(options)['forms'][0]
        form['field_values'] = self.env['l10n_lu.generate.tax.report']._remove_zero_fields(form['field_values'], options['report_id'])
        date_from = fields.Date.from_string(options['date']['date_from'])
        date_to = fields.Date.from_string(options['date']['date_to'])
        self.env['l10n_lu.generate.tax.report']._adapt_to_annual_report(form, date_from, date_to)
        self.env['l10n_lu.generate.tax.report']._adapt_to_full_annual_declaration(form, report_id=self)
        form['model'] = 1
        declaration = {'declaration_singles': {'forms': [form]}, 'declaration_groups': []}
        declaration.update(declaration_template_values)
        return {'declarations': [declaration]}
