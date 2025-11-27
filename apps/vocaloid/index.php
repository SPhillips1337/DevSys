<?php
// Simple front page for Vocaloid PoC
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Vocaloid PoC</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
<div class="container py-4">
  <h1>Vocaloid PoC</h1>
  <p>Create an account, record a small set of phonemes, and render text using your voice.</p>

  <div id="auth" class="mb-4">
    <h4>Signup</h4>
    <form id="signup-form">
      <div class="mb-2">
        <input class="form-control" id="signup-username" placeholder="username">
      </div>
      <div class="mb-2">
        <input type="password" class="form-control" id="signup-password" placeholder="password">
      </div>
      <button class="btn btn-primary" id="signup-btn">Sign up</button>
    </form>
  </div>

  <div id="recorder" style="display:none;">
    <h4>Phoneme wizard</h4>
    <p id="current-phoneme-label">Current phoneme: <strong id="phoneme-name"></strong></p>
    <button class="btn btn-secondary" id="start-record">Start Recording</button>
    <button class="btn btn-secondary" id="stop-record" disabled>Stop</button>
    <audio id="preview" controls></audio>
    <div class="mt-3">
      <button class="btn btn-success" id="save-sample">Save sample</button>
    </div>
  </div>

  <div id="render" style="display:none;" class="mt-4">
    <h4>Render text</h4>
    <textarea id="render-text" class="form-control" rows="3" placeholder="Enter sentence"></textarea>
    <div class="mt-2">
      <button class="btn btn-primary" id="request-render">Request Render</button>
    </div>
    <div class="mt-3" id="render-result"></div>
  </div>

</div>

<script src="recorder.js"></script>
</body>
</html>
