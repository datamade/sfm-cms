var Footnotes = Footnotes || {};

var Footnotes = {

    initPopovers: function() {

        $('[data-toggle="popover"]').popover({
            placement: 'auto',
            html: true,
            content: function(popover) {}
        });

        $('[data-toggle="tooltip"]').tooltip();

        $(document).on('shown.bs.popover', function(e) {

            // Init dismiss buttons
            var params = {'object_info': $(e.target).data('object_info')};
            var citation_url = $(e.target).data('citation_url');
            var popover = $(e.target).data('bs.popover');
            $.when($.get(citation_url, params)).then(function(response){
                $(e.target).attr('data-content', response);
                popover.setContent();
                $('[data-dismiss="popover"]').click(function() {
                    (($(this).parents('.popover').popover('hide').data('bs.popover') ||
                    {}).inState ||
                        {}).click = false;  // fix for BS 3.3.6
                    $(this).parents('.citation').css('visibility', 'hidden');
                });
            })
        });

    }
};
