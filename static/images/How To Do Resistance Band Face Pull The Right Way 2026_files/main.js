jQuery(function ($) {

    // Store Action
    $('.storeAction').on('click', function (e) {
        e.preventDefault();

        const ua = navigator.userAgent.toLowerCase();
        const $this = $(this);
        const appLink = $this.data('app');
        const ggLink = $this.data('gg');

        const isAppleDevice = ua.includes('iphone') || ua.includes('ipad') || ua.includes('ipod') || ua.includes('macintosh');

        if (isAppleDevice) {
            if (appLink) {
                window.open(appLink, '_blank');
            }
        } else {
            if (ggLink) {
                window.open(ggLink, '_blank');
            }
        }
    });

    // Woo header action
    const userIcon = $("#userIcon");
    const userMenu = $("#userMenu");
    const userMenuOverlay = $("#userMenuOverlay");
    const closeUserMenu = $("#closeUserMenu");

    if (userIcon.length && userMenu.length && userMenuOverlay.length && closeUserMenu.length) {
        userIcon.on("click", function () {
            userMenu.addClass("active");
            userMenuOverlay.show();
        });

        closeUserMenu.on("click", function () {
            userMenu[0].offsetWidth; // Trigger reflow
            setTimeout(() => {
                userMenuOverlay.hide();
                userMenu.removeClass("active");
            }, 100);
        });

        userMenuOverlay.on("click", function () {
            userMenu[0].offsetWidth; // Trigger reflow
            setTimeout(() => {
                userMenuOverlay.hide();
                userMenu.removeClass("active");
            }, 100);
        });
    }

    // Cart Icon click event
    $(document).on("click", "#cartIcon", function () {
        if (typeof jQuery !== "undefined") {
            $(".xoo-wsc-modal").addClass("xoo-wsc-cart-active");
            $("body").addClass("xoo-wsc-open");
        }
    });

    // Feature On Slide
    if ($(window).width() <= 820 && $('.featureon__list').length) {
        if (!$('.featureon__list').hasClass('slick-initialized')) {
            $('.featureon__list').slick({
                slidesToShow: 4,
                slidesToScroll: 1,
                dots: false,
                arrows: false,
                infinite: true,
                centerMode: false,
                autoplay: true,
                responsive: [
                    {
                        breakpoint: 480,
                        settings: {
                            slidesToShow: 3,
                            slidesToScroll: 1,
                            dots: false,
                            arrows: false,
                            infinite: true,
                            centerMode: false,
                            centerPadding: '0',
                        }
                    }
                ]
            });
        }
    } else {
        if ($('.featureon__list').hasClass('slick-initialized')) {
            $('.featureon__list').slick('unslick');
        }
    }

    // Woocommerce fucntion
    $('.quantity').each(function () {
        var $this = $(this);
        $this.prepend('<input type="button" value="-" class="minus button wp-element-button">');
        $this.append('<input type="button" value="+" class="plus button wp-element-button">');
    });

    $(document).on('click', '.minus', function () {
        var $input = $(this).siblings('input.qty');
        var value = parseInt($input.val());
        if (!isNaN(value) && value > 1) {
            $input.val(value - 1).change();
        }
    });

    $(document).on('click', '.plus', function () {
        var $input = $(this).siblings('input.qty');
        var value = parseInt($input.val());
        if (!isNaN(value)) {
            $input.val(value + 1).change();
        }
    });

    // Customer review function
    $(window).scroll(function () {
        var halfWay = $('body').height() * 0.25;
        if ($(window).scrollTop() >= halfWay) {
            $('.form-customer-feedback .customer-ftoggle').addClass('ani-left');
        } else {
            $('.form-customer-feedback .customer-ftoggle').removeClass('ani-left');
            $('.form-customer-feedback .customer-ftoggle').addClass('ani-right');
        }
    });
    customer_review_leea(jQuery);

    // Kalaviyo form
    $('.popup .popup-click').click(function () {
        $(this).closest('.popup').fadeOut();
        return false;
    });

     $('.popup .close-gray').click(function () {
        $(this).closest('.popup').fadeOut();
        return false;
    });

    var popupOpened = false;
    if ($('body').hasClass('home') || $('body').hasClass('single')) {
        var popupCookie = getCookie('popupOpened');
        if (!popupCookie) {
            $(window).on('scroll', function () {
                if (!popupOpened) {
                    var scrollPosition = $(window).scrollTop() + $(window).height();
                    var totalBodyHeight = $('body').prop('scrollHeight');

                    if (scrollPosition >= totalBodyHeight * 0.7) {
                        popupOpened = true;
                        $('#popup-email').fadeIn();

                        setCookie('popupOpened', 'true', 1);
                    }
                }
            });
        }
    }

    function getCookie(name) {
        var nameEQ = name + "=";
        var ca = document.cookie.split(';');
        for (var i = 0; i < ca.length; i++) {
            var c = ca[i];
            while (c.charAt(0) == ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }

    function setCookie(name, value, days) {
        var d = new Date();
        d.setTime(d.getTime() + (days * 24 * 60 * 60 * 1000));
        var expires = "expires=" + d.toUTCString();
        document.cookie = name + "=" + value + ";" + expires + ";path=/";
    }

    // Menu action 
    $('.hd-search a').click(function () {
        $('.toogle-menu').toggleClass('exit');
        $('.menu-main').slideToggle();
        return false;
    });

    $('.toogle-menu').click(function () {
        $(this).toggleClass('exit');
        $('.menu-main').slideToggle();
        return false;
    });

    $('.menu-main ul li.menu-item-has-children > a').click(function () {
        return false;
    });

    // Schema question
    $('.schema-faq-question').click(function () {
        $(this).next().slideToggle();
        return false;
    });

})

function customer_review_leea($) {
    $('.customer-ftoggle').click(function () {
        $('html').css('overflow', 'hidden');
        $(this).addClass('ani-right');
        $(this).removeClass('ani-left');
        $('.customer-feedback').addClass('ani-fade');
        $('.form-customer-feedback').addClass('ani-fade');
        return false;
    });
    $('.form-customer-feedback .close-btn').click(function () {
        $('.customer-ftoggle').removeClass('ani-right');
        $('.customer-feedback').removeClass('ani-fade');
        $('.form-customer-feedback').removeClass('ani-fade');
        $('.form-customer-feedback .customer-ftoggle').addClass('ani-left');
        $('html').css('overflow', 'auto');
    });
    $('.rating-feedback').rating({
        maxRating: 5,
        initialRating: 3,
        readonly: false,
        step: 1,
    });

    $('.rating-feedback').change(function () {
        $('.form-feedback').show();
        $('.form-hidden-rating').val($('.rating-feedback').val());
        // $('.form-hidden-link').val($('.link-post-feedback').val());
        $('.form-hidden-ip').val($('.ip-address').val());
        var d = new Date();
        var strDate = d.getDate() + "-" + (d.getMonth() + 1) + "-" + d.getFullYear() + " " + d.getHours() + ":" + d.getMinutes() + ":" + d.getSeconds();
        $('.form-date-send').val(strDate).attr('value', strDate);
    });
    $('.form-select').parent().addClass('your-option');

    $('.form-select').change(function () {
        if ($('.form-select').val() != "") {
            $('.form-customer-feedback .your-option').addClass('hide-star');
            $('.form-select').css("color", "#000");
        } else {
            $('.form-customer-feedback .your-option').removeClass('hide-star');
        };
        if ($('.form-select').val() == "") {
            $('textarea.form-group').hide();
        } else {
            $('textarea.form-group').slideDown();
        };
        if ($('.form-select').val() == "Questions") {
            $('.form-customer-feedback .form-group-email').slideDown();
            // $(".form-customer-feedback textarea.form-group").attr("placeholder", "New placeholder text");
        } else {
            $('.form-customer-feedback .form-group-email').hide();
        };
        if ($('.form-select').val() == "Report bug") {
            $(".form-customer-feedback textarea.form-group").attr("placeholder", "Where did you have a technical problem?");
        } else {
            $(".form-customer-feedback textarea.form-group").attr("placeholder", "What would you like to share with us?");
        };
    });
    document.addEventListener('wpcf7mailsent', function () {
        $('.form-customer-feedback .mailsent').show();
        $('.form-customer-feedback .form-feedback, .form-customer-feedback .star-rating').hide();
    }, false);
}