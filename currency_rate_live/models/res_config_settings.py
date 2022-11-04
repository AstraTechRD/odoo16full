# -*- coding: utf-8 -*-

import datetime
from lxml import etree
from dateutil.relativedelta import relativedelta
import re
import logging
from pytz import timezone

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

BANXICO_DATE_FORMAT = '%d/%m/%Y'
CBUAE_URL = "https://centralbank.ae/umbraco/Surface/Exchange/GetExchangeRateAllCurrency"
CBEGY_URL = "https://www.cbe.org.eg/en/EconomicResearch/Statistics/Pages/OfficialRatesListing.aspx"
MAP_CURRENCIES = {
    'US Dollar': 'USD',
    'UAE Dirham': 'AED',
    'Argentine Peso': 'ARS',
    'Australian Dollar': 'AUD',
    'Bangladesh Taka': 'BDT',
    'Bahrani Dinar': 'BHD',
    'Bahraini Dinar': 'BHD',
    'Brunei Dollar': 'BND',
    'Brazilian Real': 'BRL',
    'Botswana Pula': 'BWP',
    'Belarus Rouble': 'BYN',
    'Canadian Dollar': 'CAD',
    'Swiss Franc': 'CHF',
    'Chilean Peso': 'CLP',
    'Chinese Yuan - Offshore': 'CNY',
    'Chinese Yuan': 'CNY',
    'Colombian Peso': 'COP',
    'Czech Koruna': 'CZK',
    'Danish Krone': 'DKK',
    'Algerian Dinar': 'DZD',
    'Egypt Pound': 'EGP',
    'Euro': 'EUR',
    'GB Pound': 'GBP',
    'Pound Sterling': 'GBP',
    'Hongkong Dollar': 'HKD',
    'Hungarian Forint': 'HUF',
    'Indonesia Rupiah': 'IDR',
    'Indian Rupee': 'INR',
    'Iceland Krona': 'ISK',
    'Jordan Dinar': 'JOD',
    'Jordanian Dinar': 'JOD',
    'Japanese Yen': 'JPY',
    'Japanese Yen 100': 'JPY',
    'Kenya Shilling': 'KES',
    'Korean Won': 'KRW',
    'Kuwaiti Dinar': 'KWD',
    'Kazakhstan Tenge': 'KZT',
    'Lebanon Pound': 'LBP',
    'Sri Lanka Rupee': 'LKR',
    'Moroccan Dirham': 'MAD',
    'Macedonia Denar': 'MKD',
    'Mexican Peso': 'MXN',
    'Malaysia Ringgit': 'MYR',
    'Nigerian Naira': 'NGN',
    'Norwegian Krone': 'NOK',
    'NewZealand Dollar': 'NZD',
    'Omani Rial': 'OMR',
    'Omani Riyal': 'OMR',
    'Peru Sol': 'PEN',
    'Philippine Piso': 'PHP',
    'Pakistan Rupee': 'PKR',
    'Polish Zloty': 'PLN',
    'Qatari Riyal': 'QAR',
    'Serbian Dinar': 'RSD',
    'Russia Rouble': 'RUB',
    'Saudi Riyal': 'SAR',
    'Swedish Krona': 'SWK',
    'Singapore Dollar': 'SGD',
    'Thai Baht': 'THB',
    'Tunisian Dinar': 'TND',
    'Turkish Lira': 'TRY',
    'Trin Tob Dollar': 'TTD',
    'Taiwan Dollar': 'TWD',
    'Tanzania Shilling': 'TZS',
    'Uganda Shilling': 'UGX',
    'Vietnam Dong': 'VND',
    'South Africa Rand': 'ZAR',
    'Zambian Kwacha': 'ZMW',
    'دولار امريكي': 'USD',
    'بيسو ارجنتيني': 'ARS',
    'دولار استرالي': 'AUD',
    'تاكا بنغلاديشية': 'BDT',
    'دينار بحريني': 'BHD',
    'دولار بروناي': 'BND',
    'ريال برازيلي': 'BRL',
    'بولا بوتسواني': 'BWP',
    'روبل بلاروسي': 'BYN',
    'دولار كندي': 'CAD',
    'فرنك سويسري': 'CHF',
    'بيزو تشيلي': 'CLP',
    'يوان صيني - الخارج': 'CNY',
    'يوان صيني': 'CNY',
    'بيزو كولومبي': 'COP',
    'كرونة تشيكية': 'CZK',
    'كرون دانماركي': 'DKK',
    'دينار جزائري': 'DZD',
    'جينيه مصري': 'EGP',
    'يورو': 'EUR',
    'جنيه استرليني': 'GBP',
    'دولار هونج كونج': 'HKD',
    'فورنت هنغاري': 'HUF',
    'روبية اندونيسية': 'IDR',
    'روبية هندية': 'INR',
    'كرونة آيسلندية': 'ISK',
    'دينار أردني': 'JOD',
    'ين ياباني': 'JPY',
    'شلن كيني': 'KES',
    'ون كوري': 'KRW',
    'دينار كويتي': 'KWD',
    'تينغ كازاخستاني': 'KZT',
    'ليرة لبنانية': 'LBP',
    'روبية سريلانكي': 'LKR',
    'درهم مغربي': 'MAD',
    'دينار مقدوني': 'MKD',
    'بيسو مكسيكي': 'MXN',
    'رينغيت ماليزي': 'MYR',
    'نيرا نيجيري': 'NGN',
    'كرون نرويجي': 'NOK',
    'دولار نيوزيلندي': 'NZD',
    'ريال عماني': 'OMR',
    'سول بيروفي': 'PEN',
    'بيسو فلبيني': 'PHP',
    'روبية باكستانية': 'PKR',
    'زلوتي بولندي': 'PLN',
    'ريال قطري': 'QAR',
    'دينار صربي': 'RSD',
    'روبل روسي': 'RUB',
    'ريال سعودي': 'SAR',
    'كرونة سويدية': 'SWK',
    'دولار سنغافوري': 'SGD',
    'بات تايلندي': 'THB',
    'دينار تونسي': 'TND',
    'ليرة تركية': 'TRY',
    'دولار تريندادي': 'TTD',
    'دولار تايواني': 'TWD',
    'شلن تنزاني': 'TZS',
    'شلن اوغندي': 'UGX',
    'دونغ فيتنامي': 'VND',
    'راند جنوب أفريقي': 'ZAR',
    'كواشا زامبي': 'ZMW',
}

