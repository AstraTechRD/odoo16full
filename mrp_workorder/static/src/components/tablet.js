/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { View } from "@web/views/view";
import DocumentViewer from '@mrp_workorder/components/viewer';
import StepComponent from '@mrp_workorder/components/step';
import ViewsWidgetAdapter from '@mrp_workorder/components/views_widget_adapter';
import MenuPopup from '@mrp_workorder/components/menuPopup';
import SummaryStep from '@mrp_workorder/components/summary_step';

const { EventBus, useState, useEffect, onWillStart, Component, markup} = owl;

/**
 * Main Component
 * Gather the workorder and its quality check information.
 */

class Tablet extends Component {
    //--------------------------------------------------------------------------
    // Lifecycle
    //--------------------------------------------------------------------------
    setup() {
        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.notification = useService('notification');
        this.state = useState({
            selectedStepId: 0,
            workingState: "",
        });

        this.popup = useState({
            menu: {
                isShown: false,
                data: {},
            }
        });
        this.workorderId = this.props.action.context.active_id;
        this.additionalContext = this.props.action.context;
        this.workorderBus = new EventBus();
        useBus(this.workorderBus, "refresh", async () => {
            await this.getState();
            this.render();
        });
        useBus(this.workorderBus, "workorder_event", (ev) => {
            this[ev.detail]();
        });
        this.barcode = useService('barcode');
        useBus(this.barcode.bus, 'barcode_scanned', (event) => this._onBarcodeScanned(event.detail.barcode));
        onWillStart(async () => {
            await this._onWillStart();
        });

        useEffect(() => {
            this._scrollToHighlighted();
        });
    }

    _scrollToHighlighted() {
        let selectedLine = document.querySelector('.o_tablet_timeline .o_tablet_step.o_selected');
        if (selectedLine) {
            // If a line is selected, checks if this line is entirely visible
            // and if it's not, scrolls until the line is.
            const headerHeight = document.querySelector('.o_form_view').offsetHeight.height;
            const lineRect = selectedLine.getBoundingClientRect();
            const page = document.querySelector('.o_tablet_timeline');
            // Computes the real header's height (the navbar is present if the page was refreshed).
            let scrollCoordY = false;
            if (lineRect.top < headerHeight) {
                scrollCoordY = lineRect.top - headerHeight + page.scrollTop;
            } else if (lineRect.bottom > window.innerHeight) {
                const pageRect = page.getBoundingClientRect();
                scrollCoordY = page.scrollTop - (pageRect.bottom - lineRect.bottom);
            }
            if (scrollCoordY !== false) { // Scrolls to the line only if it's not entirely visible.
                page.scroll({ left: 0, top: scrollCoordY, behavior: this._scrollBehavior });
                this._scrollBehavior = 'smooth';
            }
        }
    }

    async getState() {
        this.data = await this.orm.call(
            'mrp.workorder',
            'get_workorder_data',
            [this.workorderId],
        );
        this.viewsId = this.data['views'];
        this.steps = this.data['quality.check'];
        this.state.workingState = this.data.working_state;
        if (this.steps.length && this.steps.every(step => step.quality_state !== 'none')) {
            this.createSummaryStep();
        } else {
            this.state.selectedStepId = this.data['mrp.workorder'].current_quality_check_id;
        }
    }

    createSummaryStep() {
        this.steps.push({
            id: 0,
            title: 'Summary',
            test_type: '',
        });
        this.state.selectedStepId = 0;
    }

    async selectStep(id) {
        await this.saveCurrentStep(id);
    }

    async saveCurrentStep(newId) {
        await new Promise((resolve) =>
            this.workorderBus.trigger("force_save_workorder", { resolve })
        );
        if (this.state.selectedStepId) {
            await new Promise((resolve) =>
                this.workorderBus.trigger("force_save_check", { resolve })
            );
        }
        await this.orm.write("mrp.workorder", [this.workorderId], {
            current_quality_check_id: newId,
        });
        this.state.selectedStepId = newId;
    }

