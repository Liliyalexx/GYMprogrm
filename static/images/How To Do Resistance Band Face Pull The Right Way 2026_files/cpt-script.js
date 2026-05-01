
jQuery(window).on('load', function () {
	var $ = jQuery;
	$('figure table').each(function () {
		var $table = $(this);
		var $ths1 = $table.find('th:nth-child(1)');
		var $ths2 = $table.find('th:nth-child(2)');
		var maxHeight = $ths2.innerHeight();
		var currentHeight = $ths1.innerHeight()

		if (maxHeight > currentHeight) {
			$ths1.height(maxHeight - currentHeight);
		}

		if ($(window).width() >= 767) {
			var $headers = $table.find('thead th');
			var $cells = $table.find('tbody td');

			var numberOfColumns = $headers.length;

			if ($(this).closest('.table-custom-4').length > 0) {
				$table.css('table-layout', 'auto');

				$headers.eq(0).css({
					'width': '20%',
					'text-align': 'center'
				});
				$table.find('tbody td:nth-child(1)').css({
					'width': '20%',
					'text-align': 'center'
				});

				var totalWidth = $table.outerWidth(true);
				var remainingColumns = numberOfColumns - 1;

				if (remainingColumns > 0) {
					var remainingWidth = $table.width() - $headers.eq(0).outerWidth(true);
					var eachWidth = remainingWidth / remainingColumns;

					for (var i = 1; i < numberOfColumns; i++) {
						$headers.eq(i).css('width', eachWidth + 'px');
						$table.find('tbody td:nth-child(' + (i + 1) + ')').css('width', eachWidth + 'px');
					}
				}
			}
			else if (numberOfColumns <= 3) {
				if (!$table.closest('.no-scroll').length) {
					var tableWidth = $table.outerWidth(true);
					var columnWidth = (tableWidth - 1) / numberOfColumns;

					$headers.css('width', columnWidth + 'px');
					$cells.css('width', columnWidth + 'px');
				}
			}

		}
		else {
			if ($(window).width() <= 767) {
				var $headers = $table.find('thead th');
				var $cells = $table.find('tbody td');

				var numberOfColumns = $headers.length;

				if (numberOfColumns >= 3) {
					var tableWidth = $table.outerWidth(true);
					var columnWidth = tableWidth - 155;

					$headers.css('width', columnWidth + 'px');
					$cells.css('width', columnWidth + 'px');
				} else if (numberOfColumns == 3) {
					var tableWidth = $table.outerWidth(true);
					var columnWidth = tableWidth - 155;

					$headers.css('width', columnWidth + 'px');
					$cells.css('width', columnWidth + 'px');
				} else if (numberOfColumns <= 2) {
					if ($table.closest('.no-scroll').length > 0) {
						var tableWidth = $table.outerWidth(true);
						var columnWidth = tableWidth - 155;

						$headers.each(function () {
							$(this)[0].style.setProperty('width', columnWidth + 'px', 'important');
						});
						$cells.each(function () {
							$(this)[0].style.setProperty('width', columnWidth + 'px', 'important');
						});
					}
				}
			}

			if (!$table.closest('.no-scroll').length) {
				$table.find('tbody tr').each(function () {
					var $tr = $(this);
					var $td1 = $tr.find('td:nth-child(1)');
					var rowHeight = $tr.innerHeight();

					$td1.height(rowHeight);

					if ($td1.find('p').length === 0) {
						var content = $td1.html().trim();
						$td1.html('<p>' + content + '</p>');
					}

					$td1.find('p').css({
						position: 'absolute',
						top: '50%',
						left: '50%',
						transform: 'translate(-50%, -50%)',
						margin: 0,
						textAlign: 'center',
						width: '100%'
					});
				});
			}

		}
	});
});
jQuery(document).ready(function ($) {
	if ($('.prefer-section').length === 0) {
        var html = `
        <div class="prefer-section flex">
            <div class="prefer-btn">
                <a style="display:flex; text-align:left"
                    href="https://google.com/preferences/source?q=endomondo.com" target="_blank">
                    <img src="https://www.endomondo.com/wp-content/themes/endonondo/assets/images/prefer-google-2x.png"
                        alt="">
                </a>
            </div>
            <div class="prefer-text">
                <p><b style="color: #101010">Want to stay on top of your fitness journey?</b></p>
                <p class="has-small-font-size">
				Get the latest workout guides, training programs, fitness news, and much more by
				<a 
                    href="https://google.com/preferences/source?q=endomondo.com" target="_blank">
                    adding Endomondo.com as a Preferred Source.
                </a>
                </p>
            </div>
        </div>
        `;
        $('h2.wp-block-heading').first().before(html);
    }
	// Figure Table Style

	// at-eb box
	$(document).on('click', '#at-box, #eb-box', function () {
		var label = $(this).data('label');
		$('.fact-label.' + label).fadeToggle();
		$('.modalcn-bg').fadeIn();
		return false;
	});
	$(document).on('click', function (e) {
		if ($(e.target).closest(".fact-check").length === 0) {
			$('.fact-label').fadeOut();
			$('.modalcn-bg').fadeOut();
		}
	});

	// Template-part Resource action
	$(".single-main .sg-resources > h3").on('click', function () {
		$(this).siblings("ol").slideToggle();
		$(this).toggleClass("up");
	});

	// Primary Muscle Slide

	$('.primary-muscle').slick({
		infinite: true,
		slidesToShow: 3,
		slidesToScroll: 1,
		autoplay: false,
		arrows: false,
		dots: true,
		responsive: [
			{
				breakpoint: 820,
				settings: {
					slidesToShow: 3
				}
			},
			{
				breakpoint: 768,
				settings: {
					slidesToShow: 2
				}
			}, {
				breakpoint: 431,
				settings: {
					slidesToShow: 1
				}
			}, {
				breakpoint: 320,
				settings: {
					slidesToShow: 1
				}
			}
		]
	});

})