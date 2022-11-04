odoo.define('web_mobile.barcode.tests', function (require) {
    "use strict";

    const fieldRegistry = require('web.field_registry');
    const FormView = require('web.FormView');
    const { FieldMany2One } = require('web.relational_fields');
    const { createView, dom, mock } = require('web.test_utils');

    const FieldMany2OneBarcode = require('web_mobile.barcode_fields');
    const BarcodeScanner = require('@web/webclient/barcode/barcode_scanner');

    const NAME_SEARCH = "name_search";
    const PRODUCT_PRODUCT = 'product.product';
    const SALE_ORDER_LINE = 'sale_order_line';
    const PRODUCT_FIELD_NAME = 'product_id';
    const ARCHS = {
        'product.product,false,list': `<tree>
                <field name="display_name"/>
        </tree>`,
        'product.product,false,search': '<search></search>',
    };

    async function mockRPC(route, args) {
        const result = await this._super(...arguments);
        if (args.method === NAME_SEARCH && args.model === PRODUCT_PRODUCT) {
            const records = this.data[PRODUCT_PRODUCT].records
                .filter((record) => record.barcode === args.kwargs.name)
                .map((record) => [record.id, record.name]);
            return records.concat(result);
        }
        return result;
    }

    QUnit.module('web_mobile', {
        beforeEach() {
            this.data = {
                [PRODUCT_PRODUCT]: {
                    fields: {
                        id: {type: 'integer'},
                        name: {},
                        barcode: {},
                    },
                    records: [{
                        id: 111,
                        name: 'product_cable_management_box',
                        barcode: '601647855631',
                    }, {
                        id: 112,
                        name: 'product_n95_mask',
                        barcode: '601647855632',
                    }, {
                        id: 113,
                        name: 'product_surgical_mask',
                        barcode: '601647855633',
                    }],
                },
                [SALE_ORDER_LINE]: {
                    fields: {
                        id: {type: 'integer'},
                        [PRODUCT_FIELD_NAME]: {
                            string: PRODUCT_FIELD_NAME,
                            type: 'many2one',
                            relation: PRODUCT_PRODUCT
                        },
                    }
                },
            };
        },
    }, function () {

        QUnit.test("web_mobile: barcode button in a mobile environment with single results", async function (assert) {
            assert.expect(2);

            // simulate a mobile environment
            fieldRegistry.add('many2one_barcode', FieldMany2OneBarcode);
            mock.patch(BarcodeScanner, {
                isBarcodeScannerSupported: () => true,
                scanBarcode: async () => this.data[PRODUCT_PRODUCT].records[0].barcode,
            });

            const form = await createView({
                View: FormView,
                arch: `
                    <form>
                        <sheet>
                            <field name="${PRODUCT_FIELD_NAME}" widget="many2one_barcode"/>
                        </sheet>
                    </form>`,
                data: this.data,
                model: SALE_ORDER_LINE,
                archs: ARCHS,
                mockRPC,
            });

            const $scanButton = form.$('.o_barcode');

            assert.containsOnce(form, $scanButton, "has scanner button");

            await dom.click($scanButton);

            const selectedId = form.renderer.state.data[PRODUCT_FIELD_NAME].res_id;
            assert.equal(selectedId, this.data[PRODUCT_PRODUCT].records[0].id,
                `product found and selected (${this.data[PRODUCT_PRODUCT].records[0].barcode})`);

            form.destroy();
            fieldRegistry.add('many2one_barcode', FieldMany2One);
            mock.unpatch(BarcodeScanner);
        });

        QUnit.test("web_mobile: barcode button in a mobile environment with multiple results", async function (assert) {
            // simulate a mobile environment
            fieldRegistry.add('many2one_barcode', FieldMany2OneBarcode);
            mock.patch(BarcodeScanner, {
                isBarcodeScannerSupported: () => true,
                scanBarcode: async () => "mask"
            });

            const form = await createView({
                View: FormView,
                arch: `
                    <form>
                        <sheet>
                            <field name="${PRODUCT_FIELD_NAME}" widget="many2one_barcode"/>
                        </sheet>
                    </form>`,
                data: this.data,
                model: SALE_ORDER_LINE,
                archs: ARCHS,
                mockRPC,
            });

            const $scanButton = form.$('.o_barcode');

            assert.containsOnce(form, $scanButton, "has scanner button");

            await dom.click($scanButton);

            const $modal = $('.modal-dialog.modal-lg');
            assert.containsOnce($('body'), $modal, 'there should be one modal opened in full screen');

            assert.containsN($modal, '.o_legacy_list_view .o_data_row', 2,
                'there should be 2 records displayed');

            await dom.click($modal.find('.o_legacy_list_view .o_data_row:first'));

            const selectedId = form.renderer.state.data[PRODUCT_FIELD_NAME].res_id;
            assert.equal(selectedId, this.data[PRODUCT_PRODUCT].records[1].id,
                `product found and selected (${this.data[PRODUCT_PRODUCT].records[1].barcode})`);

            form.destroy();
            fieldRegistry.add('many2one_barcode', FieldMany2One);
            mock.unpatch(BarcodeScanner);
        });
    });
});