    get worksheetData() {
        if (this.selectedStep) {
            if (this.selectedStep.worksheet_document) {
                return {
                    resModel: 'quality.check',
                    resId: this.state.selectedStepId,
                    resField: 'worksheet_document',
                    value: this.selectedStep.worksheet_document,
                    page: 1,
                };
            } else if (this.selectedStep.worksheet_url) {
                return {
                    resModel: "quality.point",
                    resId: this.selectedStep.point_id,
                    resField: "worksheet_url",
                    value: this.selectedStep.worksheet_url,
                    page: 1,
                };
            } else if (this.data.operation !== undefined && this.selectedStep.worksheet_page) {
                if (this.data.operation.worksheet) {
                    return {
                        resModel: "mrp.routing.workcenter",
                        resId: this.data.operation.id,
                        resField: "worksheet",
                        value: this.data.operation.worksheet,
                        page: this.selectedStep.worksheet_page,
                    };
                } else if (this.data.operation.worksheet_url) {
                    return {
                        resModel: "mrp.routing.workcenter",
                        resId: this.data.operation.id,
                        resField: "worksheet_url",
                        value: this.data.operation.worksheet_url,
                        page: this.selectedStep.worksheet_page,
                    };
                } else {
                    return false;
                }
            } else {
                return false;
            }
        } else if (this.data.operation.worksheet) {
            return {
                resModel: 'mrp.routing.workcenter',
                resId: this.data.operation.id,
                resField: 'worksheet',
                value: this.data.operation.worksheet,
                page: 1,
            };
        } else {
            return false;
        }
    }

    get selectedStep() {
        return this.state.selectedStepId && this.steps.find(
            l => l.id === this.state.selectedStepId
        );
    }

    get views() {
        const data = {
            workorder: {
                type: 'workorder_form',
                mode: 'edit',
                resModel: 'mrp.workorder',
                viewId: this.viewsId.workorder,
                resId: this.workorderId,
                display: { controlPanel: false },
                workorderBus: this.workorderBus,
            },
            check: {
                type: 'workorder_form',
                mode: 'edit',
                resModel: 'quality.check',
                viewId: this.viewsId.check,
                resId: this.state.selectedStepId,
                display: { controlPanel: false },
                workorderBus: this.workorderBus,
            },
        };
        return data;
    }

    get checkInstruction() {
        let note = this.data['mrp.workorder'].operation_note;
        if (note && note !== '<p><br></p>') {
            return markup(note);
        } else {
            return undefined;
        }
    }

    get isBlocked() {
        return this.state.workingState === 'blocked';
    }

    showPopup(props, popupId) {
        this.popup[popupId].isShown = true;
        this.popup[popupId].data = props;
    }

    closePopup(popupId) {
        this.getState();
        this.popup[popupId].isShown = false;
    }

    async onCloseRerender(message) {
        if (message) {
            this.notification.add(this.env._t(message), {type: 'success'});
        }
        await this.getState();
        this.render();
    }

    openMenuPopup() {
        this.showPopup({
            title: 'Menu',
            workcenterId: this.data['mrp.workorder'].workcenter_id,
            selectedStepId: this.state.selectedStepId,
            workorderId: this.workorderId,
        }, 'menu');
    }

    async _onWillStart() {
        await this.getState();
    }

    _onBarcodeScanned(barcode) {
        if (barcode.startsWith('O-BTN.') || barcode.startsWith('O-CMD.')) {
            // Do nothing. It's already handled by the barcode service.
            return;
        }
    }
}

Tablet.props = ['action', '*'];
Tablet.template = 'mrp_workorder.Tablet';
Tablet.components = {
    StepComponent,
    DocumentViewer,
    ViewsWidgetAdapter,
    MenuPopup,
    SummaryStep,
    View,
};

registry.category('actions').add('tablet_client_action', Tablet);

export default Tablet;
