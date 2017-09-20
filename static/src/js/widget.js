module.OrderWidget = module.OrderWidget.extend({      
//to use add classes and css 
        update_summary: function(){
            var order = this.pos.get('selectedOrder');
            var total = order ? order.getTotalTaxIncluded() : 0;
            var discount = order ? order.getDiscountTotal() : 0;
            var taxes = order ? total - order.getTotalTaxExcluded() : 0;
            var subtotal = order ? order.getSubtotal() : 0;
            var points_won      = order.get_won_points();
            var points_spent    = order.get_spent_points();
            var points_total    = order.get_new_total_points();
            this.el.querySelector('.summary .total > .value').textContent = this.format_currency(total);
            this.el.querySelector('.summary .discount > .value').textContent = this.format_currency(discount);
            this.el.querySelector('.summary .taxes > .value').textContent = this.format_currency(taxes);
            this.el.querySelector('.summary .subtotal > .value').textContent = this.format_currency(subtotal);

           //            order.save_to_db();
            var $loypoints = $(this.el).find('.summary .loyalty-points');
            var $line = $(this.el).find('.summary .line');
            if(this.pos.loyalty && order.get_client()){
                var points_won      = order.get_won_points();
                var points_spent    = order.get_spent_points();
                var points_total    = order.get_new_total_points();
                $loypoints.replaceWith($(QWeb.render('IsanaLoyaltyPoints',{ 
                    widget: this, 
                    rounding: this.pos.loyalty.rounding,
                    points_won: points_won,
                    points_spent: points_spent,
                    points_total: points_total,
                    order:order,
                })));
                $loypoints = $(this.el).find('.summary .loyalty-points');
                $loypoints.removeClass('oe_hidden');
                $line.addClass('loyalty');

                if(points_total < 0){
                    $loypoints.addClass('negative');
                }else{
                    $loypoints.removeClass('negative');
                }
            }else{
                $loypoints.empty();
                $loypoints.addClass('oe_hidden');
                $line.removeClass('loyalty');
            }
            
        },
    });
var SelectionPopupWidget = PopupWidget.extend({
    template: 'SelectionPopupWidget',
    show: function(options){
        options = options || {};
        var self = this;
        this._super(options);

        this.list    = options.list    || [];
        this.renderElement();
    },
    click_item : function(event) {
        this.gui.close_popup();
        if (this.options.confirm) {
            var item = this.list[parseInt($(event.target).data('item-index'))];
            item = item ? item.item : item;
            this.options.confirm.call(self,item);
        }
    }
});