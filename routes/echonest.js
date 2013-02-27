var echojs = require('echojs');
var request = require('request');

var echo = echojs({
  key: process.env.ECHO_KEY
});

function cleanString(str){
	var cleanStr = '';
	for (var i = 0; i < str.length; i++){
		if (str.charCodeAt(i) != 0){
			cleanStr += str[i];
		}
	}
	return cleanStr;
}

exports.getInfo = function(req, res){
	var title = cleanString(req.body.song);
	var artist = cleanString(req.body.artist);
	console.log(title,artist);
	echo('song/search').get({
		artist: artist,
		title: title
	}, function (err, json) {
		// console.log(json.response);
		var id = json.response.songs[0].id;
		console.log(id);
		echo('song/profile').get({
			id: id,
			bucket: 'audio_summary'
		}, function (err, json) {
			// console.log(json.response);
			var dataURL = json.response.songs[0].audio_summary.analysis_url;
			if (dataURL != undefined){
				request(dataURL, function (error, response, body) {
					if (!error && response.statusCode == 200) {
						var data = JSON.parse(body);
						var segs = data.segments;
						var segList = [];
						for (var i = 0; i < segs.length; i++){
							var start = segs[i].start;
							var end = start+segs[i].duration;
							var track = Math.floor(segs[i].pitches.indexOf(1)/2);
							var confidence = segs[i].confidence
							if (confidence > 0.5){
								segList.push([start,end,track,confidence]);
							}
						}
						res.send(segList);
						// console.log(data.track.synchstring)
					}
					else{
						console.log('error getting data');
					}
				})			
			}
			else{
				console.log('error finding data');
			}
		});
	});
};