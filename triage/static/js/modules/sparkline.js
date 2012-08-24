/*global Triage: true*/

Triage.modules.sparkleline = (function($, app) {
	"use strict";

	function renderSparkline() {
		var $sparklines = $(".sparkline");
		$sparklines.each(function() {
			var $line = $(this);
			if(!$line.find('canvas').length) {
				$line.sparkline('html', {
					lineColor: "red",
					fillColor: "pink"
				});
			}

			$line.on('click', function(e) {
				e.stopPropagation();
			});
		});
	}

	return {
		start: function() {
			renderSparkline();
			app.on("nav.reloaded", renderSparkline);
			app.on("nextpage.loaded", renderSparkline);
		},
		stop: function() {

		}
	};
});

Triage.modules.sparkleline.autoRegister = true;
