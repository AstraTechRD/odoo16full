/** @odoo-module */

import { ComponentWrapper } from "web.OwlCompatibility";
import { formView } from "@web/views/form/form_view";
import { FormEditorRenderer } from "./form_editor_renderer/form_editor_renderer";
import { FormEditorController } from "./form_editor_controller/form_editor_controller";
import { FormEditorCompiler } from "./form_editor_compiler";
import { mapActiveFieldsToFieldsInfo } from "@web/views/legacy_utils";
import { OPTIONS_BY_WIDGET } from "@web_studio/legacy/js/views/view_editor_sidebar";
import { registry } from "@web/core/registry";

const formEditor = {
    ...formView,
    Compiler: FormEditorCompiler,
    Renderer: FormEditorRenderer,
    Controller: FormEditorController,
};
registry.category("studio_editors").add("form", formEditor);

function isVisible(el) {
    const style = window.getComputedStyle(el);
    return style.display !== "none";
}

class FormEditorWrapper extends ComponentWrapper {
    setup() {
        super.setup();
        const { archInfo, fields } = this.props.controllerProps;
        const { activeFields } = archInfo;
        const fieldsInfo = mapActiveFieldsToFieldsInfo(
            activeFields,
            fields,
            this.env.config.type,
            this.env
        );
        for (const viewInfo of Object.values(fieldsInfo)) {
            const _fieldsInfo = Object.values(viewInfo).filter(
                (f) => f.widget in OPTIONS_BY_WIDGET
            );
            for (const fieldInfo of _fieldsInfo) {
                const missingOptions = OPTIONS_BY_WIDGET[fieldInfo.widget].filter(
                    ({ name }) => !(name in fieldInfo.options)
                );
                for (const option of missingOptions) {
                    fieldInfo.options[option.name] = option.default;
                }
            }
        }
        this.state = {
            fieldsInfo,
            getFieldNames: () => {
                return Object.keys(activeFields);
            },
            viewType: this.env.config.type,
        };
    }
    getLocalState() {
        return {
            lastClickedXpath: this.lastClickedXpath || null,
        };
    }
    setLastClickedXpath(lastClickedXpath) {
        this.lastClickedXpath = lastClickedXpath || null;
    }
    setLocalState(state = {}) {
        this.lastClickedXpath = state.lastClickedXpath || null;
        if (!this.el) {
            return;
        }

        const lastClickedXpath = this.lastClickedXpath;
        this.unselectedElements();

        if (lastClickedXpath) {
            const el = this.el.querySelector(`[data-studio-xpath="${lastClickedXpath}"]`);
            if (el && isVisible(el)) {
                this.env.config.onNodeClicked({
                    xpath: lastClickedXpath,
                    target: el,
                });
                //////////////////
                // factorize code!
                el.closest(".o-web-studio-editor--element-clickable").classList.add(
                    "o-web-studio-editor--element-clicked"
                );
                ///////////////
                return;
            }
            this.props.resetSidebar();
        }
    }
    unselectedElements() {
        this.lastClickedXpath = null;
        const clickedEl = this.el.querySelector(".o-web-studio-editor--element-clicked");
        if (clickedEl) {
            clickedEl.classList.remove("o-web-studio-editor--element-clicked");
        }
    }
    handleDrop() {}
    highlightNearestHook($helper, position) {
        const draggedEl = $helper[0];
        const studioStructure = $helper.data("structure");
        const pos = { x: position.pageX, y: position.pageY };
        draggedEl.dataset.studioStructure = studioStructure;
        return this.env.config.executeCallback("highlightNearestHook", draggedEl, pos);
    }
    setSelectable() {}
    selectField(fName) {
        this.env.config.executeCallback("selectField", fName);
    }
}
registry.category("wowl_editors_wrappers").add("form", FormEditorWrapper);
