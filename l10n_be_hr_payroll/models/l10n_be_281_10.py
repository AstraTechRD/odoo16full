# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import logging
import re

from collections import defaultdict
from datetime import date
from lxml import etree
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.modules.module import get_resource_path

_logger = logging.getLogger(__name__)

# Sources:
# - Technical Doc https://finances.belgium.be/fr/E-services/Belcotaxonweb/documentation-technique
# - "Avis aux débiteurs" https://finances.belgium.be/fr/entreprises/personnel_et_remuneration/avis_aux_debiteurs#q2

COUNTRY_CODES = {
    'BE': '00150',
    'ES': '00109',
    'FR': '00111',
    'GR': '00112',
    'LU': '00113',
    'DE': '00103',
    'RO': '00124',
    'IT': '00128',
    'NL': '00129',
    'TR': '00262',
    'US': '00402',
    'MA': '00354',
}


class L10nBe28110(models.Model):
    _name = 'l10n_be.281_10'
    _description = 'HR Payroll 281.10 Wizard'
    _order = 'reference_year'

    def _get_years(self):
        return [(str(i), i) for i in range(fields.Date.today().year, 2009, -1)]

    @api.model
    def default_get(self, field_list):
        if self.env.company.country_id.code != "BE":
            raise UserError(_('You must be logged in a Belgian company to use this feature'))
        return super().default_get(field_list)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    state = fields.Selection([('generate', 'generate'), ('get', 'get')], default='generate')
    reference_year = fields.Selection(
        selection='_get_years', string='Reference Year', required=True,
        default=lambda x: str(fields.Date.today().year - 1))
    is_test = fields.Boolean(string="Is It a test ?", default=False)
    type_sending = fields.Selection([
        ('0', 'Original send'),
        ('1', 'Send grouped corrections'),
        ], string="Sending Type", default='0', required=True)
    type_treatment = fields.Selection([
        ('0', 'Original'),
        ('1', 'Modification'),
        ('2', 'Add'),
        ('3', 'Cancel'),
        ], string="Treatment Type", default='0', required=True)
    xml_file = fields.Binary('XML File', readonly=True, attachment=False)
    xml_filename = fields.Char()
    xml_validation_state = fields.Selection([
        ('normal', 'N/A'),
        ('done', 'Valid'),
        ('invalid', 'Invalid'),
    ], default='normal', compute='_compute_validation_state', store=True)
    error_message = fields.Char('Error Message', compute='_compute_validation_state', store=True)
    line_ids = fields.One2many(
        'l10n_be.281_10.line', 'sheet_id', compute='_compute_line_ids', store=True, readonly=False)

    @api.depends('xml_file')
    def _compute_validation_state(self):
        xsd_schema_file_path = get_resource_path(
            'l10n_be_hr_payroll',
            'data',
            '161-xsd-2021-20220120.xsd',
        )
        xsd_root = etree.parse(xsd_schema_file_path)
        schema = etree.XMLSchema(xsd_root)

        no_xml_file_records = self.filtered(lambda record: not record.xml_file)
        no_xml_file_records.update({
            'xml_validation_state': 'normal',
            'error_message': False})
        for record in self - no_xml_file_records:
            xml_root = etree.fromstring(base64.b64decode(record.xml_file))
            try:
                schema.assertValid(xml_root)
                record.xml_validation_state = 'done'
            except etree.DocumentInvalid as err:
                record.xml_validation_state = 'invalid'
                record.error_message = str(err)

    def name_get(self):
        return [(
            record.id,
            '%s%s' % (record.reference_year, _('- Test') if record.is_test else '')
        ) for record in self]

    @api.model
    def _check_employees_configuration(self, employees):
        invalid_employees = employees.filtered(lambda e: not (e.company_id and e.company_id.street and e.company_id.zip and e.company_id.city and e.company_id.phone and e.company_id.vat))
        if invalid_employees:
            raise UserError(_("The company is not correctly configured on your employees. Please be sure that the following pieces of information are set: street, zip, city, phone and vat") + '\n' + '\n'.join(invalid_employees.mapped('name')))

        invalid_employees = employees.filtered(
            lambda e: not e.address_home_id or not e.address_home_id.street or not e.address_home_id.zip or not e.address_home_id.city or not e.address_home_id.country_id)
        if invalid_employees:
            raise UserError(_("The following employees don't have a valid private address (with a street, a zip, a city and a country):\n%s", '\n'.join(invalid_employees.mapped('name'))))

        if not all(emp.contract_ids and emp.contract_id for emp in employees):
            raise UserError(_('Some employee has no contract.'))

        invalid_employees = employees.filtered(lambda e: not e._is_niss_valid())
        if invalid_employees:
            raise UserError(_('Invalid NISS number for those employees:\n %s', '\n'.join(invalid_employees.mapped('name'))))

        invalid_country_codes = employees.address_home_id.country_id.filtered(lambda c: c.code not in COUNTRY_CODES)
        if invalid_country_codes:
            raise UserError(_('Unsupported country code %s. Please contact an administrator.', ', '.join(invalid_country_codes.mapped('code'))))

    @api.model
    def _get_lang_code(self, lang):
        if lang == 'nl_NL':
            return 1
        elif lang == 'fr_FR':
            return 2
        elif lang == 'de_DE':
            return 3
        return 2

    @api.model
    def _get_country_code(self, country):
        return COUNTRY_CODES[country.code]

    @api.model
    def _get_atn_nature(self, payslips):
        result = ''
        if any(payslip.vehicle_id or payslip.contract_id.car_id for payslip in payslips):
            result += 'F'
        if any(payslip.contract_id.has_laptop for payslip in payslips):
            result += 'H'
        if any(payslip.contract_id.internet for payslip in payslips):
            result += 'I'
        if any(payslip.contract_id.mobile for payslip in payslips):
            result += 'K'
        return result

    @api.depends('reference_year', 'company_id')
    def _compute_line_ids(self):
        for sheet in self:
            all_payslips = self.env['hr.payslip'].search([
                ('date_to', '<=', date(int(sheet.reference_year), 12, 31)),
                ('date_from', '>=', date(int(sheet.reference_year), 1, 1)),
                ('state', 'in', ['done', 'paid']),
                ('company_id', '=', sheet.company_id.id),
            ])
            all_employees = all_payslips.mapped('employee_id')
            sheet.write({
                'line_ids': [(5, 0, 0)] + [(0, 0, {
                    'employee_id': employee.id,
                }) for employee in all_employees]
            })

    def _get_rendering_data(self, employees):
        # Round to eurocent for XML file, not PDF
        no_round = self.env.context.get('no_round_281_10')

        def _to_eurocent(amount):
            return amount if no_round else int(amount * 100)

        if not self.company_id.vat or not self.company_id.zip:
            raise UserError(_('The VAT or the ZIP number is not specified on your company'))
        bce_number = self.company_id.vat.replace('BE', '')

        if not self.company_id.phone:
            raise UserError(_('The phone number is not specified on your company'))
        phone = self.company_id.phone.strip().replace(' ', '')
        if len(phone) > 12:
            raise UserError(_("The company phone number shouldn't exceed 12 characters"))

        main_data = {
            'v0002_inkomstenjaar': self.reference_year,
            'v0010_bestandtype': 'BELCOTST' if self.is_test else 'BELCOTAX',
            'v0011_aanmaakdatum': fields.Date.today().strftime('%d-%m-%Y'),
            'v0014_naam': self.company_id.name,
            'v0015_adres': self.company_id.street,
            'v0016_postcode': self.company_id.zip,
            'v0017_gemeente': self.company_id.city,
            'v0018_telefoonnummer': phone,
            'v0021_contactpersoon': self.env.user.name,
            'v0022_taalcode': self._get_lang_code(self.env.user.employee_id.address_home_id.lang),
            'v0023_emailadres': self.env.user.email,
            'v0024_nationaalnr': bce_number,
            'v0025_typeenvoi': self.type_sending,
            'a1002_inkomstenjaar': self.reference_year,
            'a1005_registratienummer': bce_number,
            'a1011_naamnl1': self.company_id.name,
            'a1013_adresnl': self.company_id.street,
            'a1014_postcodebelgisch': self.company_id.zip.strip(),
            'a1015_gemeente': self.company_id.city,
            'a1016_landwoonplaats': self._get_country_code(self.company_id.country_id),
            'a1020_taalcode': 1,
        }

        employees_data = []

        all_payslips = self.env['hr.payslip'].search([
            ('date_to', '<=', date(int(self.reference_year), 12, 31)),
            ('date_from', '>=', date(int(self.reference_year), 1, 1)),
            ('state', 'in', ['done', 'paid']),
            ('employee_id', 'in', employees.ids)
        ])
        all_employees = all_payslips.mapped('employee_id')
        self._check_employees_configuration(all_employees)

        employee_payslips = defaultdict(lambda: self.env['hr.payslip'])
        for payslip in all_payslips:
            employee_payslips[payslip.employee_id] |= payslip

        line_codes = [
            'NET', 'PAY_SIMPLE', 'PPTOTAL', 'M.ONSS', 'ATN.INT', 'ATN.MOB', 'ATN.LAP', 'CYCLE',
            'ATN.CAR', 'REP.FEES', 'REP.FEES.VOLATILE', 'PUB.TRANS', 'CAR.PRIV', 'EmpBonus.1', 'GROSS',
            'DOUBLE.DECEMBER.GROSS', 'DOUBLE.DECEMBER.P.P',
        ]
        all_line_values = all_payslips._get_line_values(line_codes, vals_list=['total', 'quantity'])

        belgium = self.env.ref('base.be')
        sequence = 0

        warrant_structure = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_structure_warrant')
        holiday_n_structure = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n_holidays')
        holiday_n1_structure = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_departure_n1_holidays')
        termination_fees_structure = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_termination_fees')

        for employee in employee_payslips:
            is_belgium = employee.address_home_id.country_id == belgium
            payslips = employee_payslips[employee]
            sequence += 1

            mapped_total = {
                code: sum(all_line_values[code][p.id]['total'] for p in payslips)
                for code in line_codes}

            total_gross = mapped_total['GROSS'] + mapped_total['DOUBLE.DECEMBER.GROSS']
            warrant_gross = sum(all_line_values['GROSS'][p.id]['total'] for p in payslips if p.struct_id == warrant_structure)
            holiday_gross = sum(all_line_values['GROSS'][p.id]['total'] for p in payslips if p.struct_id in holiday_n_structure + holiday_n1_structure)
            termination_gross = sum(all_line_values['GROSS'][p.id]['total'] for p in payslips if p.struct_id == termination_fees_structure)
            common_gross = total_gross - warrant_gross - holiday_gross - termination_gross

            postcode = employee.address_home_id.zip.strip() if is_belgium else '0'
            if len(postcode) > 4 or not postcode.isdecimal():
                raise UserError(_("The belgian postcode length shouldn't exceed 4 characters and should contain only numbers for employee %s", employee.name))

            names = re.sub(r"\([^()]*\)", "", employee.name).strip().split()
            first_name = names[-1]
            last_name = ' '.join(names[:-1])
            if len(first_name) > 30:
                raise UserError(_("The employee first name shouldn't exceed 30 characters for employee %s", employee.name))

            first_contract_date = employee.with_context(
                before_date=date(int(self.reference_year), 12, 31))._get_first_contract_date()
            if not first_contract_date:
                raise UserError(_("No first contract date found for employee %s", employee.name))

            # 2021: Only private car
            # from 2022: private car / company car (from May)
            max_other_transport_exemption = payslip.env['hr.rule.parameter']._get_parameter_from_code(
                'pricate_car_taxable_threshold',
                date=date(int(self.reference_year), 1, 1))
            start = first_contract_date
            end = date(int(self.reference_year), 12, 31)
            number_of_month = (end.year - start.year) * 12 + (end.month - start.month) + 1
            number_of_month = min(12, number_of_month)
            other_transport_exemption = 0
            has_company_car = bool(round(mapped_total['ATN.CAR'], 2))
            has_private_car = bool(round(mapped_total['CAR.PRIV'], 2)) and not has_company_car
            if round(mapped_total['CAR.PRIV'], 2) + round(mapped_total['ATN.CAR'], 2):
                other_transport_exemption = max_other_transport_exemption * number_of_month / 12.0

            cycle_days_count = sum(all_line_values['CYCLE'][p.id]['quantity'] for p in payslips)
            cycle_days_amount = sum(all_line_values['CYCLE'][p.id]['total'] for p in payslips)

            sheet_values = {
                'employee': employee,
                'employee_id': employee.id,
                'f2002_inkomstenjaar': self.reference_year,
                'f2005_registratienummer': bce_number,
                'f2008_typefiche': '28110',
                'f2009_volgnummer': sequence,
                'f2011_nationaalnr': employee.niss,
                'f2013_naam': last_name,
                'f2015_adres': employee.address_home_id.street,
                'f2016_postcodebelgisch': postcode,
                'employee_city': employee.address_home_id.city,
                'f2018_landwoonplaats': '150' if is_belgium else self._get_country_code(employee.address_home_id.country_id),
                'f2027_taalcode': self._get_lang_code(employee.address_home_id.lang),
                'f2028_typetraitement': self.type_treatment,
                'f2029_enkelopgave325': 0,
                'f2112_buitenlandspostnummer': employee.address_home_id.zip if not is_belgium else '0',
                'f2114_voornamen': first_name,
                # YTI From 2023, should be distinguished from volatile representation fees
                # 'f10_2031_compensationwithstandards': round(mapped_total['REP.FEES'], 2),
                'f10_2031_compensationwithstandards': 0,
                'f10_2033_compensationwithdocuments': 0,
                'f10_2034_ex': 0,
                'f10_2035_verantwoordingsstukken': 0,
                'f10_2036_inwonersdeenfr': 0,
                'f10_2037_vergoedingkosten': 0,
                'f10_2038_seasonalworker': 0,
                'f10_2039_optiebuitvennoots': '0',
                'f10_2040_individualconvention': 0,
                'f10_2041_overheidspersoneel': 0,
                'f10_2042_sailorcode': 0,
                'f10_2045_code': 0,
                # 'f10_2055_datumvanindienstt': employee.first_contract_date.strftime('%d/%m/%Y') if employee.first_contract_date.year == self.reference_year else '',
                'f10_2055_datumvanindienstt': first_contract_date.strftime('%d-%m-%Y') if first_contract_date else '',
                'f10_2056_datumvanvertrek': employee.end_notice_period.strftime('%d-%m-%Y') if employee.end_notice_period else '',
                'f10_2058_km': cycle_days_count * employee.km_home_work,
                # f10_2059_totaalcontrole
                'f10_2060_gewonebezoldiginge': _to_eurocent(round(common_gross, 2)),
                'f10_2061_bedragoveruren300horeca': 0,
                # f10_2062_totaal
                'f10_2063_vervroegdvakantieg': _to_eurocent(round(holiday_gross, 2)),
                'f10_2064_afzbelachterstall': 0,
                'f10_2065_opzeggingsreclasseringsverg': _to_eurocent(round(termination_gross, 2)),
                'f10_2066_impulsfund': 0,
                'f10_2067_rechtvermindering66_81': 0,
                'f10_2068_rechtvermindering57_75': 0,
                'f10_2069_fidelitystamps': 0,
                'f10_2070_decemberremuneration': 0,
                'f10_2071_totalevergoeding': cycle_days_amount,
                'f10_2072_pensioentoezetting':  0,
                'f10_2073_tipamount': 0,
                'f10_2074_bedrijfsvoorheffing': _to_eurocent(round(mapped_total['PPTOTAL'] - mapped_total['DOUBLE.DECEMBER.P.P'], 2)),  # 2.074 = 2.131 + 2.133. YTI Is it ok to include PROF_TAX / should include Double holidays?
                'f10_2075_bijzonderbijdrage': _to_eurocent(round(-mapped_total['M.ONSS'], 2)),
                'f10_2076_voordelenaardbedrag': _to_eurocent(
                    max(
                        0,
                        round(sum(mapped_total[code] for code in ['ATN.INT', 'ATN.MOB', 'ATN.LAP', 'ATN.CAR']) - other_transport_exemption, 2) if has_company_car else round(sum(mapped_total[code] for code in ['ATN.INT', 'ATN.MOB', 'ATN.LAP', 'ATN.CAR']), 2))),
                # f10_2077_totaal
                # YTI From 2023, should be distinguished from REP.FEES
                # 'f10_2078_compensationamountwithoutstandards': round(mapped_total['REP.FEES.VOLATILE'], 2),
                'f10_2078_compensationamountwithoutstandards': _to_eurocent(round(mapped_total['REP.FEES'], 2)),
                'f10_2080_detacheringsvergoed': 0,
                'f10_2081_gewonebijdragenenpremies': 0,
                'f10_2082_bedrag': _to_eurocent(round(warrant_gross, 2)),
                'f10_2083_bedrag': 0,
                'f10_2084_mobiliteitsvergoedi': 0,
                'f10_2085_forfbezoldiging': 0,
                'f10_2086_openbaargemeenschap': _to_eurocent(round(mapped_total['PUB.TRANS'], 2)),
                'f10_2087_bedrag': 0,
                'f10_2088_andervervoermiddel': _to_eurocent(round(mapped_total['CAR.PRIV'], 2) if has_private_car else round(other_transport_exemption, 2)),
                'f10_2090_outborderdays': 0,
                'f10_2092_othercode1': 0,
                'f10_2094_othercode2': 0,
                'f10_2095_aantaluren': 0,
                'f10_2096_othercode3': 0,
                'f10_2097_aantaluren': 0,
                'f10_2098_othercode4': 0,
                'f10_2099_aard': self._get_atn_nature(payslips),
                'f10_2102_kas': 0,
                'f10_2103_kasvrijaanvullendpensioen': 0,
                'f10_2106_percentages': '', # Note: No percentages for warrants
                'f10_2109_fiscaalidentificat': '', # Use NISS instead
                'f10_2110_aantaloveruren360': 0,
                'f10_2111_achterstalloveruren300horeca': 0,
                'f10_2113_forfaitrsz': 0,
                'f10_2115_bonus': _to_eurocent(round(mapped_total['EmpBonus.1'], 2)),
                'f10_2116_badweatherstamps': 0,
                'f10_2117_nonrecurrentadvantages': 0,
                'f10_2118_amountovertime180secondsemester': 0,
                'f10_2119_sportremuneration': 0,
                'f10_2120_sportvacancysavings': 0,
                'f10_2121_sportoutdated': 0,
                'f10_2122_sportindemnificationofretraction': 0,
                'f10_2123_managerremuneration': 0,
                'f10_2124_managervacancysavings': 0,
                'f10_2125_manageroutdated': 0,
                'f10_2126_managerindemnificationofretraction': 0,
                'f10_2127_nonrecurrentadvantagesoutdated': 0,
                'f10_2128_vrijaanvullendpensioenwerknemers': 0,
                'f10_2130_privatepc': 0,
                'f10_2131_bedrijfsvoorheffingvanwerkgever': _to_eurocent(round(mapped_total['PPTOTAL'] - mapped_total['DOUBLE.DECEMBER.P.P'], 2)),
                'f10_2132_amountovertime180firstsemester': 0,
                'f10_2133_bedrijfsvoorheffingbuitenlvenverbondenwerkgever': 0,
                'f10_2134_totaalbedragmobiliteitsbudget': 0,
                'f10_2135_amountpaidforvolontarysuplementaryhourscovid': 0,
                'f10_2136_amountcontractofstudent': 0,
                'f10_2137_amountstudent2020oruntilthirdquarter2021': 0,
                'f10_2138_chequesofconsumptions': 0,
                'f10_2141_occasionalworkhoreca': 0,
                'f10_2142_aantaloveruren180': 0,
                'f10_2143_bedragoveruren360horeca': 0,
                'f10_2165_achterstalloveruren360horeca': 0,
                'f10_2166_flexi_job': 0,
                'f10_2167_aantaloveruren300horeca': 0,
                'f10_2168_achterstallaantaloveruren300horeca': 0,
                'f10_2169_aantaloveruren360horeca': 0,
                'f10_2170_achterstallaantaloveruren360horeca': 0,
                'f10_2177_winstpremies': 0,
                'f10_2179_startersjob': 0,
                'f10_2180_onkostenbrandweerenambulanciers': 0,
                'f10_2181_remunerationetrang': 0,
                'f10_2182_aandelenetrang': 0,
                'f10_2183_bonuspremieoaandelenoptiesetrang': 0,
                'f10_2184_anderevaaetrang': 0,
                'f10_2185_amountother1': 0,
                'f10_2186_amountother2': 0,
                'f10_2187_amountother3': 0,
                'f10_2188_amountother4': 0,
                'f10_2190_covidovertimeremunerationfirstsemester': 0,
                'f10_2191_covidovertimeremunerationsecondsemester': 0,
                'f10_2192_covidovertimehoursfirstsemester': 0,
                'f10_2193_covidovertimehourssecondsemester': 0,
                'f10_2194_covidovertimehourstotal': 0,
                'f10_2195_covidovertimehours2020': 0,
                'f10_2196_covidovertimeremuneration2020': 0,
                'f10_2198_coronabonus': 0,
            }
            # Le code postal belge (2016) et le code postal étranger (2112) ne peuvent être
            # ni remplis, ni vides tous les deux.
            if is_belgium:
                sheet_values.pop('f2112_buitenlandspostnummer')
            else:
                sheet_values.pop('f2016_postcodebelgisch')

            # Somme de 2.060 + 2.076 + 2069 + 2.082 + 2.083
            sheet_values['f10_2062_totaal'] = sum(sheet_values[code] for code in [
                'f10_2060_gewonebezoldiginge',
                'f10_2076_voordelenaardbedrag',
                'f10_2069_fidelitystamps',
                'f10_2082_bedrag',
                'f10_2083_bedrag'])

            # Somme de 2.086 + 2.087 + 2.088
            sheet_values['f10_2077_totaal'] = sum(sheet_values[code] for code in [
                'f10_2086_openbaargemeenschap',
                'f10_2087_bedrag',
                'f10_2088_andervervoermiddel'])

            # Somme de 2060 à 2088, f10_2062_totaal et f10_2077_totaal inclus
            sheet_values['f10_2059_totaalcontrole'] = sum(sheet_values[code] for code in [
                'f10_2060_gewonebezoldiginge',
                'f10_2061_bedragoveruren300horeca',
                'f10_2062_totaal',
                'f10_2063_vervroegdvakantieg',
                'f10_2064_afzbelachterstall',
                'f10_2065_opzeggingsreclasseringsverg',
                'f10_2066_impulsfund',
                'f10_2067_rechtvermindering66_81',
                'f10_2068_rechtvermindering57_75',
                'f10_2069_fidelitystamps',
                'f10_2070_decemberremuneration',
                'f10_2071_totalevergoeding',
                'f10_2072_pensioentoezetting',
                'f10_2073_tipamount',
                'f10_2074_bedrijfsvoorheffing',
                'f10_2075_bijzonderbijdrage',
                'f10_2076_voordelenaardbedrag',
                'f10_2077_totaal',
                'f10_2078_compensationamountwithoutstandards',
                'f10_2080_detacheringsvergoed',
                'f10_2081_gewonebijdragenenpremies',
                'f10_2082_bedrag',
                'f10_2083_bedrag',
                'f10_2084_mobiliteitsvergoedi',
                'f10_2085_forfbezoldiging',
                'f10_2086_openbaargemeenschap',
                'f10_2087_bedrag',
                'f10_2088_andervervoermiddel'])

            employees_data.append(sheet_values)

        sheets_count = len(employees_data)


        sum_2009 = sum(sheet_values['f2009_volgnummer'] for sheet_values in employees_data)
        sum_2059 = sum(sheet_values['f10_2059_totaalcontrole'] for sheet_values in employees_data)
        sum_2074 = sum(sheet_values['f10_2074_bedrijfsvoorheffing'] for sheet_values in employees_data)
        total_data = {
            'r8002_inkomstenjaar': self.reference_year,
            'r8005_registratienummer': bce_number,
            # Le champ "Nombre total d'enregistrements" (8010) doit être égal au nombre
            # d'enregistrements  contenus dans cette déclaration (total des enregistrements
            # de type 2 (fiches) + enregistrement 1 et 8)
            'r8010_aantalrecords': sheets_count + 2,
            'r8011_controletotaal': sum_2009,
            'r8012_controletotaal': sum_2059,
            'r8013_totaalvoorheffingen': sum_2074,
            'r9002_inkomstenjaar': self.reference_year,
            # Le champ "Nombre de déclarations" doit être égal au nombre de déclarations
            # contenues dans l'envoi + 2.
            'r9010_aantallogbestanden': 3,
            # Le champ "Nombre de fiches" doit être égal au nombre d'enregistrements contenus
            # dans cet envoi  (total des enregistrements de type 2 (fiches) + total des
            # enregistrements 1 et 8 (début et fin débiteurs) + enregistrements 0 et 9 (début et fin d'envoi)).
            'r9011_totaalaantalrecords': sheets_count + 4,
            'r9012_controletotaal': sum_2009,
            'r9013_controletotaal': sum_2059,
            'r9014_controletotaal': sum_2074,
        }

        return {'data': main_data, 'employees_data': employees_data, 'total_data': total_data}

    def action_generate_pdf(self):
        self.line_ids.write({'pdf_to_generate': True})
        self.env.ref('hr_payroll.ir_cron_generate_payslip_pdfs')._trigger()

    def _process_files(self, files):
        self.ensure_one()
        for employee, filename, data in files:
            line = self.line_ids.filtered(lambda l: l.employee_id == employee)
            line.write({
                'pdf_file': base64.encodebytes(data),
                'pdf_filename': filename,
            })

    def action_generate_xml(self):
        self.ensure_one()
        self.xml_filename = '%s-281_10_report.xml' % (self.reference_year)
        xml_str = self.env['ir.qweb']._render('l10n_be_hr_payroll.281_10_xml_report', self._get_rendering_data(self.line_ids.employee_id))

        # Prettify xml string
        root = etree.fromstring(xml_str, parser=etree.XMLParser(remove_blank_text=True))
        xml_formatted_str = etree.tostring(root, pretty_print=True, encoding='utf-8', xml_declaration=True)

        self.xml_file = base64.encodebytes(xml_formatted_str)
        self.state = 'get'


