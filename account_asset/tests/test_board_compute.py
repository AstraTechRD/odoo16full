# -*- coding: utf-8 -*-

import datetime

from freezegun import freeze_time
from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@freeze_time('2022-07-01')
@tagged('post_install', '-at_install')
class TestAccountAssetNew(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.car = cls.env['account.asset'].create({
            'account_asset_id': cls.company_data['default_account_assets'].id,
            'account_depreciation_id': cls.company_data['default_account_assets'].copy().id,
            'account_depreciation_expense_id': cls.company_data['default_account_expense'].id,
            'journal_id': cls.company_data['default_journal_misc'].id,
            'asset_type': 'purchase',
            'name': 'Ranger Rover',
            'acquisition_date': '2020-02-01',
            'prorata_computation_type': 'none',
            'original_value': 60000,
            'salvage_value': 0,
            'method_number': 5,
            'method_period': '12',
            'method': 'linear',
        })

    def _get_depreciation_move_values(self, date, depreciation_value, remaining_value, depreciated_value, state):
        return {
            'date': datetime.datetime.strptime(date, '%Y-%m-%d').date(),
            'depreciation_value': depreciation_value,
            'asset_remaining_value': remaining_value,
            'asset_depreciated_value': depreciated_value,
            'state': state,
        }

    def test_linear_purchase_5_years_no_prorata_asset(self):
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=12000, remaining_value=48000, depreciated_value=12000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=36000, depreciated_value=24000, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=24000, depreciated_value=36000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_purchase_5_years_no_prorata_with_imported_amount_asset(self):
        self.car.write({'already_depreciated_amount_import': 1000})
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=11000, remaining_value=48000, depreciated_value=11000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=36000, depreciated_value=23000, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=24000, depreciated_value=35000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=12000, depreciated_value=47000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_linear_purchase_5_years_no_prorata_with_salvage_value_asset(self):
        self.car.write({'salvage_value': 1000})
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36400)
        self.assertEqual(self.car.value_residual, 35400)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=11800, remaining_value=47200, depreciated_value=11800, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=11800, remaining_value=35400, depreciated_value=23600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=11800, remaining_value=23600, depreciated_value=35400, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=11800, remaining_value=11800, depreciated_value=47200, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=11800, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_linear_purchase_5_years_constant_periods_asset(self):
        self.car.write({
            'prorata_computation_type': 'constant_periods',
            'prorata_date': '2020-07-01',
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 42000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=6000, remaining_value=54000, depreciated_value=6000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12000, remaining_value=42000, depreciated_value=18000, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=12000, remaining_value=30000, depreciated_value=30000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=12000, remaining_value=18000, depreciated_value=42000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12000, remaining_value=6000, depreciated_value=54000, state='draft'),
            self._get_depreciation_move_values(date='2025-12-31', depreciation_value=6000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_purchase_5_years_daily_computation_asset(self):
        self.car.write({
            'prorata_computation_type': 'daily_computation',
            'prorata_date': '2020-07-01',
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 41960.57)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=6046, remaining_value=53954, depreciated_value=6046, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=11993.43, remaining_value=41960.57, depreciated_value=18039.43, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=11993.43, remaining_value=29967.14, depreciated_value=30032.86, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=11993.43, remaining_value=17973.71, depreciated_value=42026.29, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=12026.28, remaining_value=5947.43, depreciated_value=54052.57, state='draft'),
            self._get_depreciation_move_values(date='2025-12-31', depreciation_value=5947.43, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_degressive_purchase_5_years_no_prorata_asset(self):
        self.car.write({
            'method': 'degressive',
            'method_progress_factor': 0.3,
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 29400)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=18000, remaining_value=42000, depreciated_value=18000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12600, remaining_value=29400, depreciated_value=30600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=8820, remaining_value=20580, depreciated_value=39420, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=6174, remaining_value=14406, depreciated_value=45594, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=14406, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_degressive_purchase_5_years_no_prorata_with_imported_amount_asset(self):
        self.car.write({
            'method': 'degressive',
            'method_progress_factor': 0.3,
            'already_depreciated_amount_import': 1000,
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 29400)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=17000, remaining_value=42000, depreciated_value=17000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12600, remaining_value=29400, depreciated_value=29600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=8820, remaining_value=20580, depreciated_value=38420, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=6174, remaining_value=14406, depreciated_value=44594, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=14406, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_degressive_purchase_5_years_no_prorata_with_salvage_value_asset(self):
        self.car.write({
            'method': 'degressive',
            'method_progress_factor': 0.3,
            'salvage_value': 1000,
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 29910)
        self.assertEqual(self.car.value_residual, 28910)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=17700, remaining_value=41300, depreciated_value=17700, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12390, remaining_value=28910, depreciated_value=30090, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=8673, remaining_value=20237, depreciated_value=38763, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=6071.1, remaining_value=14165.9, depreciated_value=44834.1, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=14165.9, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_degressive_then_linear_purchase_5_years_no_prorata_asset(self):
        self.car.write({
            'method': 'degressive_then_linear',
            'method_progress_factor': 0.3,
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 29400)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=18000, remaining_value=42000, depreciated_value=18000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12600, remaining_value=29400, depreciated_value=30600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=9800, remaining_value=19600, depreciated_value=40400, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=9800, remaining_value=9800, depreciated_value=50200, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=9800, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_degressive_than_linear_purchase_5_years_no_prorata_with_imported_amount_asset(self):
        self.car.write({
            'method': 'degressive_then_linear',
            'method_progress_factor': 0.3,
            'already_depreciated_amount_import': 1000,
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 29400)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=17000, remaining_value=42000, depreciated_value=17000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12600, remaining_value=29400, depreciated_value=29600, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=9800, remaining_value=19600, depreciated_value=39400, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=9800, remaining_value=9800, depreciated_value=49200, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=9800, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_degressive_than_linear_purchase_5_years_no_prorata_with_salvage_value_asset(self):
        self.car.write({
            'method': 'degressive_then_linear',
            'method_progress_factor': 0.3,
            'salvage_value': 1000,
        })
        self.car.validate()

        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 29910)
        self.assertEqual(self.car.value_residual, 28910)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=17700, remaining_value=41300, depreciated_value=17700, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=12390, remaining_value=28910, depreciated_value=30090, state='posted'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=9636.67, remaining_value=19273.33, depreciated_value=39726.67, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=9636.67, remaining_value=9636.66, depreciated_value=49363.34, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=9636.66, remaining_value=0, depreciated_value=59000, state='draft'),
        ])

    def test_linear_purchase_60_months_no_prorata_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 30000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=1000, remaining_value=59000, depreciated_value=1000, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=1000, remaining_value=58000, depreciated_value=2000, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=1000, remaining_value=57000, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=1000, remaining_value=56000, depreciated_value=4000, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=1000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=1000, remaining_value=54000, depreciated_value=6000, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1000, remaining_value=53000, depreciated_value=7000, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1000, remaining_value=52000, depreciated_value=8000, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1000, remaining_value=51000, depreciated_value=9000, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1000, remaining_value=49000, depreciated_value=11000, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1000, remaining_value=48000, depreciated_value=12000, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1000, remaining_value=47000, depreciated_value=13000, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1000, remaining_value=46000, depreciated_value=14000, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1000, remaining_value=44000, depreciated_value=16000, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1000, remaining_value=43000, depreciated_value=17000, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1000, remaining_value=42000, depreciated_value=18000, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1000, remaining_value=41000, depreciated_value=19000, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1000, remaining_value=40000, depreciated_value=20000, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1000, remaining_value=39000, depreciated_value=21000, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1000, remaining_value=38000, depreciated_value=22000, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1000, remaining_value=37000, depreciated_value=23000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1000, remaining_value=36000, depreciated_value=24000, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=1000, remaining_value=35000, depreciated_value=25000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=1000, remaining_value=34000, depreciated_value=26000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=1000, remaining_value=33000, depreciated_value=27000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=1000, remaining_value=32000, depreciated_value=28000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=31000, depreciated_value=29000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=30000, depreciated_value=30000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=29000, depreciated_value=31000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=28000, depreciated_value=32000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=27000, depreciated_value=33000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=26000, depreciated_value=34000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=25000, depreciated_value=35000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=24000, depreciated_value=36000, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=1000, remaining_value=23000, depreciated_value=37000, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=1000, remaining_value=22000, depreciated_value=38000, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=1000, remaining_value=21000, depreciated_value=39000, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=1000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=1000, remaining_value=19000, depreciated_value=41000, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=1000, remaining_value=18000, depreciated_value=42000, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=1000, remaining_value=17000, depreciated_value=43000, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=1000, remaining_value=16000, depreciated_value=44000, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=1000, remaining_value=15000, depreciated_value=45000, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=1000, remaining_value=14000, depreciated_value=46000, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=1000, remaining_value=13000, depreciated_value=47000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=1000, remaining_value=12000, depreciated_value=48000, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=1000, remaining_value=11000, depreciated_value=49000, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=1000, remaining_value=10000, depreciated_value=50000, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1000, remaining_value=9000, depreciated_value=51000, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=1000, remaining_value=8000, depreciated_value=52000, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=1000, remaining_value=7000, depreciated_value=53000, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=1000, remaining_value=6000, depreciated_value=54000, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=1000, remaining_value=5000, depreciated_value=55000, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=1000, remaining_value=4000, depreciated_value=56000, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=1000, remaining_value=3000, depreciated_value=57000, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=1000, remaining_value=2000, depreciated_value=58000, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=1000, remaining_value=1000, depreciated_value=59000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=1000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_purchase_60_months_no_prorata_with_imported_amount_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'already_depreciated_amount_import': 1500,
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 30000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=500.0, remaining_value=58000.0, depreciated_value=500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=1000.0, remaining_value=57000.0, depreciated_value=1500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=1000.0, remaining_value=56000.0, depreciated_value=2500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=1000.0, remaining_value=55000.0, depreciated_value=3500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=1000.0, remaining_value=54000.0, depreciated_value=4500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1000.0, remaining_value=53000.0, depreciated_value=5500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1000.0, remaining_value=52000.0, depreciated_value=6500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1000.0, remaining_value=51000.0, depreciated_value=7500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1000.0, remaining_value=50000.0, depreciated_value=8500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1000.0, remaining_value=49000.0, depreciated_value=9500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1000.0, remaining_value=48000.0, depreciated_value=10500.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1000.0, remaining_value=47000.0, depreciated_value=11500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1000.0, remaining_value=46000.0, depreciated_value=12500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1000.0, remaining_value=45000.0, depreciated_value=13500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1000.0, remaining_value=44000.0, depreciated_value=14500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1000.0, remaining_value=43000.0, depreciated_value=15500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1000.0, remaining_value=42000.0, depreciated_value=16500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1000.0, remaining_value=41000.0, depreciated_value=17500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1000.0, remaining_value=40000.0, depreciated_value=18500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1000.0, remaining_value=39000.0, depreciated_value=19500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1000.0, remaining_value=38000.0, depreciated_value=20500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1000.0, remaining_value=37000.0, depreciated_value=21500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1000.0, remaining_value=36000.0, depreciated_value=22500.0, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=1000.0, remaining_value=35000.0, depreciated_value=23500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=1000.0, remaining_value=34000.0, depreciated_value=24500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=1000.0, remaining_value=33000.0, depreciated_value=25500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=1000.0, remaining_value=32000.0, depreciated_value=26500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000.0, remaining_value=31000.0, depreciated_value=27500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000.0, remaining_value=30000.0, depreciated_value=28500.0, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000.0, remaining_value=29000.0, depreciated_value=29500.0, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000.0, remaining_value=28000.0, depreciated_value=30500.0, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000.0, remaining_value=27000.0, depreciated_value=31500.0, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000.0, remaining_value=26000.0, depreciated_value=32500.0, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000.0, remaining_value=25000.0, depreciated_value=33500.0, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000.0, remaining_value=24000.0, depreciated_value=34500.0, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=1000.0, remaining_value=23000.0, depreciated_value=35500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=1000.0, remaining_value=22000.0, depreciated_value=36500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=1000.0, remaining_value=21000.0, depreciated_value=37500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=1000.0, remaining_value=20000.0, depreciated_value=38500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=1000.0, remaining_value=19000.0, depreciated_value=39500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=1000.0, remaining_value=18000.0, depreciated_value=40500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=1000.0, remaining_value=17000.0, depreciated_value=41500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=1000.0, remaining_value=16000.0, depreciated_value=42500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=1000.0, remaining_value=15000.0, depreciated_value=43500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=1000.0, remaining_value=14000.0, depreciated_value=44500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=1000.0, remaining_value=13000.0, depreciated_value=45500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=1000.0, remaining_value=12000.0, depreciated_value=46500.0, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=1000.0, remaining_value=11000.0, depreciated_value=47500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=1000.0, remaining_value=10000.0, depreciated_value=48500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1000.0, remaining_value=9000.0, depreciated_value=49500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=1000.0, remaining_value=8000.0, depreciated_value=50500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=1000.0, remaining_value=7000.0, depreciated_value=51500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=1000.0, remaining_value=6000.0, depreciated_value=52500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=1000.0, remaining_value=5000.0, depreciated_value=53500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=1000.0, remaining_value=4000.0, depreciated_value=54500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=1000.0, remaining_value=3000.0, depreciated_value=55500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=1000.0, remaining_value=2000.0, depreciated_value=56500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=1000.0, remaining_value=1000.0, depreciated_value=57500.0, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=1000.0, remaining_value=0.0, depreciated_value=58500.0, state='draft'),
        ])

    def test_linear_purchase_60_months_no_prorata_with_salvage_value_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'method_progress_factor': 0.3,
            'salvage_value': 2000,
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 31000)
        self.assertEqual(self.car.value_residual, 29000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=966.67, remaining_value=57033.33, depreciated_value=966.67, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=966.66, remaining_value=56066.67, depreciated_value=1933.33, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=966.67, remaining_value=55100.0, depreciated_value=2900.0, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=966.67, remaining_value=54133.33, depreciated_value=3866.67, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=966.66, remaining_value=53166.67, depreciated_value=4833.33, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=966.67, remaining_value=52200.0, depreciated_value=5800.0, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=966.67, remaining_value=51233.33, depreciated_value=6766.67, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=966.66, remaining_value=50266.67, depreciated_value=7733.33, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=966.67, remaining_value=49300.0, depreciated_value=8700.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=966.67, remaining_value=48333.33, depreciated_value=9666.67, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=966.66, remaining_value=47366.67, depreciated_value=10633.33, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=966.67, remaining_value=46400.0, depreciated_value=11600.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=966.67, remaining_value=45433.33, depreciated_value=12566.67, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=966.66, remaining_value=44466.67, depreciated_value=13533.33, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=966.67, remaining_value=43500.0, depreciated_value=14500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=966.67, remaining_value=42533.33, depreciated_value=15466.67, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=966.66, remaining_value=41566.67, depreciated_value=16433.33, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=966.67, remaining_value=40600.0, depreciated_value=17400.0, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=966.67, remaining_value=39633.33, depreciated_value=18366.67, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=966.66, remaining_value=38666.67, depreciated_value=19333.33, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=966.67, remaining_value=37700.0, depreciated_value=20300.0, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=966.67, remaining_value=36733.33, depreciated_value=21266.67, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=966.66, remaining_value=35766.67, depreciated_value=22233.33, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=966.67, remaining_value=34800.0, depreciated_value=23200.0, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=966.67, remaining_value=33833.33, depreciated_value=24166.67, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=966.66, remaining_value=32866.67, depreciated_value=25133.33, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=966.67, remaining_value=31900.0, depreciated_value=26100.0, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=966.67, remaining_value=30933.33, depreciated_value=27066.67, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=966.66, remaining_value=29966.67, depreciated_value=28033.33, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=966.67, remaining_value=29000.0, depreciated_value=29000.0, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=966.67, remaining_value=28033.33, depreciated_value=29966.67, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=966.66, remaining_value=27066.67, depreciated_value=30933.33, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=966.67, remaining_value=26100.0, depreciated_value=31900.0, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=966.67, remaining_value=25133.33, depreciated_value=32866.67, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=966.66, remaining_value=24166.67, depreciated_value=33833.33, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=966.67, remaining_value=23200.0, depreciated_value=34800.0, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=966.67, remaining_value=22233.33, depreciated_value=35766.67, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=966.66, remaining_value=21266.67, depreciated_value=36733.33, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=966.67, remaining_value=20300.0, depreciated_value=37700.0, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=966.67, remaining_value=19333.33, depreciated_value=38666.67, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=966.66, remaining_value=18366.67, depreciated_value=39633.33, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=966.67, remaining_value=17400.0, depreciated_value=40600.0, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=966.67, remaining_value=16433.33, depreciated_value=41566.67, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=966.66, remaining_value=15466.67, depreciated_value=42533.33, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=966.67, remaining_value=14500.0, depreciated_value=43500.0, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=966.67, remaining_value=13533.33, depreciated_value=44466.67, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=966.66, remaining_value=12566.67, depreciated_value=45433.33, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=966.67, remaining_value=11600.0, depreciated_value=46400.0, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=966.67, remaining_value=10633.33, depreciated_value=47366.67, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=966.66, remaining_value=9666.67, depreciated_value=48333.33, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=966.67, remaining_value=8700.0, depreciated_value=49300.0, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=966.67, remaining_value=7733.33, depreciated_value=50266.67, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=966.66, remaining_value=6766.67, depreciated_value=51233.33, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=966.67, remaining_value=5800.0, depreciated_value=52200.0, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=966.67, remaining_value=4833.33, depreciated_value=53166.67, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=966.66, remaining_value=3866.67, depreciated_value=54133.33, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=966.67, remaining_value=2900.0, depreciated_value=55100.0, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=966.67, remaining_value=1933.33, depreciated_value=56066.67, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=966.66, remaining_value=966.67, depreciated_value=57033.33, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=966.67, remaining_value=0.0, depreciated_value=58000.0, state='draft'),
        ])

    def test_linear_purchase_60_months_constant_periods_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'prorata_computation_type': 'constant_periods',
            'prorata_date': '2020-07-01',
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36000)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1000, remaining_value=59000, depreciated_value=1000, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1000, remaining_value=58000, depreciated_value=2000, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1000, remaining_value=57000, depreciated_value=3000, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1000, remaining_value=56000, depreciated_value=4000, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1000, remaining_value=55000, depreciated_value=5000, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1000, remaining_value=54000, depreciated_value=6000, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1000, remaining_value=53000, depreciated_value=7000, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1000, remaining_value=52000, depreciated_value=8000, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1000, remaining_value=51000, depreciated_value=9000, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1000, remaining_value=50000, depreciated_value=10000, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1000, remaining_value=49000, depreciated_value=11000, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1000, remaining_value=48000, depreciated_value=12000, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1000, remaining_value=47000, depreciated_value=13000, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1000, remaining_value=46000, depreciated_value=14000, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1000, remaining_value=45000, depreciated_value=15000, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1000, remaining_value=44000, depreciated_value=16000, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1000, remaining_value=43000, depreciated_value=17000, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1000, remaining_value=42000, depreciated_value=18000, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=1000, remaining_value=41000, depreciated_value=19000, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=1000, remaining_value=40000, depreciated_value=20000, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=1000, remaining_value=39000, depreciated_value=21000, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=1000, remaining_value=38000, depreciated_value=22000, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1000, remaining_value=37000, depreciated_value=23000, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=1000, remaining_value=36000, depreciated_value=24000, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1000, remaining_value=35000, depreciated_value=25000, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1000, remaining_value=34000, depreciated_value=26000, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=1000, remaining_value=33000, depreciated_value=27000, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1000, remaining_value=32000, depreciated_value=28000, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=1000, remaining_value=31000, depreciated_value=29000, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1000, remaining_value=30000, depreciated_value=30000, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=1000, remaining_value=29000, depreciated_value=31000, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=1000, remaining_value=28000, depreciated_value=32000, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=1000, remaining_value=27000, depreciated_value=33000, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=1000, remaining_value=26000, depreciated_value=34000, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=1000, remaining_value=25000, depreciated_value=35000, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=1000, remaining_value=24000, depreciated_value=36000, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=1000, remaining_value=23000, depreciated_value=37000, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=1000, remaining_value=22000, depreciated_value=38000, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=1000, remaining_value=21000, depreciated_value=39000, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=1000, remaining_value=20000, depreciated_value=40000, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=1000, remaining_value=19000, depreciated_value=41000, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=1000, remaining_value=18000, depreciated_value=42000, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=1000, remaining_value=17000, depreciated_value=43000, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=1000, remaining_value=16000, depreciated_value=44000, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1000, remaining_value=15000, depreciated_value=45000, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=1000, remaining_value=14000, depreciated_value=46000, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=1000, remaining_value=13000, depreciated_value=47000, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=1000, remaining_value=12000, depreciated_value=48000, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=1000, remaining_value=11000, depreciated_value=49000, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=1000, remaining_value=10000, depreciated_value=50000, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=1000, remaining_value=9000, depreciated_value=51000, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=1000, remaining_value=8000, depreciated_value=52000, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=1000, remaining_value=7000, depreciated_value=53000, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=1000, remaining_value=6000, depreciated_value=54000, state='draft'),
            # 2025
            self._get_depreciation_move_values(date='2025-01-31', depreciation_value=1000, remaining_value=5000, depreciated_value=55000, state='draft'),
            self._get_depreciation_move_values(date='2025-02-28', depreciation_value=1000, remaining_value=4000, depreciated_value=56000, state='draft'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=1000, remaining_value=3000, depreciated_value=57000, state='draft'),
            self._get_depreciation_move_values(date='2025-04-30', depreciation_value=1000, remaining_value=2000, depreciated_value=58000, state='draft'),
            self._get_depreciation_move_values(date='2025-05-31', depreciation_value=1000, remaining_value=1000, depreciated_value=59000, state='draft'),
            self._get_depreciation_move_values(date='2025-06-30', depreciation_value=1000, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_linear_purchase_60_months_daily_computation_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'prorata_computation_type': 'daily_computation',
            'prorata_date': '2020-07-01',
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 36013.14)

        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1018.62, remaining_value=58981.38, depreciated_value=1018.62, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1018.62, remaining_value=57962.76, depreciated_value=2037.24, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=985.76, remaining_value=56977.0, depreciated_value=3023.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1018.62, remaining_value=55958.38, depreciated_value=4041.62, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=985.76, remaining_value=54972.62, depreciated_value=5027.38, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1018.62, remaining_value=53954.0, depreciated_value=6046.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1018.62, remaining_value=52935.38, depreciated_value=7064.62, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=920.05, remaining_value=52015.33, depreciated_value=7984.67, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1018.62, remaining_value=50996.71, depreciated_value=9003.29, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=985.76, remaining_value=50010.95, depreciated_value=9989.05, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1018.62, remaining_value=48992.33, depreciated_value=11007.67, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=985.76, remaining_value=48006.57, depreciated_value=11993.43, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1018.62, remaining_value=46987.95, depreciated_value=13012.05, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1018.62, remaining_value=45969.33, depreciated_value=14030.67, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=985.76, remaining_value=44983.57, depreciated_value=15016.43, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1018.62, remaining_value=43964.95, depreciated_value=16035.05, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=985.76, remaining_value=42979.19, depreciated_value=17020.81, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1018.62, remaining_value=41960.57, depreciated_value=18039.43, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=1018.62, remaining_value=40941.95, depreciated_value=19058.05, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=920.04, remaining_value=40021.91, depreciated_value=19978.09, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=1018.62, remaining_value=39003.29, depreciated_value=20996.71, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=985.77, remaining_value=38017.52, depreciated_value=21982.48, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=1018.62, remaining_value=36998.9, depreciated_value=23001.10, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=985.76, remaining_value=36013.14, depreciated_value=23986.86, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=1018.62, remaining_value=34994.52, depreciated_value=25005.48, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=1018.62, remaining_value=33975.9, depreciated_value=26024.10, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=985.76, remaining_value=32990.14, depreciated_value=27009.86, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=1018.62, remaining_value=31971.52, depreciated_value=28028.48, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=985.76, remaining_value=30985.76, depreciated_value=29014.24, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=1018.62, remaining_value=29967.14, depreciated_value=30032.86, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=1018.62, remaining_value=28948.52, depreciated_value=31051.48, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=920.04, remaining_value=28028.48, depreciated_value=31971.52, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=1018.62, remaining_value=27009.86, depreciated_value=32990.14, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=985.76, remaining_value=26024.10, depreciated_value=33975.9, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=1018.62, remaining_value=25005.48, depreciated_value=34994.52, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=985.76, remaining_value=24019.72, depreciated_value=35980.28, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=1018.62, remaining_value=23001.10, depreciated_value=36998.9, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=1018.62, remaining_value=21982.48, depreciated_value=38017.52, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=985.77, remaining_value=20996.71, depreciated_value=39003.29, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=1018.62, remaining_value=19978.09, depreciated_value=40021.91, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=985.76, remaining_value=18992.33, depreciated_value=41007.67, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=1018.62, remaining_value=17973.71, depreciated_value=42026.29, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=1018.62, remaining_value=16955.09, depreciated_value=43044.91, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=952.9, remaining_value=16002.19, depreciated_value=43997.81, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=1018.62, remaining_value=14983.57, depreciated_value=45016.43, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=985.76, remaining_value=13997.81, depreciated_value=46002.19, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=1018.62, remaining_value=12979.19, depreciated_value=47020.81, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=985.76, remaining_value=11993.43, depreciated_value=48006.57, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=1018.62, remaining_value=10974.81, depreciated_value=49025.19, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=1018.62, remaining_value=9956.19, depreciated_value=50043.81, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=985.76, remaining_value=8970.43, depreciated_value=51029.57, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=1018.62, remaining_value=7951.81, depreciated_value=52048.19, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=985.76, remaining_value=6966.05, depreciated_value=53033.95, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=1018.62, remaining_value=5947.43, depreciated_value=54052.57, state='draft'),
            # 2025
            self._get_depreciation_move_values(date='2025-01-31', depreciation_value=1018.62, remaining_value=4928.81, depreciated_value=55071.19, state='draft'),
            self._get_depreciation_move_values(date='2025-02-28', depreciation_value=920.05, remaining_value=4008.76, depreciated_value=55991.24, state='draft'),
            self._get_depreciation_move_values(date='2025-03-31', depreciation_value=1018.62, remaining_value=2990.14, depreciated_value=57009.86, state='draft'),
            self._get_depreciation_move_values(date='2025-04-30', depreciation_value=985.76, remaining_value=2004.38, depreciated_value=57995.62, state='draft'),
            self._get_depreciation_move_values(date='2025-05-31', depreciation_value=1018.62, remaining_value=985.76, depreciated_value=59014.24, state='draft'),
            self._get_depreciation_move_values(date='2025-06-30', depreciation_value=985.76, remaining_value=0.0, depreciated_value=60000.0, state='draft'),
        ])

    def test_degressive_purchase_60_months_no_prorata_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'method': 'degressive',
            'method_progress_factor': 0.3,
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 24990)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=1500.0, remaining_value=58500.0, depreciated_value=1500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=1500.0, remaining_value=57000.0, depreciated_value=3000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=1500.0, remaining_value=55500.0, depreciated_value=4500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=1500.0, remaining_value=54000.0, depreciated_value=6000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=1500.0, remaining_value=52500.0, depreciated_value=7500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=1500.0, remaining_value=51000.0, depreciated_value=9000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1500.0, remaining_value=49500.0, depreciated_value=10500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1500.0, remaining_value=48000.0, depreciated_value=12000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1500.0, remaining_value=46500.0, depreciated_value=13500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1500.0, remaining_value=45000.0, depreciated_value=15000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1500.0, remaining_value=43500.0, depreciated_value=16500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1500.0, remaining_value=42000.0, depreciated_value=18000.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1050.0, remaining_value=40950.0, depreciated_value=19050.0, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1050.0, remaining_value=39900.0, depreciated_value=20100.0, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1050.0, remaining_value=38850.0, depreciated_value=21150.0, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1050.0, remaining_value=37800.0, depreciated_value=22200.0, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1050.0, remaining_value=36750.0, depreciated_value=23250.0, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1050.0, remaining_value=35700.0, depreciated_value=24300.0, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1050.0, remaining_value=34650.0, depreciated_value=25350.0, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1050.0, remaining_value=33600.0, depreciated_value=26400.0, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1050.0, remaining_value=32550.0, depreciated_value=27450.0, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1050.0, remaining_value=31500.0, depreciated_value=28500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1050.0, remaining_value=30450.0, depreciated_value=29550.0, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1050.0, remaining_value=29400.0, depreciated_value=30600.0, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=735.0, remaining_value=28665.0, depreciated_value=31335.0, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=735.0, remaining_value=27930.0, depreciated_value=32070.0, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=735.0, remaining_value=27195.0, depreciated_value=32805.0, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=735.0, remaining_value=26460.0, depreciated_value=33540.0, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=735.0, remaining_value=25725.0, depreciated_value=34275.0, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=735.0, remaining_value=24990.0, depreciated_value=35010.0, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=735.0, remaining_value=24255.0, depreciated_value=35745.0, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=735.0, remaining_value=23520.0, depreciated_value=36480.0, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=735.0, remaining_value=22785.0, depreciated_value=37215.0, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=735.0, remaining_value=22050.0, depreciated_value=37950.0, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=735.0, remaining_value=21315.0, depreciated_value=38685.0, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=735.0, remaining_value=20580.0, depreciated_value=39420.0, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=514.5, remaining_value=20065.5, depreciated_value=39934.5, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=514.5, remaining_value=19551.0, depreciated_value=40449.0, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=514.5, remaining_value=19036.5, depreciated_value=40963.5, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=514.5, remaining_value=18522.0, depreciated_value=41478.0, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=514.5, remaining_value=18007.5, depreciated_value=41992.5, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=514.5, remaining_value=17493.0, depreciated_value=42507.0, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=514.5, remaining_value=16978.5, depreciated_value=43021.5, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=514.5, remaining_value=16464.0, depreciated_value=43536.0, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=514.5, remaining_value=15949.5, depreciated_value=44050.5, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=514.5, remaining_value=15435.0, depreciated_value=44565.0, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=514.5, remaining_value=14920.5, depreciated_value=45079.5, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=514.5, remaining_value=14406.0, depreciated_value=45594.0, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=360.15, remaining_value=14045.85, depreciated_value=45954.15, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=360.15, remaining_value=13685.70, depreciated_value=46314.30, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=360.15, remaining_value=13325.55, depreciated_value=46674.45, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=360.15, remaining_value=12965.40, depreciated_value=47034.60, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=360.15, remaining_value=12605.25, depreciated_value=47394.75, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=360.15, remaining_value=12245.10, depreciated_value=47754.90, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=360.15, remaining_value=11884.95, depreciated_value=48115.05, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=360.15, remaining_value=11524.80, depreciated_value=48475.20, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=360.15, remaining_value=11164.65, depreciated_value=48835.35, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=360.15, remaining_value=10804.50, depreciated_value=49195.50, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=360.15, remaining_value=10444.35, depreciated_value=49555.65, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=10444.35, remaining_value=0, depreciated_value=60000, state='draft'),
        ])

    def test_degressive_purchase_60_months_no_prorata_with_imported_amount_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'method': 'degressive',
            'method_progress_factor': 0.3,
            'already_depreciated_amount_import': 2000,
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 24990)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=1000.0, remaining_value=57000.0, depreciated_value=1000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=1500.0, remaining_value=55500.0, depreciated_value=2500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=1500.0, remaining_value=54000.0, depreciated_value=4000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=1500.0, remaining_value=52500.0, depreciated_value=5500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=1500.0, remaining_value=51000.0, depreciated_value=7000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1500.0, remaining_value=49500.0, depreciated_value=8500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1500.0, remaining_value=48000.0, depreciated_value=10000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1500.0, remaining_value=46500.0, depreciated_value=11500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1500.0, remaining_value=45000.0, depreciated_value=13000.0, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1500.0, remaining_value=43500.0, depreciated_value=14500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1500.0, remaining_value=42000.0, depreciated_value=16000.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1050.0, remaining_value=40950.0, depreciated_value=17050.0, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1050.0, remaining_value=39900.0, depreciated_value=18100.0, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1050.0, remaining_value=38850.0, depreciated_value=19150.0, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1050.0, remaining_value=37800.0, depreciated_value=20200.0, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1050.0, remaining_value=36750.0, depreciated_value=21250.0, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1050.0, remaining_value=35700.0, depreciated_value=22300.0, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1050.0, remaining_value=34650.0, depreciated_value=23350.0, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1050.0, remaining_value=33600.0, depreciated_value=24400.0, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1050.0, remaining_value=32550.0, depreciated_value=25450.0, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1050.0, remaining_value=31500.0, depreciated_value=26500.0, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1050.0, remaining_value=30450.0, depreciated_value=27550.0, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1050.0, remaining_value=29400.0, depreciated_value=28600.0, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=735.0, remaining_value=28665.0, depreciated_value=29335.0, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=735.0, remaining_value=27930.0, depreciated_value=30070.0, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=735.0, remaining_value=27195.0, depreciated_value=30805.0, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=735.0, remaining_value=26460.0, depreciated_value=31540.0, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=735.0, remaining_value=25725.0, depreciated_value=32275.0, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=735.0, remaining_value=24990.0, depreciated_value=33010.0, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=735.0, remaining_value=24255.0, depreciated_value=33745.0, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=735.0, remaining_value=23520.0, depreciated_value=34480.0, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=735.0, remaining_value=22785.0, depreciated_value=35215.0, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=735.0, remaining_value=22050.0, depreciated_value=35950.0, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=735.0, remaining_value=21315.0, depreciated_value=36685.0, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=735.0, remaining_value=20580.0, depreciated_value=37420.0, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=514.5, remaining_value=20065.5, depreciated_value=37934.5, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=514.5, remaining_value=19551.0, depreciated_value=38449.0, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=514.5, remaining_value=19036.5, depreciated_value=38963.5, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=514.5, remaining_value=18522.0, depreciated_value=39478.0, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=514.5, remaining_value=18007.5, depreciated_value=39992.5, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=514.5, remaining_value=17493.0, depreciated_value=40507.0, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=514.5, remaining_value=16978.5, depreciated_value=41021.5, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=514.5, remaining_value=16464.0, depreciated_value=41536.0, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=514.5, remaining_value=15949.5, depreciated_value=42050.5, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=514.5, remaining_value=15435.0, depreciated_value=42565.0, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=514.5, remaining_value=14920.5, depreciated_value=43079.5, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=514.5, remaining_value=14406.0, depreciated_value=43594.0, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=360.15, remaining_value=14045.85, depreciated_value=43954.15, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=360.15, remaining_value=13685.70, depreciated_value=44314.30, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=360.15, remaining_value=13325.55, depreciated_value=44674.45, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=360.15, remaining_value=12965.40, depreciated_value=45034.60, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=360.15, remaining_value=12605.25, depreciated_value=45394.75, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=360.15, remaining_value=12245.10, depreciated_value=45754.90, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=360.15, remaining_value=11884.95, depreciated_value=46115.05, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=360.15, remaining_value=11524.80, depreciated_value=46475.20, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=360.15, remaining_value=11164.65, depreciated_value=46835.35, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=360.15, remaining_value=10804.50, depreciated_value=47195.50, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=360.15, remaining_value=10444.35, depreciated_value=47555.65, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=10444.35, remaining_value=0, depreciated_value=58000, state='draft'),
        ])

    def test_degressive_purchase_60_months_no_prorata_with_salvage_value_asset(self):
        self.car.write({
            'method_number': 60,
            'method_period': '1',
            'method': 'degressive',
            'method_progress_factor': 0.3,
            'salvage_value': 2000,
        })
        self.car.validate()
        self.assertEqual(self.car.state, 'open')
        self.assertEqual(self.car.book_value, 26157)
        self.assertEqual(self.car.value_residual, 24157)
        self.assertRecordValues(self.car.depreciation_move_ids, [
            # 2020
            self._get_depreciation_move_values(date='2020-01-31', depreciation_value=1450.0, remaining_value=56550.0, depreciated_value=1450.0, state='posted'),
            self._get_depreciation_move_values(date='2020-02-29', depreciation_value=1450.0, remaining_value=55100.0, depreciated_value=2900.0, state='posted'),
            self._get_depreciation_move_values(date='2020-03-31', depreciation_value=1450.0, remaining_value=53650.0, depreciated_value=4350.0, state='posted'),
            self._get_depreciation_move_values(date='2020-04-30', depreciation_value=1450.0, remaining_value=52200.0, depreciated_value=5800.0, state='posted'),
            self._get_depreciation_move_values(date='2020-05-31', depreciation_value=1450.0, remaining_value=50750.0, depreciated_value=7250.0, state='posted'),
            self._get_depreciation_move_values(date='2020-06-30', depreciation_value=1450.0, remaining_value=49300.0, depreciated_value=8700.0, state='posted'),
            self._get_depreciation_move_values(date='2020-07-31', depreciation_value=1450.0, remaining_value=47850.0, depreciated_value=10150.0, state='posted'),
            self._get_depreciation_move_values(date='2020-08-31', depreciation_value=1450.0, remaining_value=46400.0, depreciated_value=11600.0, state='posted'),
            self._get_depreciation_move_values(date='2020-09-30', depreciation_value=1450.0, remaining_value=44950.0, depreciated_value=13050.0, state='posted'),
            self._get_depreciation_move_values(date='2020-10-31', depreciation_value=1450.0, remaining_value=43500.0, depreciated_value=14500.0, state='posted'),
            self._get_depreciation_move_values(date='2020-11-30', depreciation_value=1450.0, remaining_value=42050.0, depreciated_value=15950.0, state='posted'),
            self._get_depreciation_move_values(date='2020-12-31', depreciation_value=1450.0, remaining_value=40600.0, depreciated_value=17400.0, state='posted'),
            # 2021
            self._get_depreciation_move_values(date='2021-01-31', depreciation_value=1015.0, remaining_value=39585.0, depreciated_value=18415.0, state='posted'),
            self._get_depreciation_move_values(date='2021-02-28', depreciation_value=1015.0, remaining_value=38570.0, depreciated_value=19430.0, state='posted'),
            self._get_depreciation_move_values(date='2021-03-31', depreciation_value=1015.0, remaining_value=37555.0, depreciated_value=20445.0, state='posted'),
            self._get_depreciation_move_values(date='2021-04-30', depreciation_value=1015.0, remaining_value=36540.0, depreciated_value=21460.0, state='posted'),
            self._get_depreciation_move_values(date='2021-05-31', depreciation_value=1015.0, remaining_value=35525.0, depreciated_value=22475.0, state='posted'),
            self._get_depreciation_move_values(date='2021-06-30', depreciation_value=1015.0, remaining_value=34510.0, depreciated_value=23490.0, state='posted'),
            self._get_depreciation_move_values(date='2021-07-31', depreciation_value=1015.0, remaining_value=33495.0, depreciated_value=24505.0, state='posted'),
            self._get_depreciation_move_values(date='2021-08-31', depreciation_value=1015.0, remaining_value=32480.0, depreciated_value=25520.0, state='posted'),
            self._get_depreciation_move_values(date='2021-09-30', depreciation_value=1015.0, remaining_value=31465.0, depreciated_value=26535.0, state='posted'),
            self._get_depreciation_move_values(date='2021-10-31', depreciation_value=1015.0, remaining_value=30450.0, depreciated_value=27550.0, state='posted'),
            self._get_depreciation_move_values(date='2021-11-30', depreciation_value=1015.0, remaining_value=29435.0, depreciated_value=28565.0, state='posted'),
            self._get_depreciation_move_values(date='2021-12-31', depreciation_value=1015.0, remaining_value=28420.0, depreciated_value=29580.0, state='posted'),
            # 2022
            self._get_depreciation_move_values(date='2022-01-31', depreciation_value=710.5, remaining_value=27709.5, depreciated_value=30290.5, state='posted'),
            self._get_depreciation_move_values(date='2022-02-28', depreciation_value=710.5, remaining_value=26999.0, depreciated_value=31001.0, state='posted'),
            self._get_depreciation_move_values(date='2022-03-31', depreciation_value=710.5, remaining_value=26288.5, depreciated_value=31711.5, state='posted'),
            self._get_depreciation_move_values(date='2022-04-30', depreciation_value=710.5, remaining_value=25578.0, depreciated_value=32422.0, state='posted'),
            self._get_depreciation_move_values(date='2022-05-31', depreciation_value=710.5, remaining_value=24867.5, depreciated_value=33132.5, state='posted'),
            self._get_depreciation_move_values(date='2022-06-30', depreciation_value=710.5, remaining_value=24157.0, depreciated_value=33843.0, state='posted'),
            self._get_depreciation_move_values(date='2022-07-31', depreciation_value=710.5, remaining_value=23446.5, depreciated_value=34553.5, state='draft'),
            self._get_depreciation_move_values(date='2022-08-31', depreciation_value=710.5, remaining_value=22736.0, depreciated_value=35264.0, state='draft'),
            self._get_depreciation_move_values(date='2022-09-30', depreciation_value=710.5, remaining_value=22025.5, depreciated_value=35974.5, state='draft'),
            self._get_depreciation_move_values(date='2022-10-31', depreciation_value=710.5, remaining_value=21315.0, depreciated_value=36685.0, state='draft'),
            self._get_depreciation_move_values(date='2022-11-30', depreciation_value=710.5, remaining_value=20604.5, depreciated_value=37395.5, state='draft'),
            self._get_depreciation_move_values(date='2022-12-31', depreciation_value=710.5, remaining_value=19894.0, depreciated_value=38106.0, state='draft'),
            # 2023
            self._get_depreciation_move_values(date='2023-01-31', depreciation_value=497.35, remaining_value=19396.65, depreciated_value=38603.35, state='draft'),
            self._get_depreciation_move_values(date='2023-02-28', depreciation_value=497.35, remaining_value=18899.30, depreciated_value=39100.70, state='draft'),
            self._get_depreciation_move_values(date='2023-03-31', depreciation_value=497.35, remaining_value=18401.95, depreciated_value=39598.05, state='draft'),
            self._get_depreciation_move_values(date='2023-04-30', depreciation_value=497.35, remaining_value=17904.60, depreciated_value=40095.40, state='draft'),
            self._get_depreciation_move_values(date='2023-05-31', depreciation_value=497.35, remaining_value=17407.25, depreciated_value=40592.75, state='draft'),
            self._get_depreciation_move_values(date='2023-06-30', depreciation_value=497.35, remaining_value=16909.90, depreciated_value=41090.10, state='draft'),
            self._get_depreciation_move_values(date='2023-07-31', depreciation_value=497.35, remaining_value=16412.55, depreciated_value=41587.45, state='draft'),
            self._get_depreciation_move_values(date='2023-08-31', depreciation_value=497.35, remaining_value=15915.20, depreciated_value=42084.80, state='draft'),
            self._get_depreciation_move_values(date='2023-09-30', depreciation_value=497.35, remaining_value=15417.85, depreciated_value=42582.15, state='draft'),
            self._get_depreciation_move_values(date='2023-10-31', depreciation_value=497.35, remaining_value=14920.50, depreciated_value=43079.50, state='draft'),
            self._get_depreciation_move_values(date='2023-11-30', depreciation_value=497.35, remaining_value=14423.15, depreciated_value=43576.85, state='draft'),
            self._get_depreciation_move_values(date='2023-12-31', depreciation_value=497.35, remaining_value=13925.80, depreciated_value=44074.20, state='draft'),
            # 2024
            self._get_depreciation_move_values(date='2024-01-31', depreciation_value=348.15, remaining_value=13577.65, depreciated_value=44422.35, state='draft'),
            self._get_depreciation_move_values(date='2024-02-29', depreciation_value=348.15, remaining_value=13229.50, depreciated_value=44770.50, state='draft'),
            self._get_depreciation_move_values(date='2024-03-31', depreciation_value=348.15, remaining_value=12881.35, depreciated_value=45118.65, state='draft'),
            self._get_depreciation_move_values(date='2024-04-30', depreciation_value=348.15, remaining_value=12533.20, depreciated_value=45466.80, state='draft'),
            self._get_depreciation_move_values(date='2024-05-31', depreciation_value=348.15, remaining_value=12185.05, depreciated_value=45814.95, state='draft'),
            self._get_depreciation_move_values(date='2024-06-30', depreciation_value=348.15, remaining_value=11836.90, depreciated_value=46163.10, state='draft'),
            self._get_depreciation_move_values(date='2024-07-31', depreciation_value=348.15, remaining_value=11488.75, depreciated_value=46511.25, state='draft'),
            self._get_depreciation_move_values(date='2024-08-31', depreciation_value=348.15, remaining_value=11140.60, depreciated_value=46859.40, state='draft'),
            self._get_depreciation_move_values(date='2024-09-30', depreciation_value=348.15, remaining_value=10792.45, depreciated_value=47207.55, state='draft'),
            self._get_depreciation_move_values(date='2024-10-31', depreciation_value=348.15, remaining_value=10444.30, depreciated_value=47555.70, state='draft'),
            self._get_depreciation_move_values(date='2024-11-30', depreciation_value=348.15, remaining_value=10096.15, depreciated_value=47903.85, state='draft'),
            self._get_depreciation_move_values(date='2024-12-31', depreciation_value=10096.15, remaining_value=0, depreciated_value=58000, state='draft'),
        ])

    # TODO add more tests for:
    # 1. Test creation of asset from bill/refund
    # 2. Test Wizard action (Sell/dispose/modify/pause/resume)
    # 3.
