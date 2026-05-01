(function($) {
    $(document).ready(function() {
        $('.all__flex-item').on('click', function () {
            var filter = $(this).data('filter');

            if($(this).hasClass('filter-active') && filter < 3) {
                return false;
            }
            
			$('.all__flex-item').removeClass('all__flex-item--active');
			$(this).addClass('all__flex-item--active');


            $('.all__flex-item').removeClass('filter-active');

            if(filter == 3) {
                $('.single-main').get(0).scrollIntoView({
                    behavior: 'smooth', 
                    block: 'start'
                });
                $(this).addClass('filter-active');
                return false;
            }

            if(filter == 4 ){
                $('.comments-section').get(0).scrollIntoView({
                    behavior: 'smooth', 
                    block: 'start'
                })
                $(this).addClass('filter-active');
                return false;
            }

            $(this).addClass('filter-active');
            var id = $('.best-ajax-section #postID').val();

            $.ajax({
                type : "post",
                dataType : "json",
                url : ld_array.admin_ajax,
                data : {
                    action: "ajax_load_post", 
                    filter : filter,
                    id: id,
                    nonce: ld_array.load_post_nonce
                },
                context: this,
                beforeSend: function(){
                    $(".best-ajax-section .exercise__grid--1").empty();
                    $('.paginate_links').remove();
                    $('.exercise__grid-loading').addClass('load');
                },
                success: function(response) {
                    if(response.success) {
                        $(".best-ajax-section .exercise__grid--1").append($(response.data.content));
                        $(".best-ajax-section .pagination-best").append($(response.data.pagi));
                    }
                    $('.exercise__grid-loading').removeClass('load');
                }
            });
		});

        $(document).on('click','.paginate_links a',function(e){
            e.preventDefault();
            var id = $('.best-ajax-section #postID').val();
            var hrefThis = $(this).attr('href');
            var pagedMatch = hrefThis.match(/\/page\/(\d+)/);
            var paged = pagedMatch ? parseInt(pagedMatch[1], 10) : 1;
            var filter = $('.filter-active').data('filter');
            if(!paged) paged = 1;
            $.ajax({
                type : "post",
                dataType : "json",
                url : ld_array.admin_ajax,
                data : {
                    action: "ajax_load_post", 
                    ajax_paged : paged,
                    filter: filter,
                    id: id,
                    nonce: ld_array.load_post_nonce
                },
                context: this,
                beforeSend: function(){
                    $(".best-ajax-section .exercise__grid--2").empty();
                    $('.paginate_links').remove();
                    $('.exercise__grid-loading').addClass('load');
                },
                success: function(response) {
 
                    if(response.success) {
                        $(".best-ajax-section .exercise__grid--2").append($(response.data.content));
                        $(".best-ajax-section .pagination-best").append($(response.data.pagi));
                    }
                    $('.exercise__grid-loading').removeClass('load');
                }
            });
        });

    });
})(jQuery);