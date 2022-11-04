/** @odoo-module **/

import "@mail/components/attachment_viewer/attachment_viewer";
import { getMessagingComponent } from "@mail/utils/messaging_component";

const { Component, useEffect, useRef, useState } = owl;

export class DocumentsAttachmentViewer extends Component {
    setup() {
        this.root = useRef("root");
        this.state = useState({
            topOffset: 0,
        });
        this.previewState = useState(this.env.documentsView.previewStore);

        const onKeydown = this.onIframeKeydown.bind(this);
        useEffect(
            (iframe) => {
                if (!iframe) {
                    return;
                }
                // We need to wait until the iframe is loaded to be able to bind our keydown handler.
                const onLoad = () => {
                    // In case of youtube links contentDocument might be null.
                    if (!iframe.contentDocument) {
                        return;
                    }
                    iframe.contentDocument.addEventListener("keydown", onKeydown);
                };
                iframe.addEventListener("load", onLoad);
                return () => {
                    iframe.removeEventListener("load", onLoad);
                };
            },
            () => [this.root.el && this.root.el.querySelector("iframe")]
        );
        useEffect(
            (el) => {
                if (!el) {
                    return;
                }
                this.state.topOffset = el.scrollTop;
                const scrollHandler = () => {
                    this.state.topOffset = el.scrollTop;
                };
                el.addEventListener("scroll", scrollHandler);
                return () => {
                    el.removeEventListener("scroll", scrollHandler);
                };
            },
            () => [this.parentRoot.el]
        );
    }

    get parentRoot() {
        return this.props.parentRoot;
    }

    onGlobalKeydown(ev) {
        // Some keydown events are not handled by the attachmentViewer as we want them too
        // making it possible to interact with the background.
        const cancelledKeys = ["ArrowUp", "ArrowDown"];
        if (cancelledKeys.includes(ev.key)) {
            ev.stopPropagation();
        }
    }

    onIframeKeydown(ev) {
        if (ev.key === "Escape") {
            this.previewState.documentList.delete();
        }
    }
}
DocumentsAttachmentViewer.components = {
    AttachmentViewer: getMessagingComponent("AttachmentViewer"),
};
DocumentsAttachmentViewer.template = "documents.DocumentsAttachmentViewer";