class L10nBe28110Line(models.Model):
    _name = 'l10n_be.281_10.line'
    _description = 'HR Payroll 281.10 Line Wizard'

    employee_id = fields.Many2one('hr.employee')
    pdf_file = fields.Binary('PDF File', readonly=True, attachment=False)
    pdf_filename = fields.Char()
    sheet_id = fields.Many2one('l10n_be.281_10')
    pdf_to_generate = fields.Boolean()

    def _generate_pdf(self):
        report_sudo = self.env["ir.actions.report"].sudo()
        report_id = self.env.ref('l10n_be_hr_payroll.action_report_employee_281_10').id

        for sheet in self.sheet_id:
            lines = self.filtered(lambda l: l.sheet_id == sheet)
            rendering_data = sheet.with_context(no_round_281_10=True)._get_rendering_data(lines.employee_id)
            for sheet_values in rendering_data['employees_data']:
                for key, value in sheet_values.items():
                    if isinstance(value, int) and value == 0:
                        sheet_values[key] = '0.00 €'
                    elif isinstance(value, float):
                        sheet_values[key] = '{:,.2f} €'.format(value)
                    elif not value:
                        sheet_values[key] = _('None')

            pdf_files = []
            sheet_count = len(rendering_data['employees_data'])
            counter = 1
            for sheet_data in rendering_data['employees_data']:
                _logger.info('Printing 281.10 sheet (%s/%s)', counter, sheet_count)
                counter += 1
                sheet_filename = '%s-%s-281_10' % (sheet_data['f2002_inkomstenjaar'], sheet_data['f2013_naam'])
                employee_lang = sheet_data['employee'].sudo().address_home_id.lang
                sheet_file, dummy = report_sudo.with_context(lang=employee_lang, allowed_company_ids=sheet_data['employee'].company_id.ids)._render_qweb_pdf(
                    report_id, [sheet_data['employee_id']], data={**sheet_data, **rendering_data['data']})
                pdf_files.append((sheet_data['employee'], sheet_filename, sheet_file))

            if pdf_files:
                sheet._process_files(pdf_files)
