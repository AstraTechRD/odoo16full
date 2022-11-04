/** @odoo-module */

import { useDraggable } from "@web/core/utils/draggable";
import { closest, touching } from "@web/core/utils/ui";
import { formView } from "@web/views/form/form_view";
import * as formEditorRendererComponents from "@web_studio/client_action/view_editors/form/form_editor_renderer/form_editor_renderer_components";
import {
    cleanHooks,
    getActiveHook,
    getDroppedValues,
    getHooks,
} from "@web_studio/client_action/view_editors/utils";
import { ChatterContainer, ChatterContainerHook } from "../chatter_container";
import { StudioHook } from "../studio_hook_component";
import { InnerGroup, OuterGroup } from "./form_editor_groups";

const { useRef, useEffect, useSubEnv } = owl;

const hookPositionTolerance = 50;

const components = formView.Renderer.components;

function updateCurrentElement(mainEl, currentTarget) {
    for (const el of mainEl.querySelectorAll(".o-web-studio-editor--element-clicked")) {
        el.classList.remove("o-web-studio-editor--element-clicked");
    }
    const clickable = currentTarget.closest(".o-web-studio-editor--element-clickable");
    if (clickable) {
        clickable.classList.add("o-web-studio-editor--element-clicked");
    }
}

const HOOK_CLASS_WHITELIST = [
    "o_web_studio_field_picture",
    "o_web_studio_field_html",
    "o_web_studio_field_many2many",
    "o_web_studio_field_one2many",
    "o_web_studio_field_tabs",
    "o_web_studio_field_columns",
    "o_web_studio_field_lines",
];
const HOOK_TYPE_BLACKLIST = ["genericTag", "afterGroup", "afterNotebook", "insideSheet"];

const isBlackListedHook = (draggedEl, hookEl) =>
    !HOOK_CLASS_WHITELIST.some((cls) => draggedEl.classList.contains(cls)) &&
    HOOK_TYPE_BLACKLIST.some((t) => hookEl.dataset.type === t);

function canDropNotebook(hookEl) {
    if (hookEl.dataset.type === "page") {
        return false;
    }
    if (hookEl.closest(".o_group")) {
        return false;
    }
    return true;
}

function canDropGroup(hookEl) {
    if (hookEl.dataset.type === "insideGroup") {
        return false;
    }
    if (hookEl.closest(".o_group")) {
        return false;
    }
    return true;
}

export class FormEditorRenderer extends formView.Renderer {
    setup() {
        super.setup();
        const rootRef = useRef("compiled_view_root");
        this.rootRef = rootRef;

        // Handle click on elements
        const config = Object.create(this.env.config);
        const originalNodeClicked = config.onNodeClicked;
        config.onNodeClicked = (params) => {
            updateCurrentElement(rootRef.el, params.target);
            return originalNodeClicked(params);
        };
        useSubEnv({ config });

        // Prepare a legacy handler for JQuery UI's droppable
        const onLegacyDropped = (ev, ui) => {
            const hitHook = getActiveHook(rootRef.el);
            if (!hitHook) {
                return cleanHooks(rootRef.el);
            }
            const { xpath, position } = hitHook.dataset;
            const $droppedEl = ui.draggable || $(ev.target);

            const droppedData = $droppedEl.data();
            const isNew = $droppedEl[0].classList.contains("o_web_studio_component");
            droppedData.isNew = isNew;
            // Fieldname is useless here since every dropped element is new.
            const values = getDroppedValues({ droppedData, xpath, position });
            cleanHooks(rootRef.el);
            this.env.config.structureChange(values);
        };

        // Deals with invisible modifier by reacting to config.studioShowVisible.
        useEffect(
            (rootEl, showInvisible) => {
                if (!rootEl) {
                    return;
                }
                rootEl.classList.add("o_web_studio_form_view_editor");
                if (showInvisible) {
                    rootEl
                        .querySelectorAll(
                            ":not(.o_FormRenderer_chatterContainer) .o_invisible_modifier"
                        )
                        .forEach((el) => {
                            el.classList.add("o_web_studio_show_invisible");
                            el.classList.remove("o_invisible_modifier");
                        });
                } else {
                    rootEl
                        .querySelectorAll(
                            ":not(.o_FormRenderer_chatterContainer) .o_web_studio_show_invisible"
                        )
                        .forEach((el) => {
                            el.classList.remove("o_web_studio_show_invisible");
                            el.classList.add("o_invisible_modifier");
                        });
                }

                // FIXME: legacy: interoperability with legacy studio components
                $(rootEl).droppable({
                    accept: ".o_web_studio_component",
                    drop: onLegacyDropped,
                });
                return () => {
                    $(rootEl).droppable("destroy");
                };
            },
            () => [rootRef.el, this.env.config.studioShowInvisible]
        );

        // do this in another way?
        useEffect(
            (rootEl) => {
                if (rootEl) {
                    const optCols = rootEl.querySelectorAll("i.o_optional_columns_dropdown_toggle");
                    for (const col of optCols) {
                        col.classList.add("text-muted");
                    }
                }
            },
            () => [rootRef.el]
        );

        // A function that highlights relevant areas when dragging a component/field
        const highlightNearestHook = (draggedEl, { x, y }) => {
            cleanHooks(rootRef.el);

            const mouseToleranceRect = {
                x: x - hookPositionTolerance,
                y: y - hookPositionTolerance,
                width: hookPositionTolerance * 2,
                height: hookPositionTolerance * 2,
            };

            const touchingEls = touching(getHooks(rootRef.el), mouseToleranceRect);
            const closestHookEl = closest(touchingEls, { x, y });

            if (!closestHookEl) {
                return false;
            }

            const draggingStructure = draggedEl.dataset.studioStructure;
            switch (draggingStructure) {
                case "notebook": {
                    if (!canDropNotebook(closestHookEl)) {
                        return false;
                    }
                    break;
                }
                case "group": {
                    if (!canDropGroup(closestHookEl)) {
                        return false;
                    }
                    break;
                }
            }
            if (isBlackListedHook(draggedEl, closestHookEl)) {
                return false;
            }
            closestHookEl.classList.add("o_web_studio_nearest_hook");
            return true;
        };

        this.env.config.registerCallback("highlightNearestHook", highlightNearestHook);

        useDraggable({
            ref: rootRef,
            elements: ".o-draggable",
            onDragStart({ element }) {
                element.classList.add("o-draggable--dragging");
            },
            onDrag({ x, y, element }) {
                element.classList.remove("o-draggable--drop-ready");
                if (highlightNearestHook(element, { x, y })) {
                    element.classList.add("o-draggable--drop-ready");
                }
            },
            onDragEnd({ element }) {
                element.classList.remove("o-draggable--dragging");
            },
            onDrop: ({ element }) => {
                const targetHook = getActiveHook(rootRef.el);
                if (!targetHook) {
                    return;
                }
                const { xpath, position } = targetHook.dataset;
                const droppedData = element.dataset;
                const values = getDroppedValues({ droppedData, xpath, position });

                cleanHooks(rootRef.el);

                if (!values) {
                    return;
                }
                this.env.config.structureChange(values);
            },
        });

        this.env.config.registerCallback("selectField", (fName) => {
            const fieldElement = rootRef.el.querySelector(`.o_field_widget[name="${fName}"]`);
            if (fieldElement) {
                fieldElement.click();
            }
        });
    }
}

FormEditorRenderer.components = {
    ...components,
    ...formEditorRendererComponents,
    ChatterContainer,
    ChatterContainerHook,
    InnerGroup,
    OuterGroup,
    StudioHook,
};
