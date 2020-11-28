'use strict';

// https://github.com/zxing-js/library/issues/371
const formats = [
    ZXing.BarcodeFormat.AZTEC,
    ZXing.BarcodeFormat.CODABAR,
    ZXing.BarcodeFormat.CODE_39,
    ZXing.BarcodeFormat.CODE_128,
    ZXing.BarcodeFormat.EAN_8,
    ZXing.BarcodeFormat.EAN_13,
    ZXing.BarcodeFormat.ITF,
    ZXing.BarcodeFormat.PDF_417,
    ZXing.BarcodeFormat.QR_CODE
]
const hints = new Map()
hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, formats)
const codeReader = new ZXing.BrowserMultiFormatReader(hints)
var latestBarcode = null;
var resetLatestBarcodeId = null;

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
            if (latestBarcode != barcode) {
                foundBarcode(barcode);
                latestBarcode = barcode;
                if (resetLatestBarcodeId) {
                    window.clearTimeout(resetLatestBarcodeId);
                    resetLatestBarcodeId = null;
                }
                resetLatestBarcodeId = window.setInterval(function () {
                    latestBarcode = null;
                    resetLatestBarcodeId = null;
                }, 3000);
            }
        }
        if (err && !(err instanceof ZXing.NotFoundException)) {
            console.error(err)
            document.getElementById('result').textContent = err
        }
    })
    console.log(`Started continuos decode from camera with id ${videoSource}`);
}

