var trackInfo = [];
var canvas, ctx, aCtx, microphone, analyser;
var audioBuffer = [];
var colors = ['rgb(51,153,51','rgb(240,150,9)','rgb(27,161,226)','rgb(229,20,0)','rgb(162,0,255)','rgb(216,0,155)']
var codeToTrack = {'65':0,'83':1,'68':2,'70':3,'71':4,'72':5}
var streak = 0;
var score = 0;
var correct = 0;
var multiplier = 0;

function cleanSong(song){
  if (song.indexOf('TPE1') != -1){
    song = song.slice(0,song.indexOf('TPE1'));
  }
  else{
    console.log('weird song format');
  }
  return song;
}

function cleanArtist(artist){
  if (artist.indexOf('TPE2') != -1){
    artist = artist.slice(0,artist.indexOf('TPE2'));
  }
  else if (artist.indexOf('TALB') != -1){
    artist = artist.slice(0,artist.indexOf('TALB'));
  }
  else if (artist.indexOf('TCOM') != -1){
    artist = artist.slice(0,artist.indexOf('TCOM'));
  }
  else {
    console.log('werid artist format');
  }
  return artist;
}

function playSound() {
  analyser = aCtx.createAnalyser();
  analyser.fftSize = 2048;
  analyser.smothingTimeConstant = 0;
  source = aCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(analyser);
  analyser.connect(aCtx.destination);
  console.log('starting')
  source.start(0);
  draw();
}

var calls = 0;
function checkReady(){
  calls += 1;
  if (calls > 1){
    playSound();
  }
}

var pixPerSec = 150;
function draw(){
  requestAnimFrame(draw,canvas);
  var time = aCtx.currentTime;
  ctx.clearRect(0,0,canvas.width,canvas.height);
  for (var i = 0; i < trackInfo.length; i++){
    var note = trackInfo[i];
    var len = note[1]-note[0];
    var startY = note[0]*pixPerSec;
    var height = 10;
    var track = note[2];
    var color = colors[track];
    var trackWidth = canvas.width/6;
    var trackX = trackWidth*track;
    ctx.save();
    ctx.translate(0,time*pixPerSec);
    ctx.fillStyle = color;
    ctx.fillRect(trackX,-startY+canvas.height,trackWidth,height);
    ctx.restore();
  }
  ctx.fillRect(0,canvas.height-1,canvas.width,1);
}

function checkAccuracy(code,time,trackInfo){
  var distances = [];
  for (var i = 0; i < trackInfo.length; i++){
    var segStart = trackInfo[i][0]
    distances[i] = Math.abs(segStart-time);
  }
  var min = Math.max.apply(null,distances);
  var index = 0;
  for (var i = 0; i < distances.length; i++){
    if (distances[i] < min){
      min = distances[i];
      index = i;
    }
  }
  var track = trackInfo[index][2]
  var trackPress = codeToTrack[code];
  console.log(min,track,trackPress)
  if ((track == trackPress) && min < 0.1){
    return true;
  }
  else {
    return false;
  }
}

$(function () {
  // requestAnim shim layer by Paul Irish
  window.requestAnimFrame = (function(){
    return  window.requestAnimationFrame       || 
            window.webkitRequestAnimationFrame || 
            window.mozRequestAnimationFrame    || 
            window.oRequestAnimationFrame      || 
            window.msRequestAnimationFrame     || 
            function(callback, element){
              window.setTimeout(callback, 1000 / 60);
            };
  })();
  $('#selectSongUI').click(function(){
    $('#selectSongUI').fadeOut(333);
    $('#selectSong').click();
  });

  canvas = document.getElementById('canvas');
  canvas.width = 450;
  canvas.height = 728;
  ctx = canvas.getContext('2d');
  $(document).keydown(function(e){
    var code = (e.keyCode ? e.keyCode : e.which);
    var time = aCtx.currentTime;
    if (checkAccuracy(code,time,trackInfo)){
      streak += 1;
      multiplier = Math.floor(streak,5)+1;
      correct += 1;
      score += (100*multiplier)
    }
    else{
      streak = 0;
    }
    // console.log(streak);
    $('#streak').html(streak);
    $('#score').html(score);
    // $('#percent').html(percent);
  });

  document.querySelector('input[type="file"]').onchange = function(e) {
    var reader = new FileReader();
    var reader2 = new FileReader();
    reader.onload = function(e) {
      var res = this.result;
      if (res.slice(0,3) != 'ID3'){
        console.log('no ID3 tags');
      }
      else{
        var rawTags = res.slice(0,200).split('ÿþ');
        if (rawTags.length > 4){
          var song = cleanSong(rawTags[1]);
          var artist = cleanArtist(rawTags[2]);
          $.post('/getInfo',
            {song:song,artist:artist},
            function(data){
              trackInfo = data;
              checkReady();
            });        
        }
        else{
          console.log('error at ID3 tags');
        }
      }
    };

    reader2.onload = function(e){
      var arrayBuffer = this.result;
      console.log(arrayBuffer);
      console.log('initSound called');
      aCtx = new webkitAudioContext();
      aCtx.decodeAudioData(arrayBuffer, function(buffer) {
        // audioBuffer is global to reuse the decoded audio later.
        audioBuffer = buffer;
        checkReady();
      }, function(e) {
        console.log('Error decoding file', e);
      });
    }
    reader.readAsBinaryString(this.files[0]);
    reader2.readAsArrayBuffer(this.files[0]);
  };
});