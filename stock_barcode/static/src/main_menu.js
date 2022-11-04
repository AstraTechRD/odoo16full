/** @odoo-module **/

import * as BarcodeScanner from '@web/webclient/barcode/barcode_scanner';
import { bus } from 'web.core';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onMounted, onWillUnmount, onWillStart, useState } = owl;

export class MainMenu extends Component {
    setup() {
        const displayDemoMessage = this.props.action.params.message_demo_barcodes;
        const user = useService('user');
        this.actionService = useService('action');
        this.dialogService = useService('dialog');
        this.home = useService("home_menu");
        this.notificationService = useService("notification");
        this.rpc = useService('rpc');
        this.state = useState({ displayDemoMessage });

        this.mobileScanner = BarcodeScanner.isBarcodeScannerSupported();

        onWillStart(async () => {
            this.locationsEnabled = await user.hasGroup('stock.group_stock_multi_locations');
            this.packagesEnabled = await user.hasGroup('stock.group_tracking_lot');
        });
        onMounted(() => {
            bus.on('barcode_scanned', this, this._onBarcodeScanned);
        });
        onWillUnmount(() => {
            bus.off('barcode_scanned', this, this._onBarcodeScanned);
        });
    }

    async openMobileScanner() {
        const barcode = await BarcodeScanner.scanBarcode();
        if (barcode){
            this._onBarcodeScanned(barcode);
            if ('vibrate' in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.notificationService.add(this.env._t("Please, Scan again !"), { type: 'warning' });
        }
    }

    removeDemoMessage() {
        this.state.displayDemoMessage = false;
        const params = {
            title: this.env._t("Don't show this message again"),
            body: this.env._t("Do you want to permanently remove this message ?\
                    It won't appear anymore, so make sure you don't need the barcodes sheet or you have a copy."),
            confirm: () => {
                this.rpc('/stock_barcode/rid_of_message_demo_barcodes');
                location.reload();
            },
            cancel: () => {},
            confirmLabel: this.env._t("Remove it"),
            cancelLabel: this.env._t("Leave it"),
        };
        this.dialogService.add(ConfirmationDialog, params);
    }

    async _onBarcodeScanned(barcode) {
        const res = await this.rpc('/stock_barcode/scan_from_main_menu', { barcode });
        if (res.action) {
            return this.actionService.doAction(res.action);
        }
        this.notificationService.add(res.warning, { type: 'danger' });
    }
}
MainMenu.template = 'stock_barcode.MainMenu';

registry.category('actions').add('stock_barcode_main_menu', MainMenu);
