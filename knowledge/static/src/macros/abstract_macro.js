/** @odoo-module */

import { _t } from "web.core";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { isVisible } from "@web/core/utils/ui";
import { MacroEngine } from "@web/core/macro";

class KnowledgeMacroPageChangeError extends Error {}

export class AbstractMacro {
    /**
     * @param {Object} options
     * @param {HTMLElement} options.targetXmlDoc
     * @param {Array[Object]} options.breadcrumbs
     * @param {Any} options.data
     * @param {Object} options.services require: uiService, dialogService
     * @param {integer} [options.interval]
     */
    constructor ({
        targetXmlDoc,
        breadcrumbs,
        data,
        services,
        interval = 16,
    }) {
        this.targetXmlDoc = targetXmlDoc;
        this.breadcrumbsIndex = breadcrumbs.length - 1;
        this.breadcrumbsName = breadcrumbs[this.breadcrumbsIndex].name;
        this.breadcrumbsSelector = ['.breadcrumb > .breadcrumb-item.active', (el) => el.textContent.includes(this.breadcrumbsName)];
        this.interval = interval;
        this.data = data;
        this.engine = new MacroEngine();
        this.services = services;
        this.blockUI = { action: function () {
            if (!this.services.ui.isBlocked) {
                this.services.ui.block();
            }
        }.bind(this) };
        this.unblockUI = { action: function () {
            if (this.services.ui.isBlocked) {
                this.services.ui.unblock();
            }
        }.bind(this) };
        this.onError = this.onError.bind(this);
    }
    start() {
        // Build the desired macro action
        const macroAction = this.macroAction();
        if (!macroAction || !macroAction.steps || !macroAction.steps.length) {
            return;
        }
        /**
         * Preliminary breadcrumbs macro. It will use the @see breadcrumbsIndex
         * to switch back to the view related to the stored record
         * (@see KnowledgeCommandsService ). Once and if the view of the target
         * record is correctly loaded, run the specific macroAction.
         */
        const startMacro = {
            name: "restore_record",
            interval: this.interval,
            onError: this.onError,
            steps: [
                this.blockUI, {
                trigger: function () {
                    const breadcrumbs = document.querySelectorAll(`.breadcrumb-item:not(.active)`);
                    if (breadcrumbs.length > this.breadcrumbsIndex) {
                        const breadcrumb = breadcrumbs[this.breadcrumbsIndex];
                        if (breadcrumb.textContent.includes(this.breadcrumbsName)) {
                            return this.getFirstVisibleElement(breadcrumb.querySelector('a'));
                        }
                    }
                    return null;
                }.bind(this),
                action: 'click',
            }, {
                trigger: this.getFirstVisibleElement.bind(this, ...this.breadcrumbsSelector),
                action: this.engine.activate.bind(this.engine, macroAction),
            }],
        };
        this.engine.activate(startMacro);
    }
    /**
     * @param {Error} error
     * @param {Object} step
     * @param {integer} index
     */
    onError(error, step, index) {
        this.unblockUI.action();
        if (error instanceof KnowledgeMacroPageChangeError) {
            this.services.dialog.add(AlertDialog,{
                body: _t('The operation was interrupted because the page or the record changed. Please try again later.'),
                title: _t('Error'),
                cancel: () => {},
                cancelLabel: _t('Close'),
            });
        } else {
            console.error(error);
        }
    }
    /**
     * @param {String|HTMLElement} selector
     * @param {Function} filter
     * @param {boolean} reverse
     * @returns {HTMLElement}
     */
    getFirstVisibleElement(selector, filter=false, reverse=false) {
        const elementsArray = typeof(selector) === 'string' ? Array.from(document.querySelectorAll(selector)) : [selector];
        const sel = filter ? elementsArray.filter(filter) : elementsArray;
        for (let i = 0; i < sel.length; i++) {
            i = reverse ? sel.length - 1 - i : i;
            if (isVisible(sel[i])) {
                return sel[i];
            }
        }
        return null;
    }
    validatePage() {
        if (!this.getFirstVisibleElement(...this.breadcrumbsSelector)) {
            throw new KnowledgeMacroPageChangeError();
        }
    }
    /**
     * @returns {Object}
     */
    macroAction() {
        return {
            name: this.constructor.name,
            interval: this.interval,
            onError: this.onError,
            steps: [],
        };
    }
    /**
     * Handle the case where an item is hidden in a tab of the form view notebook
     */
    searchInXmlDocNotebookTab(targetSelector) {
        const page = this.targetXmlDoc.querySelector(targetSelector).closest('page');
        const pageString = page.getAttribute('string');
        const pageEl = this.getFirstVisibleElement('.o_notebook .nav-link:not(.active)', (el) => el.textContent.includes(pageString));
        if (pageEl) {
            pageEl.click();
        }
    }
}
