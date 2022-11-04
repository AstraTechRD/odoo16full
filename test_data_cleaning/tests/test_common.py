# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import unittest

from odoo.tests.common import TransactionCase


class TestCommon(TransactionCase):
    def setUp(self):
        super(TestCommon, self).setUp()

        self.Model = self.env['data_cleaning.model']
        self.Record = self.env['data_cleaning.record']
        self.Rule = self.env['data_cleaning.rule']

        self.TestModel = self.env['data_cleaning.test.model']
        self.TestDCModel = self.Model.create({
            'name': 'Test Model',
            'res_model_id': self.env['ir.model']._get('data_cleaning.test.model').id
        })

    def _create_rule(self, action, field_name, action_trim=False, action_case=False, sequence=0):
        return self.Rule.create({
            'cleaning_model_id': self.TestDCModel.id,
            'field_id': self.env['ir.model.fields']._get('data_cleaning.test.model', field_name).id,
            'action': action,
            'action_trim': action_trim,
            'action_case': action_case,
            'sequence': sequence,
        })

    def _create_record(self, model, **kwargs):
        return self.env[model].create(kwargs)
