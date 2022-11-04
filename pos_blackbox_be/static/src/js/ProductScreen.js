odoo.define('pos_blackbox_be.ProductScreen', function(require) {

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const PosBlackBoxBeProductScreen = ProductScreen => class extends ProductScreen {
        disallowLineQuantityChange() {
            let result = super.disallowLineQuantityChange();
            return (this.env.pos.useBlackBoxBe() && this.numpadMode === 'quantity') || result;
        }
    };

    Registries.Component.extend(ProductScreen, PosBlackBoxBeProductScreen);

    return ProductScreen;
});
