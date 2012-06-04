/*global Triage: true*/

Triage.modules.errorNav = (function($, app) {
	"use strict";

	var show = 'open';
	var orderBy = 'date';
	var direction = 'desc';
	var rowsLoaded = 0;
	var search;
	var lastLoaded;

	var buildUrl = function() {

		var params = {
			show: show,
			order_by: orderBy, 
			direction: direction,
			timelatest: lastLoaded
		};

		if (search) {
			params['search'] = search;
		}

		if (rowsLoaded) {
			params['start'] = rowsLoaded; // start is 0 indexed
		}

		return window.location.origin + window.location.pathname + '?' + $.param(params);
	};

	var reloadList = function() {
		rowsLoaded = 0;

		lastLoaded = Math.floor(Date.now() / 1000);
		app.trigger('nav.reloading', lastLoaded);

		$.ajax({
			url: buildUrl(),
			dataType: 'html',
			success: function(data){
				$('.error-list tbody').html(data);
				$('.changes-info').hide();
				rowsLoaded = $('.error-list tbody tr').length;
				app.trigger('nav.reloaded', lastLoaded);
			}
		});
	};

	var loadNextPage = function() {
		var button = $(this);

		rowsLoaded = $('.error-list tbody tr').length;
		button.attr('disabled', true).find('i').addClass('icon-loader');

		$.ajax({
			url: buildUrl(),
			dataType: 'html',
			success: function(data){
				button.attr('disabled', false).find('i').removeClass('icon-loader');
				$('.error-list tbody').append(data);
				rowsLoaded = $('.error-list tbody tr').length;
			}
		});
	};

	var updateShowTabs = function(tab) {

		show = tab.data('name');
		tab.siblings().removeClass('active').addClass('inactive');
		tab.removeClass('inactive').addClass('active');

		app.trigger('system.activecountchanged', parseInt(tab.find('.count').text()));

		reloadList();
	};


	var updateOrderTabs = function(tab) {

		orderBy = tab.data('name');

		if (tab.hasClass('active')) {

			if (direction == 'desc') {
				tab.removeClass('desc').addClass('asc');
				direction = 'asc';
			} else {
				tab.removeClass('asc').addClass('desc');
				direction = 'desc';
			}

		} else {
			tab.siblings().removeClass('active').addClass('inactive');
			tab.removeClass('inactive').addClass('active');
			tab.removeClass('asc').removeClass('desc').addClass(direction);
		}

		reloadList();
	};

	var checkForUpdates = function() {
		var params = {
			show: show,
			timelatest: lastLoaded
		};
		if (search) {
			params['search'] = search;
		}			

		var url = window.location.origin + window.location.pathname
			+ '/changes?' + $.param(params);

		$.ajax({
			url: url,
			dataType: 'json',
			success: function(data){
				if (data) {
					app.trigger('nav.newchanges', data);
				}
			}
		});
	};

	return {
		start: function() {
			$('#error-tabs li').on('click', function() {
				updateShowTabs($(this));
				return false;
			});

			$('#order-items li').on('click', function() {
				updateOrderTabs($(this));
				return false;
			});

			$('#errorlist-search').on('submit', function() {
				search = $(this).find('.searchfield').val();
				reloadList();
				return false;
			});

			$('.changes-info .reload').on('click', function() {
				reloadList();
				return false;		
			})

			$('#aggregate-action-container a').on('click', function() {
				alert("Not implemented. Go to https://github.com/lwc/triage to fork and fix.");
				return false;
			})

			app.on('error.seen', function(errorId) {
				var currentTab = $('#error-tabs li.active');
				var count;

				if (currentTab.data('name') != 'mine') {
					count = parseInt(currentTab.find('.count').text())-1;
					currentTab.find('.count').text(count);
					app.trigger('system.activecountchanged', count);
				}

			});

			app.on('nav.newchanges', function(count){
				$('.changes-info').slideDown().find('.errcount').text(count);
			});

			$(function() {
				var count = $('#error-tabs li.active .count');
				app.trigger('system.activecountchanged', parseInt(count.text()));

				lastLoaded = parseInt($('.error-list tbody tr:first-child').data('timelatest'));

				window.setInterval(checkForUpdates, 600000);			
			});


			$('#loadmore').on('click', loadNextPage);
		},
		stop: function() {
			$('#loadmore').on('click', loadNextPage);
		}
	};
});

Triage.modules.errorNav.autoRegister = true;
