/** @odoo-module alias=documents.component.PdfPage **/

const { Component, onMounted, onPatched, useState, useRef } = owl;

/**
 * Represents the page of a PDF.
 */
export class PdfPage extends Component {

    /**
     * @override
     */
    setup() {
        this.state = useState({
            isHover: false,
            isRendered: false,
        });
        // Used to append a canvas when it has been rendered.
        this.canvasWrapperRef = useRef("canvasWrapper");

        onMounted(() => this.renderPage(this.props.canvas));
    
        onPatched(() => this.renderPage(this.props.canvas));
    }   

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * The canvas is rendered asynchronously so it is only manually appended
     * later when available. It should have been done through the natural owl
     * re-rendering but it is currently causing unnecessary re-renderings of
     * sibling components which would noticeably slows the behaviour down.
     *
     * @public
     * @param {DomElement} canvas
     */
    renderPage(canvas) {
        if (!canvas || this.isRendered) {
            return;
        }
        this.canvasWrapperRef.el.appendChild(canvas);
        this.isRendered = true;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickWrapper(ev) {
        ev.stopPropagation();
        this.props.onPageClicked(this.props.pageId);
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSelect(ev) {
        ev.stopPropagation();
        if (this.props.onSelectClicked) {
            this.props.onSelectClicked(
                this.props.pageId,
                true,
                ev.shiftKey,
                true,
            );
        }
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDragEnter(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.state.isHover = true;
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDragLeave(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.state.isHover = false;
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDragOver(ev) {
        ev.preventDefault();
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDragStart(ev) {
        ev.stopPropagation();
        if (this.props.onPageDragged) {
            this.props.onPageDragged(ev);
        }
        ev.dataTransfer.setData('o_documents_pdf_data', this.props.pageId);
    }
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onDrop(ev) {
        this.state.isHover = false;
        if (!ev.dataTransfer.types.includes('o_documents_pdf_data')) {
            return;
        }
        const pageId = ev.dataTransfer.getData('o_documents_pdf_data');
        if (pageId === this.props.pageId) {
            return;
        }
        if (this.props.onPageDropped) {
            this.props.onPageDropped(this.props.pageId, pageId);
        }
    }
}

PdfPage.defaultProps = {
    isPreview: false,
    isSelected: false,
};

PdfPage.props = {
    canvas: {
        type: Object,
        optional: true,
    },
    isPreview: {
        type: Boolean,
        optional: true,
    },
    isSelected: {
        type: Boolean,
        optional: true,
    },
    onPageClicked: {
        type: Function,
        optional: true,
    },
    onPageDragged: {
        type: Function,
        optional: true,
    },
    onPageDropped: {
        type: Function,
        optional: true,
    },
    onSelectClicked: {
        type: Function,
        optional: true,
    },
    pageId: String,    
};

PdfPage.template = 'documents.component.PdfPage';
