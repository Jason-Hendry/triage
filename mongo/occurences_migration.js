var name = "hourly_occurrences";

db[name].drop();
db.createCollection(name);
db[name].ensureIndex({key: 1}, {unique: true});
db[name].ensureIndex({hash: 1});

function create_or_update(instance) {
	function getKey(instance) {
		var d = new Date(instance.timestamp * 1000);
		return d.getUTCFullYear() + "-" + d.getUTCMonth() + "-" + d.getUTCDate() + "-" + d.getUTCHours();
	}

	var key = getKey(instance);
	var occurrence = db[name].findOne({key: key, hash: instance.hash});

	if (occurrence) {
		occurrence.count++;
		db[name].save(occurrence);
	} else {
		db[name].insert({
			_types: [ "HourlyOccurrences" ],
			_cls: "HourlyOccurrences",
			hash: instance.hash,
			key: key,
			timestamp: instance.timestamp,
			count: 1
		});
	}
}

var instances = db.error_instance.find().sort({timestamp: 0});

for (var i = 0; i < instances.count(); i++) {
	create_or_update(instances[i]);
}
