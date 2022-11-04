from odoo.tests.common import TransactionCase, tagged


@tagged('-standard', 'external')
class CurrencyTestCase(TransactionCase):

    def setUp(self):
        super(CurrencyTestCase, self).setUp()
        # Each test will check the number of rates for USD
        self.currency_usd = self.env.ref('base.USD')
        self.test_company = self.env['res.company'].create({
            'name': 'Test Company',
            'currency_id': self.currency_usd.id,
        })

    def test_live_currency_update_ecb(self):
        self.test_company.currency_provider = 'ecb'
        rates_count = len(self.currency_usd.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(self.currency_usd.rate_ids), rates_count + 1)

    def test_live_currency_update_fta(self):
        self.test_company.currency_provider = 'fta'
        # testing Swiss Federal Tax Administration requires that Franc Suisse can be found
        # which is not the case in runbot/demo data as l10n_ch is not always installed
        self.env.ref('base.CHF').write({'active': True})
        rates_count = len(self.currency_usd.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(self.currency_usd.rate_ids), rates_count + 1)

    def test_live_currency_update_banxico(self):
        self.test_company.currency_provider = 'banxico'
        self.env.ref('base.MXN').write({'active': True})
        rates_count = len(self.currency_usd.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(self.currency_usd.rate_ids), rates_count + 1)

    def test_live_currency_update_boc(self):
        self.test_company.currency_provider = 'boc'
        rates_count = len(self.currency_usd.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(self.currency_usd.rate_ids), rates_count + 1)

    def test_live_currency_update_xe_com(self):
        self.test_company.currency_provider = 'xe_com'
        rates_count = len(self.currency_usd.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(self.currency_usd.rate_ids), rates_count + 1)

    def test_live_currency_update_bnr_com(self):
        self.test_company.currency_provider = 'bnr'
        rates_count = len(self.currency_usd.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(self.currency_usd.rate_ids), rates_count + 1)

    def test_live_currency_update_cbuae(self):
        self.test_company.currency_provider = 'cbuae'
        rates_count = len(self.currency_usd.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(self.currency_usd.rate_ids), rates_count + 1)

    def test_live_currency_update_cbegy(self):
        self.test_company.currency_provider = 'cbegy'
        rates_count = len(self.currency_usd.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(self.currency_usd.rate_ids), rates_count + 1)

    def test_live_currency_update_bcrp(self):
        pen = self.env.ref('base.PEN')
        pen.active = True
        usd = self.env.ref('base.USD')
        usd.active = True
        self.test_company.write({
            'currency_provider': 'bcrp',
            'currency_id': pen.id
        })
        pen_rates_count = len(pen.rate_ids)
        usd_rates_count = len(usd.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(pen.rate_ids), pen_rates_count + 1)
        self.assertEqual(pen.rate_ids[-1].rate, 1.0)
        self.assertEqual(len(usd.rate_ids), usd_rates_count + 1)
        self.assertLess(usd.rate_ids[-1].rate, 1)

    def test_live_currency_update_tcmb(self):
        ytl = self.env.ref('base.TRY')
        ytl.active = True
        self.test_company.write({
            'currency_provider': 'tcmb',
            'currency_id': ytl.id
        })
        rates_count = len(ytl.rate_ids)
        res = self.test_company.update_currency_rates()
        self.assertTrue(res)
        self.assertEqual(len(ytl.rate_ids), rates_count + 1)
