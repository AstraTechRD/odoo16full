/** @odoo-module **/

import { ChatterContainer } from '@mail/components/chatter_container/chatter_container';

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import BarcodeQuantModel from '@stock_barcode/models/barcode_quant_model';
import { bus } from 'web.core';
import config from 'web.config';
import GroupedLineComponent from '@stock_barcode/components/grouped_line';
import LineComponent from '@stock_barcode/components/line';
import PackageLineComponent from '@stock_barcode/components/package_line';
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import * as BarcodeScanner from '@web/webclient/barcode/barcode_scanner';
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { View } from "@web/views/view";

const { Component, onMounted, onPatched, onWillStart, onWillUnmount, useSubEnv } = owl;

/**
 * Main Component
 * Gather the line information.
 * Manage the scan and save process.
 */

class MainComponent extends Component {
    //--------------------------------------------------------------------------
    // Lifecycle
    //--------------------------------------------------------------------------

    setup() {
        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.notification = useService('notification');
        this.props.model = this.props.action.res_model;
        this.props.id = this.props.action.context.active_id;
        const model = this._getModel(this.props);
        useSubEnv({model});
        this._scrollBehavior = 'smooth';
        this.isMobile = config.device.isMobile;

        onWillStart(async () => {
            const barcodeData = await this.rpc(
                '/stock_barcode/get_barcode_data',
                {
                    model: this.props.model,
                    res_id: this.props.id || false,
                }
            );
            this.groups = barcodeData.groups;
            this.env.model.setData(barcodeData);
            this.env.model.on('process-action', this, this._onDoAction);
            this.env.model.on('notification', this, this._onNotification);
            this.env.model.on('refresh', this, this._onRefreshState);
            this.env.model.on('update', this, () => this.render(true));
            this.env.model.on('do-action', this, args => bus.trigger('do-action', args));
            this.env.model.on('history-back', this, () => this.env.config.historyBack());
        });

        onMounted(() => {
            bus.on('barcode_scanned', this, this._onBarcodeScanned);
            bus.on('edit-line', this, this._onEditLine);
            bus.on('exit', this, this.exit);
            bus.on('open-package', this, this._onOpenPackage);
            bus.on('refresh', this, this._onRefreshState);
            bus.on('warning', this, this._onWarning);
        });

        onWillUnmount(() => {
            bus.off('barcode_scanned', this, this._onBarcodeScanned);
            bus.off('edit-line', this, this._onEditLine);
            bus.off('exit', this, this.exit);
            bus.off('open-package', this, this._onOpenPackage);
            bus.off('refresh', this, this._onRefreshState);
            bus.off('warning', this, this._onWarning);
        });

        onPatched(() => {
            this._scrollToSelectedLine();
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get displayHeaderInfoAsColumn() {
        return this.env.model.isDone || this.env.model.isCancelled;
    }

    get displayBarcodeApplication() {
        return this.env.model.view === 'barcodeLines';
    }

    get displayBarcodeActions() {
        return this.env.model.view === 'actionsView';
    }

    get displayBarcodeLines() {
        return this.displayBarcodeApplication && this.env.model.canBeProcessed;
    }

    get displayInformation() {
        return this.env.model.view === 'infoFormView';
    }

    get displayNote() {
        return !this._hideNote && this.env.model.record.note;
    }

    get displayPackageContent() {
        return this.env.model.view === 'packagePage';
    }

    get displayProductPage() {
        return this.env.model.view === 'productPage';
    }

    get lineFormViewData() {
        const data = this.env.model.viewsWidgetData;
        data.context = data.additionalContext;
        data.resId = this._editedLineParams && this._editedLineParams.currentId;
        return data;
    }

    get highlightValidateButton() {
        return this.env.model.highlightValidateButton;
    }

    get info() {
        return this.env.model.barcodeInfo;
    }

    get isTransfer() {
        return this.currentSourceLocation && this.currentDestinationLocation;
    }

    get lines() {
        return this.env.model.groupedLines;
    }

    get mobileScanner() {
        return BarcodeScanner.isBarcodeScannerSupported();
    }

    get packageLines() {
        return this.env.model.packageLines;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _getModel(params) {
        const { rpc, orm, notification } = this;
        if (params.model === 'stock.picking') {
            return new BarcodePickingModel(params, { rpc, orm, notification });
        } else if (params.model === 'stock.quant') {
            return new BarcodeQuantModel(params, { rpc, orm, notification });
        } else {
            throw new Error('No JS model define');
        }
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    async cancel() {
        await this.env.model.save();
        const action = await this.orm.call(
            this.props.model,
            'action_cancel_from_barcode',
            [[this.props.id]]
        );
        const onClose = res => {
            if (res && res.cancelled) {
                this.env.model._cancelNotification();
                this.env.config.historyBack();
            }
        };
        bus.trigger('do-action', {
            action,
            options: {
                on_close: onClose.bind(this),
            },
        });
    }

    async openMobileScanner() {
        const barcode = await BarcodeScanner.scanBarcode();
        if (barcode) {
            this.env.model.processBarcode(barcode);
            if ('vibrate' in window.navigator) {
                window.navigator.vibrate(100);
            }
        } else {
            this.env.services.notification.notify({
                type: 'warning',
                message: this.env._t("Please, Scan again !"),
            });
        }
    }

    async exit(ev) {
        if (this.displayBarcodeApplication) {
            await this.env.model.save();
            this.env.config.historyBack();
        } else {
            this.toggleBarcodeLines();
        }
    }

    hideNote(ev) {
        this._hideNote = true;
        this.render();
    }

    async openProductPage() {
        if (!this._editedLineParams) {
            await this.env.model.save();
        }
        this.env.model.displayProductPage();
    }

    async print(action, method) {
        await this.env.model.save();
        const options = this.env.model._getPrintOptions();
        if (options.warning) {
            return this.env.model.notification.add(options.warning, { type: 'warning' });
        }
        if (!action && method) {
            action = await this.orm.call(
                this.props.model,
                method,
                [[this.props.id]]
            );
        }
        bus.trigger('do-action', { action, options });
    }

    putInPack(ev) {
        ev.stopPropagation();
        this.env.model._putInPack();
    }

    saveFormView(lineRecord) {
        const lineId = (lineRecord && lineRecord.data.id) || (this._editedLineParams && this._editedLineParams.currentId);
        const recordId = (lineRecord.resModel === this.props.model) ? lineId : undefined
        this._onRefreshState({ recordId, lineId });
    }

    toggleBarcodeActions(ev) {
        ev.stopPropagation();
        this.env.model.displayBarcodeActions();
    }

    async toggleBarcodeLines(lineId) {
        this._editedLineParams = undefined;
        await this.env.model.displayBarcodeLines(lineId);
    }

    async toggleInformation() {
        await this.env.model.save();
        this.env.model.displayInformation();
    }

    /**
     * Calls `validate` on the model and then triggers up the action because OWL
     * components don't seem able to manage wizard without doing custom things.
     *
     * @param {OdooEvent} ev
     */
    async validate(ev) {
        ev.stopPropagation();
        await this.env.model.validate();
    }

    /**
     * Handler called when a barcode is scanned.
     *
     * @private
     * @param {string} barcode
     */
    _onBarcodeScanned(barcode) {
        if (this.displayBarcodeApplication) {
            this.env.model.processBarcode(barcode);
        }
    }

    _scrollToSelectedLine() {
        if (!this.displayBarcodeLines) {
            this._scrollBehavior = 'auto';
            return;
        }
        let selectedLine = document.querySelector('.o_sublines .o_barcode_line.o_highlight');
        const isSubline = Boolean(selectedLine);
        if (!selectedLine) {
            selectedLine = document.querySelector('.o_barcode_line.o_highlight');
        }
        if (!selectedLine) {
            const matchingLine = this.env.model.findLineForCurrentLocation();
            if (matchingLine) {
                selectedLine = document.querySelector(`.o_barcode_line[data-virtual-id="${matchingLine.virtual_id}"]`);
            }
        }
        if (selectedLine) {
            // If a line is selected, checks if this line is on the top of the
            // page, and if it's not, scrolls until the line is on top.
            const header = document.querySelector('.o_barcode_header');
            const lineRect = selectedLine.getBoundingClientRect();
            const navbar = document.querySelector('.o_main_navbar');
            const page = document.querySelector('.o_barcode_lines');
            // Computes the real header's height (the navbar is present if the page was refreshed).
            const headerHeight = navbar ? navbar.offsetHeight + header.offsetHeight : header.offsetHeight;
            if (lineRect.top < headerHeight || lineRect.bottom > (headerHeight + lineRect.height)) {
                let top = lineRect.top - headerHeight + page.scrollTop;
                if (isSubline) {
                    const parentLine = selectedLine.closest('.o_barcode_lines > .o_barcode_line');
                    const parentSummary = parentLine.querySelector('.o_barcode_line_summary');
                    top -= parentSummary.getBoundingClientRect().height;
                }
                page.scroll({ left: 0, top, behavior: this._scrollBehavior });
                this._scrollBehavior = 'smooth';
            }

        }
    }

    async _onDoAction(ev) {
        bus.trigger('do-action', {
            action: ev,
            options: {
                on_close: this._onRefreshState.bind(this),
            },
        });
    }

    async _onEditLine(ev) {
        let { line } = ev;
        const virtualId = line.virtual_id;
        await this.env.model.save();
        // Updates the line id if it's missing, in order to open the line form view.
        if (!line.id && virtualId) {
            line = this.env.model.pageLines.find(l => Number(l.dummy_id) === virtualId);
        }
        this._editedLineParams = this.env.model.getEditedLineParams(line);
        await this.openProductPage();
    }

    _onNotification(notifParams) {
        const { message } = notifParams;
        delete notifParams.message;
        this.env.services.notification.add(message, notifParams);
    }

    _onOpenPackage(packageId) {
        this._inspectedPackageId = packageId;
        this.env.model.displayPackagePage();
    }

    async _onRefreshState(paramsRefresh) {
        const { recordId, lineId } = paramsRefresh || {}
        const { route, params } = this.env.model.getActionRefresh(recordId);
        const result = await this.rpc(route, params);
        await this.env.model.refreshCache(result.data.records);
        await this.toggleBarcodeLines(lineId);
    }

    /**
     * Handles triggered warnings. It can happen from an onchange for example.
     *
     * @param {CustomEvent} ev
     */
    _onWarning(ev) {
        const { title, message } = ev.detail;
        this.env.services.dialog.add(ConfirmationDialog, { title, body: message });
    }
}
MainComponent.template = 'stock_barcode.MainComponent';
MainComponent.components = {
    View,
    GroupedLineComponent,
    LineComponent,
    PackageLineComponent,
    ChatterContainer,
};

registry.category("actions").add("stock_barcode_client_action", MainComponent);

export default MainComponent;
