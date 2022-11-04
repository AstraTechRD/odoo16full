/** @odoo-module */

import {
    click,
    editInput,
    getFixture,
    getNodesTextContent,
    triggerEvent,
} from '@web/../tests/helpers/utils';
import {
    makeView,
    setupViewRegistries,
} from '@web/../tests/views/helpers';

import { getFirstElementForXpath } from '@project/../tests/project_test_utils';

let target;

export const fsmProductMakeViewParams = {
    type: 'kanban',
    resModel: 'product.product',
    serverData: {
        models: {
            'product.product': {
                fields: {
                    fsm_quantity: { string: "Material Quantity", type: 'integer' },
                },
                records: [
                    { id: 1, fsm_quantity: 0.00 },
                    { id: 2, fsm_quantity: 0.00 },
                    { id: 3, fsm_quantity: 1.00 },
                ],
            },
        },
        views: { },
    },
    arch: `
        <kanban
            class="o_kanban_mobile o_fsm_material_kanban"
            action="fsm_add_quantity" type="object"
            js_class="fsm_product_kanban"
        >
            <templates>
                <t t-name="kanban-box">
                    <div>
                        <field name="fsm_quantity" widget="fsm_product_quantity"/>
                    </div>
                </t>
            </templates>
        </kanban>
    `,
};

