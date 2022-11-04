/** @odoo-module **/

import { createWebClient, getActionManagerServerData, doAction } from "@web/../tests/webclient/helpers";
import { getFixture } from "@web/../tests/helpers/utils";

let serverData;
let target;

QUnit.module('WebMap Mobile', {
    beforeEach() {
        serverData = getActionManagerServerData();
        target = getFixture();
        Object.assign(serverData, {
            actions: {
                1: {
                    id: 1,
                    name: 'Task Action 1',
                    res_model: 'project.task',
                    type: 'ir.actions.act_window',
                    views: [[false, 'list'], [false, 'map'], [false, 'kanban'], [false, 'form']],
                },
            },
            views: {
                'project.task,false,map': `
                <map res_partner="partner_id" routing="1">
                    <field name="name" string="Project"/>
                </map>`,
                'project.task,false,list': '<tree><field name="name"/></tree>',
                'project.task,false,kanban': `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div class="oe_kanban_global_click">
                                <field name="name"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
                'project.task,false,form':
                    `<form>
                    <group>
                        <field name="display_name"/>
                    </group>
                </form>`,
                'project.task,false,search': '<search><field name="name" string="Project"/></search>',
            },
            models: {
                'project.task': {
                    fields: {
                        display_name: { string: "name", type: "char" },
                        sequence: { string: "sequence", type: "integer" },
                        partner_id: {
                            string: "partner",
                            type: "many2one",
                            relation: "res.partner",
                        },
                    },
                },
            },
        });
    },
});

QUnit.test("uses a Map(first mobile-friendly) view by default", async function (assert) {
    const webClient = await createWebClient({ serverData });
    // should open Map(first mobile-friendly) view for action
    await doAction(webClient, 1);

    assert.containsNone(target, '.o_list_view');
    assert.containsNone(target, '.o_kanban_view');
    assert.containsOnce(target, '.o_map_view');

});
