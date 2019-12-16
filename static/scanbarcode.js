'use strict';

window.addEventListener("load", function () {
    // [1] GET ALL THE HTML ELEMENTS
    var takeelem = document.getElementById("vid-take");
    takeelem.addEventListener("click", takeimage);
});

function takeimage() {
    var videoelem = document.getElementById("video");
    var canvaselem = document.getElementById("vid-canvas");
    shutter();
    // Create snapshot from video
    var draw = document.createElement("canvas");
    draw.width = videoelem.videoWidth;
    draw.height = videoelem.videoHeight;
    var context2D = draw.getContext("2d");
    context2D.drawImage(videoelem, 0, 0, videoelem.videoWidth, videoelem.videoHeight);
    // Create snapshot from video
    canvaselem.innerHTML = "";
    canvaselem.appendChild(draw)
    // Upload to server
    draw.toBlob(function (blob) {
        var data = new FormData();
        data.append('json', JSON.stringify({ "bggid": bggid, "putaway": putaway }));
        data.append('upimage', blob);
        fetch('/processbarcode', {
            method: 'POST',
            body: data
        })
            .then(function (response) {
                return response.json();
            })
            .then(function (response) {
                var alrt = document.getElementById('alert');
                alrt.innerHTML = response['html'];
                alrt.classList.add('on');
                if (response['js']) {
                    eval(response['js']);
                }
            })
    }, "image/jpeg");
}

function shutter() {
    $('#shutter').addClass('on');
    setTimeout(function () {
        $('#shutter').removeClass('on');
    }, 30 * 2 + 45);/* Shutter speed (double & add 45) */
}


const videoElement = document.querySelector('video');
const videoButtons = document.querySelector('#sourcebuttons');
//const selectors = [videoSelect];
var videoSource = undefined;

function selectVideo(but) {
    videoSource = this.value;
    window.localStorage.setItem("camera", this.value);
    start();
}

function gotDevices(deviceInfos) {
    // Handles being called several times to update labels. Preserve values.
    while (videoButtons.firstChild) {
        videoButtons.removeChild(videoButtons.firstChild);
    }
    var lastcamera = window.localStorage.getItem("camera");
    for (let i = 0; i !== deviceInfos.length; ++i) {
        const deviceInfo = deviceInfos[i];
        const button = document.createElement('button');
        button.value = deviceInfo.deviceId;
        button.classList.add('btn');
        button.classList.add('btn-primary');
        if (deviceInfo.kind === 'videoinput') {
            if (deviceInfo.deviceId == lastcamera && videoSource != deviceInfo.deviceId) {
                videoSource = deviceInfo.deviceId;
                start();
            }
            var space = document.createElement('span');
            space.innerHTML = "&nbsp;";
            videoButtons.appendChild(space);
            button.innerText = deviceInfo.label || `camera ${i}`;
            button.onclick = selectVideo;
            videoButtons.appendChild(button);
        } else {
            console.log('Not a video device: ', deviceInfo);
        }
    }
}

navigator.mediaDevices.enumerateDevices().then(gotDevices).catch(handleError);

function gotStream(stream) {
    window.stream = stream; // make stream available to console
    videoElement.srcObject = stream;
    // Refresh button list in case labels have become available
    return navigator.mediaDevices.enumerateDevices();
}

function handleError(error) {
    console.log('navigator.MediaDevices.getUserMedia error: ', error.message, error.name);
}

function start() {
    if (window.stream) {
        window.stream.getTracks().forEach(track => {
            track.stop();
        });
    }
    //const videoSource = videoSelect.value;
    const constraints = {
        video: { width: 1280, height: 720, deviceId: videoSource ? { exact: videoSource } : undefined }
    };
    navigator.mediaDevices.getUserMedia(constraints).then(gotStream).then(gotDevices).catch(handleError);
}

//videoSelect.onchange = start;

start();

