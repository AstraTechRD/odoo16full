/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ImageField } from '@web/views/fields/image/image_field';

const { Component } = owl;

class ImagePreviewDialog extends Component {}
ImagePreviewDialog.components = { Dialog };
ImagePreviewDialog.template = "quality.ImagePreviewDialog";

export class TabletImageField extends ImageField {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }

    openModal() {
        this.dialog.add(ImagePreviewDialog, {
            src: this.getUrl(this.props.name),
        });
    }
}

TabletImageField.template = "quality.TabletImageField";

registry.category("fields").add("tablet_image", TabletImageField);
