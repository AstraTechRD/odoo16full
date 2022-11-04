# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from . import test_common

class TestMerge(test_common.TestCommon):
    def test_generic_merge(self):
        self._create_rule('x_name', 'exact')

        rec = self._create_record('x_dm_test_model', x_name='toto')
        rec2 = self._create_record('x_dm_test_model', x_name='toto')
        ref = self._create_record('x_dm_test_model_ref', x_name='ref toto', x_test_id=rec2.id)
        self.MyModel.find_duplicates()

        groups = self.env['data_merge.group'].search([('model_id', '=', self.MyModel.id)])
        self.assertEqual(len(groups), 1, 'Should have found 1 group')

        group = groups[0]
        records = group.record_ids
        master_record = records.filtered('is_master')
        other_record = records - master_record

        self.assertEqual(master_record._original_records(), rec, "the 1st record created should be the master")
        self.assertEqual(ref.x_test_id, rec2, "The reference should be to rec2")

        group.merge_records()
        self.assertFalse(other_record.exists(), "record should be unlinked")
        self.assertEqual(ref.x_test_id, rec, "The reference should be to rec")

    def test_generic_insensitive_rule(self):
        self._create_rule('x_name', 'accent')
        for name in ('accentuée', 'accentuee', 'Accentuée', 'Accentué'):
            self._create_record('x_dm_test_model', x_name=name)
        self.MyModel.find_duplicates()

        groups = self.env['data_merge.group'].search([('model_id', '=', self.MyModel.id)])
        self.assertEqual(len(groups), 1, 'Should have found 1 group')
        self.assertEqual(len(groups.record_ids), 3, 'First group must contains three records: ("accentuée", "accentue", "Accentuée")')
        self.assertNotIn('Accentué', groups[0].record_ids.mapped('display_name'), 'Group must not contains "Accentué"')
