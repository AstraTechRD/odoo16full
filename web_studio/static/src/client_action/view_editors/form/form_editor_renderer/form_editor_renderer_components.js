/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";
import { FieldContentOverlay } from "./field_content_overlay";
import { formView } from "@web/views/form/form_view";
import { StudioHook } from "../studio_hook_component";
import { studioIsVisible } from "@web_studio/client_action/view_editors/utils";
import { useService } from "@web/core/utils/hooks";
import { fieldVisualFeedback } from "@web/views/fields/field";

const { useState, Component } = owl;

export function useStudioRef(refName = "studioRef", onClick) {
    // create two hooks and call them here?
    const comp = owl.useComponent();
    const ref = owl.useRef(refName);
    owl.useEffect(
        (el) => {
            if (el) {
                el.setAttribute("data-studio-xpath", comp.props.studioXpath);
            }
        },
        () => [ref.el]
    );

    if (onClick) {
        const handler = onClick.bind(comp);
        owl.useEffect(
            (el) => {
                if (el) {
                    el.addEventListener("click", handler, { capture: true });
                    return () => {
                        el.removeEventListener("click", handler);
                    };
                }
            },
            () => [ref.el]
        );
    }
}

/**
 * Overrides and extensions of components used by the FormRenderer
 * As a rule of thumb, elements should be able to handle the props
 * - studioXpath: the xpath to the node in the form's arch to which the component
 *   refers
 * - They generally be clicked on to change their characteristics (in the Sidebar)
 * - The click doesn't trigger default behavior (the view is inert)
 * - They can be draggable (FormLabel referring to a field)
 * - studioIsVisible: all components whether invisible or not, are compiled and rendered
 *   this props allows to toggle the class o_invisible_modifier
 * - They can have studio hooks, that are placeholders for dropping content (new elements, field, or displace elements)
 */

const components = formView.Renderer.components;

export class Widget extends components.Widget {
    get widgetProps() {
        const widgetProps = super.widgetProps;
        delete widgetProps.studioXpath;
        delete widgetProps.hasEmptyPlaceholder;
        delete widgetProps.hasLabel;
        delete widgetProps.studioIsVisible;
        return widgetProps;
    }
}

/*
 * Field:
 * - Displays an Overlay for X2Many fields
 * - handles invisible
 */
export class Field extends components.Field {
    setup() {
        super.setup();
        this.state = useState({
            displayOverlay: false,
        });
        useStudioRef("rootRef", this.onClick);
    }
    get fieldComponentProps() {
        const fieldComponentProps = super.fieldComponentProps;
        delete fieldComponentProps.studioXpath;
        delete fieldComponentProps.hasEmptyPlaceholder;
        delete fieldComponentProps.hasLabel;
        delete fieldComponentProps.studioIsVisible;
        return fieldComponentProps;
    }
    get classNames() {
        const classNames = super.classNames;
        classNames["o_web_studio_show_invisible"] = !studioIsVisible(this.props);
        classNames["o-web-studio-editor--element-clickable"] = true;
        if (!this.props.hasLabel && classNames["o_field_empty"]) {
            delete classNames["o_field_empty"];
            classNames["o_web_studio_widget_empty"] = true;
        }
        return classNames;
    }

    getEmptyPlaceholder() {
        const { hasEmptyPlaceholder, hasLabel, fieldInfo, name, record } = this.props;
        if (hasLabel || !hasEmptyPlaceholder) {
            return false;
        }
        const { empty } = fieldVisualFeedback(this.FieldComponent, record, name, fieldInfo);
        return empty ? record.activeFields[name].string : false;
    }

    isX2ManyEditable(props) {
        const { name, record } = props;
        const field = record.fields[name];
        if (!["one2many", "many2many"].includes(field.type)) {
            return false;
        }
        const activeField = record.activeFields[name];
        if (["many2many_tags", "hr_org_chart"].includes(activeField.widget)) {
            return false;
        }
        return true;
    }

    onEditViewType(viewType) {
        const { name, record, studioXpath } = this.props;
        this.env.config.onEditX2ManyView({ viewType, fieldName: name, record, xpath: studioXpath });
    }

    onClick(ev) {
        if (ev.target.classList.contains("o_web_studio_editX2Many")) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault();
        this.env.config.onNodeClicked({
            xpath: this.props.studioXpath,
            target: ev.target,
        });
        this.state.displayOverlay = !this.state.displayOverlay;
    }
}
Field.components = { ...Field.components, FieldContentOverlay };
Field.template = "web_studio.Field";

/*
 * FormLabel:
 * - Can be draggable if in InnerGroup
 */
