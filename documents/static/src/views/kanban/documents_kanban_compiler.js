/** @odoo-module **/

import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { isTextNode } from "@web/views/view_compiler";
import { createElement } from "@web/core/utils/xml";

export class DocumentsKanbanCompiler extends KanbanCompiler {
    setup() {
        super.setup();
        this.compilers.push({ selector: "[t-name='kanban-box']", fn: this.compileCard });
    }

    /**
     * @override
     */
    compileCard() {
        const result = super.compileGenericNode(...arguments);
        const cards = result.childNodes;
        for (const card of cards) {
            if (isTextNode(card)) {
                continue;
            }
            // Prevent default kanban renderer hotkey event from triggering
            const dummyElement = createElement("a");
            dummyElement.classList.add("o_hidden", "o_documents_dummy_action");
            card.prepend(dummyElement);
            card.setAttribute("t-on-dragstart.stop", `(ev) => props.record.onDragStart(ev)`);
            const fileInput = card.querySelector("input.o_kanban_replace_document");
            if (fileInput) {
                fileInput.setAttribute("t-on-change.stop", `(ev) => props.record.onReplaceDocument(ev)`);
            }
        }
        return result;
    }
}
