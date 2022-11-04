/** @odoo-module **/

import { PdfViewerField } from '@web/views/fields/pdf_viewer/pdf_viewer_field';
import { ImageField } from '@web/views/fields/image/image_field';
import { SlidesViewer } from "@mrp/views/fields/google_slides_viewer";

const { Component, useEffect, useRef } = owl;

class DocumentViewer extends Component {

    setup() {
        this.magicNumbers = {
            'JVBER': 'pdf',
            '/': 'jpg',
            'R': 'gif',
            'i': 'png',
            'P': 'svg+xml',
        };
        this.pdfIFrame = useRef('pdf_viewer');
        useEffect(() => {
            this.updatePdf();
        });
    }

    updatePdf() {
        if (this.pdfIFrame.el) {
            const iframe = this.pdfIFrame.el.firstElementChild;
            iframe.removeAttribute('style');
            // Once the PDF viewer is loaded, hides everything except the page.
                iframe.addEventListener('load', () => {
                    iframe.contentDocument.querySelector('.toolbar').style.display = 'none';
                    iframe.contentDocument.querySelector('body').style.background = 'none';
                    iframe.contentDocument.querySelector('#viewerContainer').style.boxShadow = 'none';
                    iframe.contentDocument.querySelector('#mainContainer').style.margin = '-2.5em';
                });
        }
    }
    get type() {
        if (!this.props || !this.props.value) {
            return false;
        }
        if (this.props.resField === "worksheet_url") {
            return "google_slide";
        }
        for (const [magicNumber, type] of Object.entries(this.magicNumbers)) {
            if (this.props.value.startsWith(magicNumber)) {
                return type;
            }
        }
        return false;
    }

    get viewerProps() {
        let viewerProps = {
            record: {
                resModel: this.props.resModel,
                resId: this.props.resId,
                data: {},
            },
            name: this.props.resField,
            value: this.props.value,
            readonly: true,
        };
        viewerProps['record']['data'][this.props.resField] = this.props.resField;
        viewerProps['record']['data'][`$(this.props.resField)_page`] = this.props.page || 1;
        if (this.type === 'pdf') {
            viewerProps['fileNameField'] = this.props.resField;
        }
        return viewerProps;
    }
}

DocumentViewer.template = 'mrp_workorder.DocumentViewer';
DocumentViewer.props = ["resField", "resModel", "resId", "value", "page"];
DocumentViewer.components = {
    PdfViewerField,
    ImageField,
    SlidesViewer,
};

export default DocumentViewer;
