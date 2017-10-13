  var _super = module.Paymentline;
    module.Paymentline = module.Paymentline.extend({
        initialize: function(attributes, options) {
            this.amount = 0;
            this.cashregister = options.cashregister || null;
            if (this.cashregister){
                this.name = this.cashregister.journal_id[1] || [];
            }
            
            this.selected = false;
            this.pos = options.pos || [];
        },
        get_amount_str: function(){
            var decimals_isana = this.pos.dp['Product Price POS']
            console.log(decimals_isana,this.pos.currency.decimals)
            return round_di(parseFloat(this.amount) || 0, decimals_isana); 
            // return this.amount.toFixed(this.pos.currency.decimals);
        },
        init_from_JSON: function(json){
            this.amount = json.amount;
            this.cashregister = this.pos.cashregisters_by_id[json.statement_id];
            this.name = this.cashregister.journal_id[1];
        },
    });