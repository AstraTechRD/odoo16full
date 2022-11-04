/** @odoo-module */

import { appendAttr, isComponentNode } from "@web/views/view_compiler";
import { computeXpath } from "@web_studio/client_action/view_editors/xml_utils";
import { createElement } from "@web/core/utils/xml";
import { formView } from "@web/views/form/form_view";
import { objectToString } from "@web/views/form/form_compiler";

const interestingSelector = [
    ":not(field) sheet", // A hook should be present to add elements in the sheet
    ":not(field) field", // should be clickable and draggable
    ":not(field) notebook", // should be able to add pages
    ":not(field) page", // should be clickable
    ":not(field) button", // should be clickable
    ":not(field) label", // should be clickable
    ":not(field) group", // any group: outer or inner
    ":not(field) group group > *", // content of inner groups serves as main dropzone
    ":not(field) div.oe_chatter",
    ":not(field) .oe_avatar",
].join(", ");

export class FormEditorCompiler extends formView.Compiler {
    compile(key, params = {}) {
        params.enableInvisible = true;
        const xml = this.templates[key];

        // One pass to compute and add the xpath for the arch's node location
        // onto that node.
        for (const el of xml.querySelectorAll(interestingSelector)) {
            const xpath = computeXpath(el);
            el.setAttribute("studioXpath", xpath);
        }

        // done after construction of xpaths
        this.addChatter = true;
        this.chatterData = {
            remove_message_ids: false,
            remove_follower_ids: false,
            remove_activity_ids: false,
        };
        this.avatars = [];

        let buttonBox = xml.querySelector("div.oe_button_box");
        const buttonHook = createElement("ButtonHook", { add_buttonbox: !buttonBox });
        if (buttonBox) {
            buttonBox.prepend(buttonHook);
        }

        const compiled = super.compile(key, params);

        const sheetBg = compiled.querySelector(".o_form_sheet_bg");
        if (sheetBg) {
            const studioHook = createElement("StudioHook", {
                xpath: `"${sheetBg.getAttribute("studioXpath")}"`,
                position: "'inside'",
                type: "'insideSheet'",
            });
            sheetBg.querySelector(".o_form_sheet").prepend(studioHook);
        }

        if (this.addChatter) {
            const chatterContainerHook = createElement("ChatterContainerHook", {
                threadModel: `props.record.resModel`,
                chatterData: objectToString(this.chatterData),
            });
            const el = compiled.querySelector(".o_form_sheet") || compiled;
            el.after(chatterContainerHook);
        } else {
            const parent = compiled.querySelector(".o_FormRenderer_chatterContainer");
            parent.removeAttribute("t-attf-class"); // avoid class o-aside
            parent.removeAttribute("t-if");
        }

        if (!buttonBox) {
            buttonBox = createElement("div", { class: "oe_button_box" });
            buttonBox.prepend(buttonHook);
            const compiledButtonBox = this.compileButtonBox(buttonBox, {});
            const el = compiled.querySelector(".o_form_sheet") || compiled;
            el.prepend(compiledButtonBox);
        }

        const fieldStatus = compiled.querySelector(`Field[type="'statusbar'"]`); // change selector at some point
        if (!fieldStatus) {
            const add_statusbar = !compiled.querySelector(".o_form_statusbar");
            const statusBarFieldHook = createElement("StatusBarFieldHook", { add_statusbar });
            const el = compiled.querySelector(".o_form_sheet_bg") || compiled;
            el.prepend(statusBarFieldHook);
        }

        // Note: the ribon does not allow to remove an existing avatar!
        const title = compiled.querySelector(".oe_title");
        if (title) {
            if (
                !title.querySelector(":scope > h1 > [isAvatar]") && // check it works with <field class="oe_avatar" ... />
                !title.parentElement.querySelector(":scope > [isAvatar]")
            ) {
                const avatarHook = createElement("AvatarHook", {
                    fields: `props.record.fields`,
                });
                const h1 = title.querySelector(":scope > h1");
                if (h1 && h1.classList.contains("d-flex") && h1.classList.contains("flex-row")) {
                    avatarHook.setAttribute("class", `'oe_avatar ms-3 p-3 o_web_studio_avatar h4'`);
                    h1.append(avatarHook);
                } else {
                    avatarHook.setAttribute("class", `'oe_avatar ms-3 me-3 o_web_studio_avatar'`);
                    title.before(avatarHook);
                }
            }
        }
        for (const el of this.avatars) {
            el.removeAttribute("isAvatar");
        }

        compiled.querySelectorAll(":not(.o_form_statusbar) Field").forEach((el) => {
            el.setAttribute("hasEmptyPlaceholder", "true");
        });

        compiled
            .querySelectorAll(`InnerGroup > t[t-set-slot][subType="'item_component'"] Field`)
            .forEach((el) => {
                el.setAttribute("hasLabel", "true");
            });

        return compiled;
    }

