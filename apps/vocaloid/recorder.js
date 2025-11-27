// Simple MediaRecorder-based recorder and uploader
const phonemes = ['AA','AE','AH','AO','EH','ER','IH','IY','OW','UH','S','T','K'];
let currentIndex = 0;
let mediaRecorder;
let chunks = [];
let username = null;

function $(id){return document.getElementById(id)}

async function signup(e){
  e.preventDefault();
  const user = $('signup-username').value;
  const pass = $('signup-password').value;
  const resp = await fetch('api/signup.php', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username:user,password:pass})});
  if(resp.ok){
    username = user;
    $('auth').style.display='none';
    $('recorder').style.display='block';
    $('render').style.display='block';
    loadPhoneme();
  } else {
    alert('Signup failed');
  }
}

function loadPhoneme(){
  $('phoneme-name').innerText = phonemes[currentIndex];
}

async function startRecording(){
  const stream = await navigator.mediaDevices.getUserMedia({audio:true});
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => chunks.push(e.data);
  mediaRecorder.onstop = e => {
    const blob = new Blob(chunks, {type:'audio/webm'});
    $('preview').src = URL.createObjectURL(blob);
    window.latestBlob = blob;
    chunks = [];
  }
  mediaRecorder.start();
  $('start-record').disabled = true; $('stop-record').disabled = false;
}

function stopRecording(){
  mediaRecorder.stop();
  $('start-record').disabled = false; $('stop-record').disabled = true;
}

async function saveSample(){
  if(!window.latestBlob){ alert('No recording'); return; }
  const phoneme = phonemes[currentIndex];
  const fd = new FormData();
  fd.append('file', window.latestBlob, phoneme + '.webm');
  fd.append('phoneme', phoneme);
  fd.append('username', username);
  const resp = await fetch('api/upload.php', {method:'POST', body:fd});
  if(resp.ok){
    alert('Saved ' + phoneme);
    currentIndex = (currentIndex+1) % phonemes.length;
    loadPhoneme();
  } else {
    alert('Upload failed');
  }
}

async function requestRender(){
  const text = $('render-text').value;
  const resp = await fetch('api/request_render.php', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({username, text})});
  if(resp.ok){
    const j = await resp.json();
    $('render-result').innerHTML = `<p>Job created: ${j.job_id}</p><audio controls src="${j.url}"></audio>`;
  } else {
    alert('Render request failed');
  }
}

$('signup-form').addEventListener('submit', signup);
$('start-record').addEventListener('click', startRecording);
$('stop-record').addEventListener('click', stopRecording);
$('save-sample').addEventListener('click', saveSample);
$('request-render').addEventListener('click', requestRender);
