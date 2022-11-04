/** @odoo-module **/

import FormView from 'web.FormView';
import KanbanView from 'web.KanbanView';
import { createView } from 'web.test_utils';

QUnit.module("M2OResourceWidgetTestsLegacy", {
    beforeEach() {
        this.data = {
            planning: {
                fields: {
                    display_name: { string: "Resource Type", type: "char" },
                    resource_type: { string: "Resource Type", type: "selection" },
                    resource_id: { string: "Resource", type: 'many2one', relation: 'resource' },
                },
                records: [{
                    id: 1,
                    display_name: "Planning Slot",
                    resource_id: 1,
                    resource_type: 'material',
                }, {
                    id: 2,
                    display_name: "Planning Slot",
                    resource_id: 2,
                    resource_type: 'human',
                }],
            },
            resource: {
                fields: {
                    name: { string: "Name", type: "char" },
                    resource_type: { string: "Resource Type", type: "selection" },
                },
                records: [{
                    id: 1,
                    name: "Continuity Tester",
                    resource_type: 'material',
                }, {
                    id: 2,
                    name: "Admin",
                    resource_type: 'human',
                }],
            },
        };
    },
}, () => {
    QUnit.test('many2one_avatar_resource widget in form view', async function (assert) {
        assert.expect(1);

        const form = await createView({
            View: FormView,
            model: 'planning',
            data: this.data,
            arch:
                `<form js_class="form_legacy" string="Partners">
                    <field name="display_name"/>
                    <field name="resource_id" widget="many2one_avatar_resource"/>
                </form>`,
            res_id: 1,
        });
        assert.hasClass(
            form.el.querySelector('.o_material_resource'),
            'o_material_resource',
            "material icon should be displayed"
        );
        form.destroy();
    });

    QUnit.test('many2one_avatar_resource widget in kanban view', async function (assert) {
        assert.expect(4);

        const kanban = await createView({
            View: KanbanView,
            model: 'planning',
            data: this.data,
            arch: `<kanban js_class="kanban_legacy">
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="resource_id" widget="many2one_avatar_resource" options="{'hide_label': true}"/></div>
                        </t>
                    </templates>
                </kanban>`,
        });

        assert.containsN(kanban, '.o_m2o_avatar', 2);
        assert.hasClass(
            kanban.$('.o_m2o_avatar:nth(0) > span'),
            'o_material_resource',
            "material icon should be displayed"
        );
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(0)>span:nth(1)').text(), '');
        assert.strictEqual(kanban.$('.o_m2o_avatar:nth(1) > img').data('src'), '/web/image/resource/2/avatar_128');
        kanban.destroy();
    });
});
