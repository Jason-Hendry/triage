(function($, moment, Highcharts) {
	"use strict";

	var Graph = function(id) {
		var self = this;

		this.categories = [];
		this.occurrences = [];

		this.render = function(title, width, height) {
			self.chart = new Highcharts.Chart({
				chart: {
					renderTo: id,
					type: 'line',
					marginRight: 130,
					marginBottom: 25,
					width: width,
					height: height
				},
				title: {
					text: title,
					x: -20 //center
				},
				subtitle: {
					text: '',
					x: -20
				},
				xAxis: {
					categories: self.categories
				},
				yAxis: {
					title: {
						text: 'Number of occurrences'
					},
					plotLines: [{
					value: 0,
					width: 1,
					color: '#808080'
					}]
				},
				tooltip: {
					formatter: function() {
						return '<b>'+ this.series.name +'</b><br/>'+
						this.y +' times this bug appeared';
					}
				},
				legend: {
					layout: 'vertical',
					align: 'right',
					verticalAlign: 'top',
					x: -10,
					y: 100,
					borderWidth: 0
				},
				series: [{
					name: 'occurrences',
					data: self.occurrences
				}]
			});
		};
	};

	function getPeriods($occurrences, type) {
		return $occurrences.map(function() {
			var
				oneHour = 3600000,
				oneDay = 86400000,
				timestamp = parseInt($(this).data('period'), 10),
				m = moment.unix(timestamp)
				;

			var diff = moment.utc().diff(m);

			if (diff > oneDay) {
				if (type === "month") {
					return m.format("MMM");
				}

				return m.format("MMM Do");
			} else if (diff > oneHour) {
				return m.format("ha");
			} else {
				var text = {
					hour: "This hour",
					day: "Today",
					month: "This month"
				};
				return text[type];
			}
		});
	}

	function getOccurrences($occurrences) {
		return $occurrences.map(function() { return parseInt($(this).text(), 10); });
	}

	function renderGraph($container, title, type) {
		var
			$occurrences = $container.find('.' + type + ' .occurrence'),
			graph = new Graph('graph-display-' + type)
			;

		graph.categories = getPeriods($occurrences, type);
		graph.occurrences = getOccurrences($occurrences);
		graph.render(title, 1200, 200);
	}

	$(function() {
		var $graph = $('.graph');
		renderGraph($graph, 'Hourly frequency graph', 'hour');
		renderGraph($graph, 'Daily frequency graph', 'day');
	});
})(jQuery, moment, Highcharts);