QUnit.module('industry_fsm_sale', {}, function () {
    QUnit.module('FSMProductQuantity', {
        beforeEach(assert) {
            this.makeViewParams = fsmProductMakeViewParams;
            this.data = this.makeViewParams.serverData;
            target = getFixture();
            setupViewRegistries();
        },
    });

    QUnit.test('fsm_product_quantity widget in kanban view', async function (assert) {
        assert.expect(6);

        await makeView(this.makeViewParams);

        assert.hasClass(target.getElementsByClassName('o_kanban_renderer'), 'o_fsm_material_kanban');
        assert.containsN(target, '.o_kanban_record:not(.o_kanban_ghost)', 3, "The number of kanban record should be equal to 3 records.");
        assert.containsN(target, '.o_kanban_record div[name="fsm_quantity"] button[name="fsm_remove_quantity"]', 3, "The number of remove button should be equal to the number of kanban records (expected 3 records).");
        assert.containsN(target, '.o_kanban_record div[name="fsm_quantity"] button[name="fsm_add_quantity"]', 3, "The number of add button should be equal to the number of kanban records (expected 3 records).");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll('.o_kanban_record div[name="fsm_quantity"] span')),
            ["0", "0", "1"],
            "The quantity of the 2 first products displayed should be equal to 0 and the quantity of the last one should be equal to 1."
        );
        assert.containsN(target, '.o_kanban_record button[name="fsm_add_quantity"] input', 0, "The number of input in the fsm product quantity should be equal to 0 since the widget is in readonly.");
    });

    QUnit.test('fsm_product_quantity: click on fsm_remove_button to decrease the quantity.', async function (assert) {
        assert.expect(5);

        await makeView({
            ...this.makeViewParams,
            async mockRPC(route, params) {
                const { args, model, method } = params;
                if (model == 'product.product' && method === 'set_fsm_quantity') {
                    const [id, quantity] = args;
                    assert.step('set_fsm_quantity');
                    assert.deepEqual(id, 3);
                    assert.strictEqual(quantity, 0.00);
                    return true;
                }
            },
        });

        assert.containsN(target, '.o_kanban_record:not(.o_kanban_ghost)', 3, "The number of kanban record should be equal to 3 records.");
        await click(target, '.o_kanban_record button[name="fsm_remove_quantity"]:not(:disabled)');
        assert.verifySteps(['set_fsm_quantity']);
    });

    QUnit.test('fsm_product_quantity: click on fsm_add_button to add a quantity unit in a product', async function (assert) {
        assert.expect(8);

        await makeView({
            ...this.makeViewParams,
            async mockRPC(route, params) {
                const { args, model, method } = params;
                if (model == 'product.product' && method === 'set_fsm_quantity') {
                    const [id, quantity] = args;
                    assert.step('set_fsm_quantity');
                    if ([1, 2].includes(id)) {
                        assert.strictEqual(quantity, 1.00);
                    } else if (id === 3) {
                        assert.strictEqual(quantity, 2.00);
                    }
                    return true;
                }
            },
        });

        assert.containsN(target, '.o_kanban_record:not(.o_kanban_ghost)', 3, "The number of kanban record should be equal to 3 records.");

        // Click on the button for each product in the kanban view
        await click(target, '.o_kanban_record:nth-child(1) button[name="fsm_add_quantity"]');
        await click(target, '.o_kanban_record:nth-child(2) button[name="fsm_add_quantity"]');
        await click(target, '.o_kanban_record:nth-child(3) button[name="fsm_add_quantity"]');
        assert.verifySteps(['set_fsm_quantity', 'set_fsm_quantity', 'set_fsm_quantity']);
    });

    QUnit.test('fsm_product_quantity: edit manually the product quantity', async function (assert) {
        assert.expect(11);

        await makeView({
            ...this.makeViewParams,
            async mockRPC(route, params) {
                const { args, model, method } = params;
                if (model == 'product.product' && method === 'set_fsm_quantity') {
                    const [id, quantity] = args;
                    assert.step('set_fsm_quantity');
                    assert.strictEqual(id, 1);
                    assert.strictEqual(quantity, 12.00);
                    return true;
                }
            },
        });

        assert.containsN(target, '.o_kanban_record:not(.o_kanban_ghost)', 3, "The number of kanban record should be equal to 3 records.");
        assert.containsN(target, '.o_kanban_record div[name="fsm_quantity"] span', 3);
        assert.containsNone(target, '.o_kanban_record div[name="fsm_quantity"] input');
        const firstFsmQuantityWidget = target.querySelector('.o_kanban_record:nth-child(1) div[name="fsm_quantity"]');
        assert.deepEqual(getNodesTextContent(firstFsmQuantityWidget.getElementsByTagName('span')), ["0"], "The product quantity should be equal to 0.");

        await click(firstFsmQuantityWidget, 'span');
        assert.containsNone(firstFsmQuantityWidget, 'span');
        assert.containsN(firstFsmQuantityWidget, 'input', 1);
        await editInput(firstFsmQuantityWidget, 'input', '12');
        await triggerEvent(firstFsmQuantityWidget, 'input', 'blur');
        assert.verifySteps(['set_fsm_quantity']);
        assert.containsNone(firstFsmQuantityWidget, 'input', 'The product quantity should not be editable.');
    });

    QUnit.skip('fsm_product_quantity: edit manually a wrong product quantity', async function (assert) {
        assert.expect(6);

        await makeView({
            ...this.makeViewParams,
            async mockRPC(route, params) {
                const { args, model, method } = params;
                if (model == 'product.product' && method === 'set_fsm_quantity') {
                    const [id, quantity] = args;
                    assert.step('set_fsm_quantity');
                    assert.strictEqual(id, 1);
                    assert.strictEqual(quantity, 12.00);
                    return true;
                }
            },
        });

        assert.containsN(target, '.o_kanban_record:not(.o_kanban_ghost)', 3, "The number of kanban record should be equal to 3 records.");
        const firstFsmQuantityWidget = target.querySelector('.o_kanban_record:nth-child(1) div[name="fsm_quantity"]');
        assert.deepEqual(getNodesTextContent(firstFsmQuantityWidget.getElementsByTagName('span')), ["0.00"], "The content of the span tag should be equal to 0.");
        assert.containsNone(firstFsmQuantityWidget, 'input', "The product quantity should not be editable.");

        await click(firstFsmQuantityWidget, 'span');
        assert.containsNone(firstFsmQuantityWidget, 'span', "The product quantity should be editable.");

        await editInput(firstFsmQuantityWidget, 'input', "12a");
        await triggerEvent(firstFsmQuantityWidget, 'input', 'blur');
        assert.verifySteps(['set_fsm_quantity']);
        assert.containsNone(firstFsmQuantityWidget, 'input', 'The product quantity should not be editable.');
    });

    QUnit.test('fsm_product_quantity: edit manually and press ENTER key to save the edition', async function (assert) {
        assert.expect(10);

        await makeView({
            ...this.makeViewParams,
            async mockRPC(route, params) {
                const { args, model, method } = params;
                if (model == 'product.product' && method === 'set_fsm_quantity') {
                    const [id, quantity] = args;
                    assert.step('set_fsm_quantity');
                    assert.strictEqual(id, 1);
                    assert.strictEqual(quantity, 42.00);
                    return true;
                }
            },
        });

        assert.containsN(target, '.o_kanban_record:not(.o_kanban_ghost)', 3, "The number of kanban record should be equal to 3 records.");
        const firstFsmQuantityWidget = target.querySelector('.o_kanban_record:nth-child(1) div[name="fsm_quantity"]');
        assert.deepEqual(getNodesTextContent(firstFsmQuantityWidget.getElementsByTagName('span')), ["0"], "The content of the span tag should be equal to 0.");
        assert.containsNone(firstFsmQuantityWidget, 'input', "The product quantity should not be editable.");

        await click(firstFsmQuantityWidget, 'span');
        assert.containsNone(firstFsmQuantityWidget, 'span', "The product quantity should be editable.");
        assert.containsN(firstFsmQuantityWidget, 'input', 1, "The product quantity should be editable.");

        await editInput(firstFsmQuantityWidget, 'input', '42');

        await triggerEvent(firstFsmQuantityWidget, 'input', 'keydown', { key: 'Enter', which: 13 });
        assert.verifySteps(['set_fsm_quantity']);
        assert.containsNone(firstFsmQuantityWidget, 'input', 'The fsm product quantity should be readonly.');
    });

    QUnit.test('fsm_product_quantity: check when the quantity in a product contains more than 5 digits, a class should be added to the span and also the input one displaying this quantity', async function (assert) {
        this.data.models['product.product'].records.push({id: 4, fsm_quantity: 123456.00}, {id: 5, fsm_quantity: 12345.00});

        await makeView(this.makeViewParams);

        assert.containsN(target, '.o_kanban_record:not(.o_kanban_ghost)', 5, "The number of kanban record should be equal to 5 records.");
        assert.containsN(target, '.o_kanban_record:not(.o_kanban_ghost) div[name="fsm_quantity"] span.small', 1, "Only one kanban record should have the `small` class in its span displayed in the fsm_product_quantity widget.");
        assert.containsNone(target, '.o_kanban_record div[name="fsm_quantity"] input', "No fsm_product_quantity widget in all kanban record should be editable.");
        const fsmProductQuantityWidgetWithSmallClass = getFirstElementForXpath(target, '//div[@name="fsm_quantity"][contains(., "123456")]');
        assert.hasClass(fsmProductQuantityWidgetWithSmallClass.querySelector('span'), 'small');

        await click(fsmProductQuantityWidgetWithSmallClass, 'span');
        assert.containsN(fsmProductQuantityWidgetWithSmallClass, 'input.small', 1, 'The fsm product widget should be editable and the input tag should also have the small class.');
        assert.containsNone(target, '.o_kanban_record:not(.o_kanban_ghost) div[name="fsm_quantity"] span.small', "The product quantity with small class should be editable, that is no span should be found.");
        assert.containsN(target, '.o_kanban_record:not(.o_kanban_ghost) div[name="fsm_quantity"] input.small', 1, "The product quantity with small class should be editable, that is a kanban record should have an input tag in fsm product quantity widget with small class.");
    });
});
