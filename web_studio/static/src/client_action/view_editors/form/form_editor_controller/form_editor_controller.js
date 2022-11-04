/** @odoo-module */

import { formView } from "@web/views/form/form_view";

function rebindLegacyDatapoint(datapoint, basicModel) {
    const newDp = {};

    const descrs = Object.getOwnPropertyDescriptors(datapoint);
    Object.defineProperties(newDp, descrs);

    newDp.id = "__can'ttouchthis__";
    newDp.evalModifiers = basicModel._evalModifiers.bind(basicModel, newDp);
    newDp.getContext = basicModel._getContext.bind(basicModel, newDp);
    newDp.getDomain = basicModel._getDomain.bind(basicModel, newDp);
    newDp.getFieldNames = basicModel._getFieldNames.bind(basicModel, newDp);
    newDp.isDirty = basicModel.isDirty.bind(basicModel, newDp.id);
    newDp.isNew = basicModel.isNew.bind(basicModel, newDp.id);
    return newDp;
}

function applyParentRecordOnModel(model, parentRecord) {
    const legacyHandle = parentRecord.__bm_handle__;
    const legacyDp = parentRecord.model.__bm__.localData[legacyHandle];

    const load = model.load;
    model.load = async (...args) => {
        const res = await load.call(model, ...args);
        const localData = model.__bm__.localData;

        const parentDp = rebindLegacyDatapoint(legacyDp, model.__bm__);
        localData[parentDp.id] = parentDp;

        const rootDp = localData[model.root.__bm_handle__];
        rootDp.parentID = parentDp.id;
        return res;
    };
}

export class FormEditorController extends formView.Controller {
    setup() {
        super.setup();
        this.mailTemplate = null;
        this.hasAttachmentViewerInArch = false;

        if (this.props.parentRecord) {
            applyParentRecordOnModel(this.model, this.props.parentRecord);
        }
    }
}
FormEditorController.props = {
    ...formView.Controller.props,
    parentRecord: { type: [Object, { value: null }], optional: true },
};
