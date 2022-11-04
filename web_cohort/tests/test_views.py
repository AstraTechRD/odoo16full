from odoo.addons.base.tests.test_views import ViewCase


class TestViews(ViewCase):
    def test_get_views_model_fields(self):
        model = self.env.ref('base.model_ir_ui_view')
        self.env['ir.model.fields'].create([
            {'model_id': model.id, 'name': 'x_date_start', 'ttype': 'datetime'},
            {'model_id': model.id, 'name': 'x_date_stop', 'ttype': 'datetime'},
        ])

        view = self.assertValid(
            """
                <cohort string="foo" date_start="x_date_start" date_stop="x_date_stop" interval="week" mode="churn" sample="1">
                    <field name="priority"/>
                </cohort>
            """
        )

        views = self.View.get_views([(view.id, 'cohort')])
        self.assertTrue('x_date_start' in views['models']['ir.ui.view'])
        self.assertTrue('x_date_start' in views['models']['ir.ui.view'])
