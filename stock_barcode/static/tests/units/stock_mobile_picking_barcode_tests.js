odoo.define('stock_mobile_barcode.stock_picking_barcode_tests', function (require) {
"use strict";

const { mock } = require('web.test_utils');
const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');
const BarcodeScanner = require('@web/webclient/barcode/barcode_scanner');
const { destroy, getFixture } = require("@web/../tests/helpers/utils");

QUnit.module('stock_mobile_barcode', {}, function () {

QUnit.module('Barcode', {
    beforeEach: function () {
        var self = this;

        this.clientData = {
            action: {
                tag: 'stock_barcode_client_action',
                type: 'ir.actions.client',
                res_model: "stock.picking",
                context: {},
            },
            currentState: {
                actions: {},
                data: {
                    records: {
                        'barcode.nomenclature': [{
                            id: 1,
                            rule_ids: [],
                        }],
                        'stock.location': [],
                        'stock.move.line': [],
                        'stock.picking': [],
                    },
                    nomenclature_id: 1,
                },
                groups: {},
            },
        };
        this.mockRPC = function (route, args) {
            if (route === '/stock_barcode/get_barcode_data') {
                return Promise.resolve(self.clientData.currentState);
            } else if (route === '/stock_barcode/static/img/barcode.svg') {
                return Promise.resolve();
            }
        };
    }
});

QUnit.test('scan barcode button in mobile device', async function (assert) {
    assert.expect(1);
    const pickingRecord = {
        id: 2,
        state: 'done',
        move_line_ids: [],
    };
    this.clientData.action.context.active_id = pickingRecord.id;
    this.clientData.currentState.data.records['stock.picking'].push(pickingRecord);
    this.clientData.currentState.groups.group_stock_multi_locations = false;

    mock.patch(BarcodeScanner, {
        isBarcodeScannerSupported: () => true,
        scanBarcode: async () => {},
    });

    const target = getFixture();

    const webClient = await createWebClient({
        mockRPC: this.mockRPC,
    });
    await doAction(webClient, this.clientData.action);
    assert.containsOnce(target, '.o_stock_mobile_barcode');
    destroy(webClient);
    mock.unpatch(BarcodeScanner);
});

});
});
