var name = "hourly_occurrences";

db[name].drop();
db.createCollection(name);
db[name].ensureIndex({key: 1}, {unique: true});
db[name].ensureIndex({hash: 1});

function createOrUpdate(instance) {
	function getUTC(instance) {
		var d = new Date(instance.timestamp * 1000);
		return {
			key: d.getUTCFullYear() + "-" + (d.getUTCMonth() + 1) + "-" + d.getUTCDate() + "-" + d.getUTCHours(),
			timestamp: Math.floor(d.getTime()/ 1000)
		};
	}

	var utc = getUTC(instance);
	var occurrence = db[name].findOne({key: utc.key, hash: instance.hash});

	if (occurrence) {
		occurrence.count++;
		db[name].save(occurrence);
	} else {
		db[name].insert({
			_types: [ "HourlyOccurrences" ],
			_cls: "HourlyOccurrences",
			hash: instance.hash,
			key: utc.key,
			project: instance.project,
			timestamp: utc.timestamp,
			count: 1
		});
	}
}

var instances = db.error_instance.find().sort({timestamp: 0});

for (var i = 0; i < instances.count(); i++) {
	createOrUpdate(instances[i]);
}