_logger = logging.getLogger(__name__)


def xml2json_from_elementtree(el, preserve_whitespaces=False):
    """ xml2json-direct
    Simple and straightforward XML-to-JSON converter in Python
    New BSD Licensed
    http://code.google.com/p/xml2json-direct/
    """
    res = {}
    if el.tag[0] == "{":
        ns, name = el.tag.rsplit("}", 1)
        res["tag"] = name
        res["namespace"] = ns[1:]
    else:
        res["tag"] = el.tag
    res["attrs"] = {}
    for k, v in el.items():
        res["attrs"][k] = v
    kids = []
    if el.text and (preserve_whitespaces or el.text.strip() != ''):
        kids.append(el.text)
    for kid in el:
        kids.append(xml2json_from_elementtree(kid, preserve_whitespaces))
        if kid.tail and (preserve_whitespaces or kid.tail.strip() != ''):
            kids.append(kid.tail)
    res["children"] = kids
    return res


# countries, provider_code, description
CURRENCY_PROVIDER_SELECTION = [
    ([], 'ecb', 'European Central Bank'),
    ([], 'xe_com', 'xe.com'),
    (['AE'], 'cbuae', 'UAE Central Bank'),
    (['CA'], 'boc', 'Bank Of Canada'),
    (['CH'], 'fta', 'Federal Tax Administration (Switzerland)'),
    (['CL'], 'mindicador', 'Chilean mindicador.cl'),
    (['EG'], 'cbegy', 'Central Bank of Egypt'),
    (['MX'], 'banxico', 'Mexican Bank'),
    (['PE'], 'bcrp', 'Bank of Peru'),
    (['RO'], 'bnr', 'National Bank Of Romania'),
    (['TR'], 'tcmb', 'Turkey Republic Central Bank'),
]

