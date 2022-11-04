/** @odoo-module */

/**
 * Opens the power box of the editor
 * @param {HTMLElement} paragraph
 */
export function openCommandBar(paragraph) {
    const sel = document.getSelection();
    sel.removeAllRanges();
    const range = document.createRange();
    range.setStart(paragraph, 0);
    range.setEnd(paragraph, 0);
    sel.addRange(range);
    paragraph.dispatchEvent(new KeyboardEvent('keydown', {
        key: '/',
    }));
    const slash = document.createTextNode('/');
    paragraph.replaceChildren(slash);
    sel.removeAllRanges();
    range.setStart(paragraph, 1);
    range.setEnd(paragraph, 1);
    sel.addRange(range);
    paragraph.dispatchEvent(new InputEvent('input', {
        inputType: 'insertText',
        data: '/',
        bubbles: true,
    }));
    paragraph.dispatchEvent(new KeyboardEvent('keyup', {
        key: '/',
    }));
}