    applyInvisible(invisible, compiled, params) {
        // Just return the node if it is always Visible
        if (!invisible) {
            return compiled;
        }

        let isVisileExpr;
        // If invisible is dynamic (via Domain), pass a props or apply the studio class.
        if (typeof invisible !== "boolean") {
            const recordExpr = params.recordExpr || "props.record";
            isVisileExpr = `!evalDomainFromRecord(${recordExpr},${JSON.stringify(invisible)})`;
            if (isComponentNode(compiled)) {
                compiled.setAttribute("studioIsVisible", isVisileExpr);
            } else {
                appendAttr(compiled, "class", `o_web_studio_show_invisible:!${isVisileExpr}`);
            }
        } else {
            if (isComponentNode(compiled)) {
                compiled.setAttribute("studioIsVisible", "false");
            } else {
                appendAttr(compiled, "class", `o_web_studio_show_invisible:true`);
            }
        }

        // Finally, put a t-if on the node that accounts for the parameter in the config.
        const studioShowExpr = `env.config.studioShowInvisible`;
        isVisileExpr = isVisileExpr ? `(${isVisileExpr} or ${studioShowExpr})` : studioShowExpr;
        if (compiled.hasAttribute("t-if")) {
            const formerTif = compiled.getAttribute("t-if");
            isVisileExpr = `( ${formerTif} ) and ${isVisileExpr}`;
        }
        compiled.setAttribute("t-if", isVisileExpr);
        return compiled;
    }

    createLabelFromField(fieldId, fieldName, fieldString, label, params) {
        const studioXpath = label.getAttribute("studioXpath");
        const formLabel = super.createLabelFromField(...arguments);
        formLabel.setAttribute("studioXpath", `"${studioXpath}"`);
        if (formLabel.hasAttribute("t-if")) {
            formLabel.setAttribute("studioIsVisible", formLabel.getAttribute("t-if"));
            formLabel.removeAttribute("t-if");
        }
        return formLabel;
    }

    compileNode(node, params = {}, evalInvisible = true) {
        const nodeType = node.nodeType;
        // Put a xpath on the currentSlot containing the future compiled element.
        // Do it early not to be bothered by recursive call to compileNode.
        const currentSlot = params.currentSlot;
        if (nodeType === 1 && currentSlot && !currentSlot.hasAttribute("studioXpath")) {
            const parentElement = node.parentElement;
            if (parentElement && parentElement.tagName === "page") {
                const xpath = computeXpath(node.parentElement);
                currentSlot.setAttribute("studioXpath", `"${xpath}"`);
                if (!node.parentElement.querySelector(":scope > group")) {
                    const hookProps = {
                        position: "'inside'",
                        type: "'page'",
                        xpath: `"${xpath}"`,
                    };
                    currentSlot.setAttribute("studioHookProps", objectToString(hookProps));
                }
            } else {
                const xpath = node.getAttribute("studioXpath");
                currentSlot.setAttribute("studioXpath", `"${xpath}"`);
            }
        }

        const compiled = super.compileNode(node, params, true); // always evalInvisible

        if (nodeType === 1) {
            // Put a xpath on anything of interest.
            if (node.hasAttribute("studioXpath")) {
                const xpath = node.getAttribute("studioXpath");
                if (isComponentNode(compiled)) {
                    compiled.setAttribute("studioXpath", `"${xpath}"`);
                } else if (!compiled.hasAttribute("studioXpath")) {
                    compiled.setAttribute("studioXpath", xpath);
                }
            }

            if (node.classList.contains("oe_chatter")) {
                this.addChatter = false;
                // compiled is not ChatterContainer!
                const chatterNode = compiled.querySelector("ChatterContainer");
                const xpath = node.getAttribute("studioXpath");
                chatterNode.setAttribute("studioXpath", `"${xpath}"`);
                compiled.classList.add("o-web-studio-editor--element-clickable");
            }
            if (node.classList.contains("oe_avatar")) {
                compiled.setAttribute("isAvatar", true);
                this.avatars.push(compiled);
            }
            const name = node.getAttribute("name"); // not sure that part works
            if (name === "message_ids") {
                this.chatterData.remove_message_ids = true;
            } else if (name === "message_follower_ids") {
                this.chatterData.remove_follower_ids = true;
            } else if (name === "activity_ids") {
                this.chatterData.remove_activity_ids = true;
            }
        }
        return compiled;
    }

    isAlwaysInvisible() {
        return false;
    }
}