class ResCompany(models.Model):
    _inherit = 'res.company'

    currency_interval_unit = fields.Selection(
        selection=[
            ('manually', 'Manually'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly')
        ],
        default='manually',
        required=True,
        string='Interval Unit',
    )
    currency_next_execution_date = fields.Date(string="Next Execution Date")
    currency_provider = fields.Selection(
        selection=[(provider_code, desc) for dummy, provider_code, desc in CURRENCY_PROVIDER_SELECTION],
        string='Service Provider',
        compute='_compute_currency_provider',
        readonly=False,
        store=True,
    )

    @api.depends('country_id')
    def _compute_currency_provider(self):
        code_providers = {
            country: provider_code
            for countries, provider_code, dummy in CURRENCY_PROVIDER_SELECTION
            for country in countries
        }
        for record in self:
            record.currency_provider = code_providers.get(record.country_id.code, 'ecb')

    def update_currency_rates(self):
        ''' This method is used to update all currencies given by the provider.
        It calls the parse_function of the selected exchange rates provider automatically.

        For this, all those functions must be called _parse_xxx_data, where xxx
        is the technical name of the provider in the selection field. Each of them
        must also be such as:
            - It takes as its only parameter the recordset of the currencies
              we want to get the rates of
            - It returns a dictionary containing currency codes as keys, and
              the corresponding exchange rates as its values. These rates must all
              be based on the same currency, whatever it is. This dictionary must
              also include a rate for the base currencies of the companies we are
              updating rates from, otherwise this will result in an error
              asking the user to choose another provider.

        :return: True if the rates of all the records in self were updated
                 successfully, False if at least one wasn't.
        '''
        active_currencies = self.env['res.currency'].search([])
        rslt = True
        for (currency_provider, companies) in self._group_by_provider().items():
            parse_function = getattr(companies, '_parse_' + currency_provider + '_data')
            try:
                parse_results = parse_function(active_currencies)
                companies._generate_currency_rates(parse_results)
            except Exception:
                rslt = False
                _logger.exception('Unable to connect to the online exchange rate platform %s. The web service may be temporary down.', currency_provider)
        return rslt

    def _group_by_provider(self):
        """ Returns a dictionnary grouping the companies in self by currency
        rate provider. Companies with no provider defined will be ignored."""
        rslt = {}
        for company in self:
            if not company.currency_provider:
                continue

            if rslt.get(company.currency_provider):
                rslt[company.currency_provider] += company
            else:
                rslt[company.currency_provider] = company
        return rslt

    def _generate_currency_rates(self, parsed_data):
        """ Generate the currency rate entries for each of the companies, using the
        result of a parsing function, given as parameter, to get the rates data.

        This function ensures the currency rates of each company are computed,
        based on parsed_data, so that the currency of this company receives rate=1.
        This is done so because a lot of users find it convenient to have the
        exchange rate of their main currency equal to one in Odoo.
        """
        Currency = self.env['res.currency']
        CurrencyRate = self.env['res.currency.rate']

        for company in self:
            rate_info = parsed_data.get(company.currency_id.name, None)

            if not rate_info:
                raise UserError(_("Your main currency (%s) is not supported by this exchange rate provider. Please choose another one.", company.currency_id.name))

            base_currency_rate = rate_info[0]

            for currency, (rate, date_rate) in parsed_data.items():
                rate_value = rate/base_currency_rate

                currency_object = Currency.search([('name','=',currency)])
                already_existing_rate = CurrencyRate.search([('currency_id', '=', currency_object.id), ('name', '=', date_rate), ('company_id', '=', company.id)])
                if already_existing_rate:
                    already_existing_rate.rate = rate_value
                else:
                    CurrencyRate.create({'currency_id': currency_object.id, 'rate': rate_value, 'name': date_rate, 'company_id': company.id})

    def _parse_fta_data(self, available_currencies):
        ''' Parses the data returned in xml by FTA servers and returns it in a more
        Python-usable form.'''
        request_url = 'https://www.backend-rates.ezv.admin.ch/api/xmldaily?d=today&locale=en'
        response = requests.get(request_url, timeout=30)
        response.raise_for_status()

        rates_dict = {}
        available_currency_names = available_currencies.mapped('name')
        xml_tree = etree.fromstring(response.content)
        data = xml2json_from_elementtree(xml_tree)
        for child_node in data['children']:
            if child_node['tag'] == 'devise':
                currency_code = child_node['attrs']['code'].upper()

                if currency_code in available_currency_names:
                    currency_xml = None
                    rate_xml = None

                    for sub_child in child_node['children']:
                        if sub_child['tag'] == 'waehrung':
                            currency_xml = sub_child['children'][0]
                        elif sub_child['tag'] == 'kurs':
                            rate_xml = sub_child['children'][0]
                        if currency_xml and rate_xml:
                            #avoid iterating for nothing on children
                            break

                    rates_dict[currency_code] = (float(re.search('\d+',currency_xml).group()) / float(rate_xml), fields.Date.today())

        if 'CHF' in available_currency_names:
            rates_dict['CHF'] = (1.0, fields.Date.today())

        return rates_dict

    def _parse_ecb_data(self, available_currencies):
        ''' This method is used to update the currencies by using ECB service provider.
            Rates are given against EURO
        '''
        request_url = "http://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
        response = requests.get(request_url, timeout=30)
        response.raise_for_status()

        xmlstr = etree.fromstring(response.content)
        data = xml2json_from_elementtree(xmlstr)
        node = data['children'][2]['children'][0]
        available_currency_names = available_currencies.mapped('name')
        rslt = {x['attrs']['currency']:(float(x['attrs']['rate']), fields.Date.today()) for x in node['children'] if x['attrs']['currency'] in available_currency_names}

        if rslt and 'EUR' in available_currency_names:
            rslt['EUR'] = (1.0, fields.Date.today())

        return rslt

    def _parse_cbuae_data(self, available_currencies):
        ''' This method is used to update the currencies by using UAE Central Bank service provider.
            Exchange rates are expressed as 1 unit of the foreign currency converted into AED
        '''
        response = requests.get(CBUAE_URL, timeout=30)
        response.raise_for_status()

        htmlelem = etree.fromstring(response.content, etree.HTMLParser(encoding='utf-8'))
        rates_entries = htmlelem.xpath("//table/tbody//tr")
        available_currency_names = set(available_currencies.mapped('name'))
        rslt = {}
        for rate_entry in rates_entries:
            # line structure is <td>Currency Description</td><td>rate</td>
            currency_code = MAP_CURRENCIES.get(rate_entry[1].text)
            rate = float(rate_entry[2].text)
            if currency_code in available_currency_names:
                rslt[currency_code] = (1.0/rate, fields.Date.today())

        if 'AED' in available_currency_names:
            rslt['AED'] = (1.0, fields.Date.today())
        return rslt

    def _parse_cbegy_data(self, available_currencies):
        ''' This method is used to update the currencies by using the Central Bank of Egypt service provider.
            Exchange rates are expressed as 1 unit of the foreign currency converted into EGP
        '''
        fetched_data = requests.get(CBEGY_URL, timeout=30)
        fetched_data.raise_for_status()

        htmlelem = etree.fromstring(fetched_data.content, etree.HTMLParser())
        rates_entries = htmlelem.xpath("//table/tbody/tr")
        available_currency_names = set(available_currencies.mapped('name'))
        rslt = {}
        for rate_entry in rates_entries:
            currency_code = MAP_CURRENCIES.get(rate_entry[0].text)
            # line structure is <td>Currency Description</td><td><span>BUY RATE</span></td><td><span>SELL RATE</span></td>
            # we use the average of SELL and BUY rates
            rate = (float(rate_entry[1][0].text) + float(rate_entry[2][0].text)) / 2
            if currency_code in available_currency_names:
                rslt[currency_code] = (1.0/rate, fields.Date.today())

        if 'EGP' in available_currency_names:
            rslt['EGP'] = (1.0, fields.Date.today())
        return rslt

    def _parse_boc_data(self, available_currencies):
        """This method is used to update currencies exchange rate by using Bank
           Of Canada daily exchange rate service.
           Exchange rates are expressed as 1 unit of the foreign currency converted into Canadian dollars.
           Keys are in this format: 'FX{CODE}CAD' e.g.: 'FXEURCAD'
        """
        available_currency_names = available_currencies.mapped('name')

        request_url = "http://www.bankofcanada.ca/valet/observations/group/FX_RATES_DAILY/json"
        response = requests.get(request_url, timeout=30)
        response.raise_for_status()
        if not 'application/json' in response.headers.get('Content-Type', ''):
            raise ValueError('Should be json')
        data = response.json()

        # 'observations' key contains rates observations by date
        last_observation_date = sorted([obs['d'] for obs in data['observations']])[-1]
        last_obs = [obs for obs in data['observations'] if obs['d'] == last_observation_date][0]
        last_obs.update({'FXCADCAD': {'v': '1'}})
        rslt = {}
        if 'CAD' in available_currency_names:
            rslt['CAD'] = (1, fields.Date.today())

        for currency_name in available_currency_names:
            currency_obs = last_obs.get('FX{}CAD'.format(currency_name), None)
            if currency_obs is not None:
                rslt[currency_name] = (1.0/float(currency_obs['v']), fields.Date.today())

        return rslt

    def _parse_banxico_data(self, available_currencies):
        """Parse function for Banxico provider.
        * With basement in legal topics in Mexico the rate must be **one** per day and it is equal to the rate known the
        day immediate before the rate is gotten, it means the rate for 02/Feb is the one at 31/jan.
        * The base currency is always MXN but with the inverse 1/rate.
        * The official institution is Banxico.
        * The webservice returns the following currency rates:
            - SF46410 EUR
            - SF60632 CAD
            - SF43718 USD Fixed
            - SF46407 GBP
            - SF46406 JPY
            - SF60653 USD SAT - Officially used from SAT institution
        Source: http://www.banxico.org.mx/portal-mercado-cambiario/
        """
        icp = self.env['ir.config_parameter'].sudo()
        token = icp.get_param('banxico_token')
        if not token:
            # https://www.banxico.org.mx/SieAPIRest/service/v1/token
            token = 'd03cdee20272f1edc5009a79375f1d942d94acac8348a33245c866831019fef4'  # noqa
            icp.set_param('banxico_token', token)
        foreigns = {
            # position order of the rates from webservices
            'SF46410': 'EUR',
            'SF60632': 'CAD',
            'SF46406': 'JPY',
            'SF46407': 'GBP',
            'SF60653': 'USD',
        }
        url = 'https://www.banxico.org.mx/SieAPIRest/service/v1/series/%s/datos/%s/%s?token=%s' # noqa
        date_mx = datetime.datetime.now(timezone('America/Mexico_City'))
        today = date_mx.strftime(DEFAULT_SERVER_DATE_FORMAT)
        yesterday = (date_mx - datetime.timedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        res = requests.get(url % (','.join(foreigns), yesterday, today, token), timeout=30)
        res.raise_for_status()
        series = res.json()['bmx']['series']
        series = {serie['idSerie']: {dato['fecha']: dato['dato'] for dato in serie['datos']} for serie in series if 'datos' in serie}

        available_currency_names = available_currencies.mapped('name')

        rslt = {
            'MXN': (1.0, fields.Date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)),
        }

        today = date_mx.strftime(BANXICO_DATE_FORMAT)
        yesterday = (date_mx - datetime.timedelta(days=1)).strftime(BANXICO_DATE_FORMAT)
        for index, currency in foreigns.items():
            if not series.get(index, False):
                continue
            if currency not in available_currency_names:
                continue

            serie = series[index]
            for rate in serie:
                try:
                    foreign_mxn_rate = float(serie[rate])
                except (ValueError, TypeError):
                    continue
                foreign_rate_date = datetime.datetime.strptime(rate, BANXICO_DATE_FORMAT).strftime(DEFAULT_SERVER_DATE_FORMAT)
                rslt[currency] = (1.0/foreign_mxn_rate, foreign_rate_date)
        return rslt

    def _parse_xe_com_data(self, available_currencies):
        """ Parses the currency rates data from xe.com provider.
        As this provider does not have an API, we directly extract what we need
        from HTML.
        """
        url_format = 'http://www.xe.com/currencytables/?from=%(currency_code)s'
        today = fields.Date.today()

        # We generate all the exchange rates relative to the USD. This is purely arbitrary.
        response = requests.get(url_format % {'currency_code': 'USD'}, timeout=30)
        response.raise_for_status()

        rslt = {}

        available_currency_names = available_currencies.mapped('name')

        if 'USD' in available_currency_names:
            rslt['USD'] = (1.0, today)

        htmlelem = etree.fromstring(response.content, etree.HTMLParser())
        rates_entries = htmlelem.xpath(".//div[@id='table-section']//tbody/tr")
        for rate_entry in rates_entries:
            # line structure is <th>CODE</th><td>NAME<td><td>UNITS PER CURRENCY</td><td>CURRENCY PER UNIT</td>
            currency_code = ''.join(rate_entry.find('.//th').itertext()).strip()
            if currency_code in available_currency_names:
                rate = float(rate_entry.find("td[2]").text.replace(',', ''))
                rslt[currency_code] = (rate, today)

        return rslt

    def _parse_bnr_data(self, available_currencies):
        ''' This method is used to update the currencies by using
        BNR service provider. Rates are given against RON
        '''
        request_url = "https://www.bnr.ro/nbrfxrates.xml"
        response = requests.get(request_url, timeout=30)
        response.raise_for_status()

        xmlstr = etree.fromstring(response.content)
        data = xml2json_from_elementtree(xmlstr)
        available_currency_names = available_currencies.mapped('name')
        rate_date = fields.Date.today()
        rslt = {}
        rates_node = data['children'][1]['children'][2]
        if rates_node:
            rate_date = (datetime.datetime.strptime(
                rates_node['attrs']['date'], DEFAULT_SERVER_DATE_FORMAT
            ) + datetime.timedelta(days=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            for x in rates_node['children']:
                if x['attrs']['currency'] in available_currency_names:
                    rslt[x['attrs']['currency']] = (
                        float(x['attrs'].get('multiplier', '1')) / float(x['children'][0]),
                        rate_date
                    )
        if rslt and 'RON' in available_currency_names:
            rslt['RON'] = (1.0, rate_date)
        return rslt

    def _parse_bcrp_data(self, available_currencies):
        """Bank of Peru (bcrp)
        API Doc: https://estadisticas.bcrp.gob.pe/estadisticas/series/ayuda/api
            - https://estadisticas.bcrp.gob.pe/estadisticas/series/api/[códigos de series]/[formato de salida]/[periodo inicial]/[periodo final]/[idioma]
        Source: https://estadisticas.bcrp.gob.pe/estadisticas/series/diarias/tipo-de-cambio
            PD04640PD	TC Sistema bancario SBS (S/ por US$) - Venta
            PD04648PD	TC Euro (S/ por Euro) - Venta
        """

        bcrp_date_format_url = '%Y-%m-%d'
        bcrp_date_format_res = '%d.%b.%y'
        result = {}
        available_currency_names = available_currencies.mapped('name')
        if 'PEN' not in available_currency_names:
            return result
        result['PEN'] = (1.0, fields.Date.context_today(self.with_context(tz='America/Lima')))
        url_format = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api/%(currency_code)s/json/%(date_start)s/%(date_end)s/ing"
        foreigns = {
            # currency code from webservices
            'USD': 'PD04640PD',
            'EUR': 'PD04648PD',
        }
        date_pe = self.mapped('currency_next_execution_date')[0] or datetime.datetime.now(timezone('America/Lima'))
        # In case the desired date does not have an exchange rate, it means that we must use the previous day until we
        # find a change. It is left 7 since in tests we have found cases of up to 5 days without update but no more
        # than that. That is not to say that that cannot change in the future, so we leave a little margin.
        first_pe_str = (date_pe - datetime.timedelta(days=7)).strftime(bcrp_date_format_url)
        second_pe_str = date_pe.strftime(bcrp_date_format_url)
        data = {
            'date_start': first_pe_str,
            'date_end': second_pe_str,
        }
        for currency_odoo_code, currency_pe_code in foreigns.items():
            if currency_odoo_code not in available_currency_names:
                continue
            data.update({'currency_code': currency_pe_code})
            url = url_format % data
            try:
                res = requests.get(url, timeout=10)
                res.raise_for_status()
                series = res.json()
            except Exception as e:
                _logger.error(e)
                continue
            date_rate_str = series['periods'][-1]['name']
            fetched_rate = float(series['periods'][-1]['values'][0])
            rate = 1.0 / fetched_rate if fetched_rate else 0
            if not rate:
                continue
            # This replace is done because the service is returning Set for September instead of Sep the value
            # commonly accepted for September,
            normalized_date = date_rate_str.replace('Set', 'Sep')
            date_rate = datetime.datetime.strptime(normalized_date, bcrp_date_format_res).strftime(DEFAULT_SERVER_DATE_FORMAT)
            result[currency_odoo_code] = (rate, date_rate)
        return result

    def _parse_mindicador_data(self, available_currencies):
        """Parse function for mindicador.cl provider for Chile
        * Regarding needs of rates in Chile there will be one rate per day, except for UTM index (one per month)
        * The value of the rate is the "official" rate
        * The base currency is always CLP but with the inverse 1/rate.
        * The webservice returns the following currency rates:
            - EUR
            - USD (Dolar Observado)
            - UF (Unidad de Fomento)
            - UTM (Unidad Tributaria Mensual)
        """
        logger = _logger.getChild('mindicador')
        icp = self.env['ir.config_parameter'].sudo()
        server_url = icp.get_param('mindicador_api_url')
        if not server_url:
            server_url = 'https://mindicador.cl/api'
            icp.set_param('mindicador_api_url', server_url)
        foreigns = {
            "USD": "dolar",
            "EUR": "euro",
            "UF": "uf",
            "UTM": "utm",
        }
        available_currency_names = available_currencies.mapped('name')
        logger.debug('mindicador: available currency names: %s', available_currency_names)
        today_date = fields.Date.context_today(self.with_context(tz='America/Santiago'))
        rslt = {
            'CLP': (1.0, fields.Date.to_string(today_date)),
        }
        request_date = today_date.strftime('%d-%m-%Y')
        for index, currency in foreigns.items():
            if index not in available_currency_names:
                logger.debug('Index %s not in available currency name', index)
                continue
            url = server_url + '/%s/%s' % (currency, request_date)
            res = requests.get(url, timeout=30)
            res.raise_for_status()
            if 'html' in res.text:
                raise ValueError('Should be json')
            data_json = res.json()
            if not data_json['serie']:
                continue
            date = data_json['serie'][0]['fecha'][:10]
            rate = data_json['serie'][0]['valor']
            rslt[index] = (1.0 / rate,  date)
        return rslt

    def _parse_tcmb_data(self, available_currencies):
        """Parse function for Turkish Central bank provider
        * The webservice returns the following currency rates:
        - USD, AUD, DKK, EUR, GBP, CHF, SEK, CAD, KWD, NOK, SAR,
        - JPY, BGN, RON, RUB, IRR, CNY, PKR, QAR, KRW, AZN, AED
        """
        server_url = 'https://www.tcmb.gov.tr/kurlar/today.xml'
        available_currency_names = set(available_currencies.mapped('name'))

        res = requests.get(server_url, timeout=30)
        res.raise_for_status()

        root = etree.fromstring(res.text.encode())
        rate_date = fields.Date.to_string(datetime.datetime.strptime(root.attrib['Date'], '%m/%d/%Y'))
        rslt = {
            currency.attrib['Kod']: (2 / (float(currency.find('ForexBuying').text) + float(currency.find('ForexSelling').text)), rate_date)
            for currency in root
            if currency.attrib['Kod'] in available_currency_names
        }
        rslt['TRY'] = (1.0, rate_date)

        return rslt

    @api.model
    def run_update_currency(self):
        """ This method is called from a cron job to update currency rates.
        """
        records = self.search([('currency_next_execution_date', '<=', fields.Date.today())])
        if records:
            to_update = self.env['res.company']
            for record in records:
                if record.currency_interval_unit == 'daily':
                    next_update = relativedelta(days=+1)
                elif record.currency_interval_unit == 'weekly':
                    next_update = relativedelta(weeks=+1)
                elif record.currency_interval_unit == 'monthly':
                    next_update = relativedelta(months=+1)
                else:
                    record.currency_next_execution_date = False
                    continue
                record.currency_next_execution_date = datetime.date.today() + next_update
                to_update += record
            to_update.update_currency_rates()


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_interval_unit = fields.Selection(related="company_id.currency_interval_unit", readonly=False)
    currency_provider = fields.Selection(related="company_id.currency_provider", readonly=False)
    currency_next_execution_date = fields.Date(related="company_id.currency_next_execution_date", readonly=False)

    @api.onchange('currency_interval_unit')
    def onchange_currency_interval_unit(self):
        #as the onchange is called upon each opening of the settings, we avoid overwriting
        #the next execution date if it has been already set
        if self.company_id.currency_next_execution_date:
            return
        if self.currency_interval_unit == 'daily':
            next_update = relativedelta(days=+1)
        elif self.currency_interval_unit == 'weekly':
            next_update = relativedelta(weeks=+1)
        elif self.currency_interval_unit == 'monthly':
            next_update = relativedelta(months=+1)
        else:
            self.currency_next_execution_date = False
            return
        self.currency_next_execution_date = datetime.date.today() + next_update

    def update_currency_rates_manually(self):
        self.ensure_one()

        if not (self.company_id.update_currency_rates()):
            raise UserError(_('Unable to connect to the online exchange rate platform. The web service may be temporary down. Please try again in a moment.'))
