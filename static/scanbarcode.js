'use strict';

const codeReader = new ZXing.BrowserMultiFormatReader()
var seenBarcodes = new Set();

window.addEventListener("load", function () {
    start();
});

function foundBarcode(barcode) {
    var data = new FormData();
    fetch('/processbarcode', {
        headers: {
            'Content-Type': 'application/json'
        },
        method: "POST",
        body: JSON.stringify({ "barcode": barcode, "bggid": bggid, "putaway": putaway })
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

// The camid changes at reboot (and maybe other times)
// Save the camera name displayed to the user
function saveCamera(cam) {
    console.debug("Saving camera", cam);
    window.localStorage.setItem("camera", cam);
}

function getCamera() {
    var ret = window.localStorage.getItem("camera");
    console.debug("Returning camera", ret);
    return ret;
}

function selectVideo(but) {
    videoSource = this.value;
    saveCamera(this.innerText);
    start();
}

function gotDevices(deviceInfos) {
    // Handles being called several times to update labels.
    while (videoButtons.firstChild) {
        videoButtons.removeChild(videoButtons.firstChild);
    }
    var lastcamera = getCamera();
    for (let i = 0; i !== deviceInfos.length; ++i) {
        const deviceInfo = deviceInfos[i];
        const button = document.createElement('button');
        button.value = deviceInfo.deviceId;
        button.classList.add('btn');
        button.classList.add('btn-primary');
        if (deviceInfo.kind === 'videoinput') {
            var space = document.createElement('span');
            space.innerHTML = "&nbsp;";
            videoButtons.appendChild(space);
            button.innerText = deviceInfo.label || `camera ${i}`;
            if (button.innerText == lastcamera && videoSource != deviceInfo.deviceId) {
                videoSource = deviceInfo.deviceId;
                start();
            }
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
    const constraints = {
        video: { width: 1280, height: 720, deviceId: videoSource ? { exact: videoSource } : undefined }
    };
    navigator.mediaDevices.getUserMedia(constraints).then(gotStream).then(gotDevices).catch(handleError);

    codeReader.reset();
    codeReader.decodeFromVideoDevice(videoSource, 'video', (result, err) => {
        if (result) {
            console.log(result);
            var barcode = result.text;
            if (!seenBarcodes.has(barcode)) {
                foundBarcode(barcode);
                seenBarcodes.add(barcode);
            }
        }
        if (err && !(err instanceof ZXing.NotFoundException)) {
            console.error(err)
            document.getElementById('result').textContent = err
        }
    })
    console.log(`Started continuos decode from camera with id ${videoSource}`);
}

