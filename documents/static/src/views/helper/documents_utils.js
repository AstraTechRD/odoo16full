/** @odoo-module alias=documents.utils */

export default {
    /**
     * @param {Array} items the ordered pool of all items in the context of this multi-selection.
     * @param {any} target the item in the pool that is marked as target for this multi-selection.
     * @param {Object} [param2={}] options of the multi-selection.
     * @param {any} [param2.anchor] if set, the item in the pool that acts as anchor.
     *   Useful to auto-(un)select all in-between items to `target` when optional parameter
     *   `isRangeSelection` is set.
     * @param {boolean} [param2.isCheckbox=false] if the selection comes from a checkbox, in which case the
     *   range selection takes precedence over the keep selection.
     * @param {boolean} [param2.isKeepSelection=false] if set, multi-selection must keep already
     *   selected items in resulting selection. See optional param `selected` for list of already
     *   selected items.
     * @param {boolean} [param2.isRangeSelection=false] if set, the multi-selection should
     *   auto-(un)select all in-between items of optional `anchor` item and `target` item.
     * @param {Array} [param2.selected=[]] ordered list of already selected items. Useful to keep them
     *   in resulting selection when optional param `isKeepSelection` is set.
     * @returns {Object} { anchor, selection } where `anchor` is the new anchor and `selection` is the
     *   new selection.
     */
    computeMultiSelection(
        items,
        target,
        { anchor, isCheckbox = false, isKeepSelection = false, isRangeSelection = false, selected = [] } = {}
    ) {
        if (isCheckbox) {
            isKeepSelection = isRangeSelection ? false : isKeepSelection;
        }
        const wasSelected = selected.includes(target);
        const isBasicSelection = !isRangeSelection && !isKeepSelection;
        let newSelection;

        if (isBasicSelection) {
            if (selected.length > 1) {
                newSelection = [target];
            } else {
                newSelection = wasSelected ? [] : [target];
            }
        } else {
            let selectedRecordsIds;
            if (isRangeSelection) {
                const anchorIndex = items.indexOf(anchor);
                const selectedRecordIndex = items.indexOf(target);
                const lowerIndex = Math.min(anchorIndex, selectedRecordIndex);
                const upperIndex = Math.max(anchorIndex, selectedRecordIndex);
                selectedRecordsIds = items.slice(lowerIndex, upperIndex + 1);
            } else {
                selectedRecordsIds = [target];
            }

            if (isKeepSelection) {
                newSelection = wasSelected
                    ? selected.filter((id) => id !== target)
                    : selected.concat(selectedRecordsIds);
            } else {
                newSelection = selectedRecordsIds;
            }
        }

        if (!isRangeSelection) {
            if (newSelection.includes(target)) {
                anchor = target;
            } else {
                anchor = undefined;
            }
        }

        return { newSelection, anchor };
    },
};
