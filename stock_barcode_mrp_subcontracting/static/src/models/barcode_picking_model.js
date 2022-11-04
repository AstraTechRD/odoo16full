/** @odoo-module **/

import BarcodePickingModel from '@stock_barcode/models/barcode_picking_model';
import { patch } from 'web.utils';
import { _t } from 'web.core';


patch(BarcodePickingModel.prototype, 'stock_barcode_mrp_subcontracting', {
    
    showSubcontractingDetails(line) {
        return line.is_subcontract_stock_barcode && !['done', 'cancel'].includes(line.state) && this.getQtyDone(line);
    },
    
    getPickingToRecordComponents() {
        const displayValues = ["hide", "facultative", "mandatory"];
        let picking = this.record;
        if (this.params.model === "stock.picking.batch") {
            const picking_id = this.record.picking_ids.reduce((prevId, currentId) => {
                const currentPicking = this.cache.getRecord("stock.picking", currentId);
                const currentValue = currentPicking.display_action_record_components;
                const prevPicking = this.cache.getRecord("stock.picking", prevId);
                const prevValue = prevPicking.display_action_record_components;
                if (displayValues.indexOf(prevValue) > displayValues.indexOf(currentValue)) {
                    return prevId;
                } else {
                    return currentId;
                }
            }, this.record.picking_ids[0]);
            picking = this.cache.getRecord("stock.picking", picking_id);
        }
        return picking;
    },

    get displayActionRecordComponents() {
        return this.getPickingToRecordComponents().display_action_record_components;
    },

    _actionRecordComponents(line) {
        const moveId = line && line.move_id || false;
        return this._getActionRecordComponents(moveId).then(
            res => this.trigger('do-action', res),
            error => this.trigger('notification', error)
        );
    },

    async _getActionRecordComponents(moveId) {
        await this.save();
        let action = false;
        if (moveId) {
            action = await this.orm.call(
                'stock.move',
                'action_show_details',
                [[moveId]]
            );
        } else {
            action = await this.orm.call(
                'stock.picking',
                'action_record_components',
                [[this.getPickingToRecordComponents().id]]
            );
        }
        if (!action) {
            return Promise.reject({
                message: _t('No components to register'),
                type: 'danger',
            });
        }
        const options = {
            on_close: () => {
                this.trigger('refresh');
            },
        };
        return { action, options };
    },

    async _getActionSubcontractingDetails(line) {
        await this.save();
        const action = await this.orm.call(
            'stock.move',
            'action_show_subcontract_details',
            [[line.move_id]]
        );
        const options = {
            on_no_action: () => {
                this.trigger('notification', {
                    message: _t('Nothing to show'),
                    type: 'danger',
                });
            }
        };
        return {action, options};
    },

    _getCommands() {
        return Object.assign(this._super(), {
            'O-BTN.record-components': this._actionRecordComponents.bind(this),
        });
    },

    async _updateLineQty(line, args) {
        // We cannot know if this particularly line is mandatory
        // In master is_subcontract_stock_barcode should be a selection like the display_action_record_components
        if (
            line.is_subcontract_stock_barcode &&
            this.displayActionRecordComponents === "mandatory"
        ) {
            await this._actionRecordComponents(line);
        } else {
            this._super(...arguments);
        }
    },
});
