/** @odoo-module */

import { fsmProductMakeViewParams } from '@industry_fsm_sale/../tests/fsm_product_quantity_tests';

const data = fsmProductMakeViewParams.serverData;
data.models['product.product'].fields.quantity_decreasable = { type: 'boolean', string: 'Quantity Decreasable' };
for (const product of data.models['product.product'].records) {
    product.quantity_decreasable = true;
}

fsmProductMakeViewParams.arch = `
    <kanban
        class="o_kanban_mobile o_fsm_material_kanban"
        action="fsm_add_quantity" type="object"
        js_class="fsm_product_kanban"
    >
        <field name="quantity_decreasable" />
        <templates>
            <t t-name="kanban-box">
                <div>
                    <field name="fsm_quantity" widget="fsm_product_quantity"/>
                </div>
            </t>
        </templates>
    </kanban>
`;