export class FormLabel extends components.FormLabel {
    setup() {
        super.setup();
        useStudioRef("rootRef", this.onClick);
    }
    get className() {
        let className = super.className;
        if (!studioIsVisible(this.props)) {
            className += " o_web_studio_show_invisible";
        }
        className += " o-web-studio-editor--element-clickable";
        return className;
    }
    onClick(ev) {
        ev.preventDefault();
        this.env.config.onNodeClicked({
            xpath: this.props.studioXpath,
            target: ev.target,
        });
    }
}
FormLabel.template = "web_studio.FormLabel";

/*
 * ViewButton:
 * - Deals with invisible
 * - Click is overriden not to trigger the bound action
 */
export class ViewButton extends components.ViewButton {
    setup() {
        super.setup();
        useStudioRef("rootRef");
    }
    getClassName() {
        let className = super.getClassName();
        if (!studioIsVisible(this.props)) {
            className += " o_web_studio_show_invisible";
        }
        className += " o-web-studio-editor--element-clickable";
        return className;
    }

    onClick(ev) {
        if (this.props.tag === "a") {
            ev.preventDefault();
        }
        this.env.config.onNodeClicked({
            xpath: this.props.studioXpath,
            target: ev.currentTarget,
        });
    }
}
ViewButton.template = "web_studio.ViewButton";
ViewButton.props = [...components.ViewButton.props, "studioIsVisible?", "studioXpath"];

/*
 * Notebook:
 * - Display every page, the elements in the page handle whether they are invisible themselves
 * - Push a droppable hook on every empty page
 * - Can add a new page
 */
export class Notebook extends components.Notebook {
    computePages(props) {
        const pages = super.computePages(props);
        pages.forEach((p) => {
            p[1].studioIsVisible = p[1].isVisible;
            p[1].isVisible = p[1].isVisible || this.env.config.studioShowInvisible;
        });
        return pages;
    }
    onNewPageClicked() {
        this.env.config.structureChange({
            type: "add",
            structure: "page",
            position: "inside",
            xpath: this.props.studioXpath,
        });
    }
}
Notebook.template = "web_studio.Notebook.Hook";
Notebook.components = { ...components.Notebook.components, StudioHook };
Notebook.props = { ...components.Notebook.props, studioXpath: String };

export class StatusBarFieldHook extends Component {
    onClick() {
        this.env.config.onViewChange({
            add_statusbar: this.props.add_statusbar,
            type: "add",
            structure: "field",
            field_description: {
                field_description: "Pipeline status bar",
                type: "selection",
                selection: [
                    ["status1", this.env._t("First Status")],
                    ["status2", this.env._t("Second Status")],
                    ["status3", this.env._t("Third Status")],
                ],
                default_value: true,
            },
            target: {
                tag: "header",
            },
            new_attrs: {
                widget: "statusbar",
                options: "{'clickable': '1'}",
            },
            position: "inside",
        });
    }
}
StatusBarFieldHook.template = "web_studio.StatusBarFieldHook";

class FieldSelectorDialog extends Component {
    setup() {
        this.selectRef = owl.useRef("select");
    }
    onConfirm() {
        const field = this.selectRef.el.value;
        this.props.onConfirm(field);
        this.props.close();
    }
    onCancel() {
        this.props.close();
    }
}
FieldSelectorDialog.template = "web_studio.FieldSelectorDialog";
FieldSelectorDialog.components = { Dialog };

export class AvatarHook extends Component {
    setup() {
        this.dialogService = useService("dialog");
    }
    onClick() {
        const fields = [];
        for (const field of Object.values(this.props.fields)) {
            if (field.type === "binary") {
                fields.push(field);
            }
        }
        this.dialogService.add(FieldSelectorDialog, {
            fields,
            showNew: true,
            onConfirm: (field) => {
                this.env.config.onViewChange({
                    structure: "avatar_image",
                    field,
                });
            },
        });
    }
}
AvatarHook.template = "web_studio.AvatarHook";
AvatarHook.props = { fields: Object, class: { type: String, optional: true } };

export class ButtonHook extends Component {
    onClick() {
        this.env.config.onViewChange({
            structure: "button",
            type: "add",
            add_buttonbox: this.props.add_buttonbox,
        });
    }
}
ButtonHook.template = "web_studio.ButtonHook";

export class ButtonBox extends components.ButtonBox {
    getButtons() {
        const maxVisibleButtons = this.getMaxButtons();
        const visible = [];
        const additional = [];
        for (const [slotName, slot] of Object.entries(this.props.slots)) {
            if (this.env.config.studioShowInvisible || !("isVisible" in slot) || slot.isVisible) {
                if (visible.length >= maxVisibleButtons) {
                    additional.push(slotName);
                } else {
                    visible.push(slotName);
                }
            }
        }
        return { visible, additional };
    }
}
