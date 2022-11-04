/** @odoo-module */

/**
 * @param {String} string - Name of the drag event
 * @param {DataTransfer} dataTransfer - Object used to store data
 * @param {HTMLElement} target - Target element
 */
export function dragAndDrop(type, dataTransfer, target) {
    const fakeDragAndDrop = new Event(type, {
        bubbles: true,
        cancelable: true,
        composed: true,
    });
    fakeDragAndDrop.dataTransfer = dataTransfer;
    target.dispatchEvent(fakeDragAndDrop);
}

/**
 * @param {DataTransfer} dataTransfer - Object used to store data
 * @param {HTMLElement} target - Target element
 */
export function pasteElements(dataTransfer, target) {
    const fakePaste = new Event('paste', {
        bubbles: true,
        cancelable: true,
        composed: true,
    });
    fakePaste.clipboardData = dataTransfer;

    const sel = document.getSelection();
    sel.removeAllRanges();
    const range = document.createRange();
    const firstChild = target.firstChild;
    if (!firstChild) {
        range.setStart(target, 0);
        range.setEnd(target, 0);
    } else {
        range.setStart(firstChild, 0);
        range.setEnd(firstChild, 0);
    }
    sel.addRange(range);
    target.dispatchEvent(fakePaste);
}
