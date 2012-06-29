(function($) {

    var Graph = function(id) {
		var self = this;

		this.categories = [];
		this.occurences = [];

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
			            text: 'Number of occurences'
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
			        name: 'occurences',
			        data: self.occurences
			    }]
			});
		};
	};

	function getPeriods($occurences) {
		return $occurences.map(function() { return $(this).data('period'); });
	}

	function getOccurences($occurences) {
		return $occurences.map(function() { return parseInt($(this).text(), 10); });
	}

	$(function() {
		var $graph = $('.graph');
		var $hourlyOccurences = $graph.find('.hourly .occurence');
		var $dailyOccurences = $graph.find('.daily .occurence');
	    var hourlyGraph = new Graph('graph-display-hourly');
	    var dailyGraph = new Graph('graph-display-daily');

	    hourlyGraph.categories = getPeriods($hourlyOccurences);
	    hourlyGraph.occurences = getOccurences($hourlyOccurences);
		hourlyGraph.render('Hourly frequency chart', 600, 200);

	    dailyGraph.categories = getPeriods($dailyOccurences);
	    dailyGraph.occurences = getOccurences($dailyOccurences);
		dailyGraph.render('daily frequency chart', 600, 200);
	});
})(jQuery);
