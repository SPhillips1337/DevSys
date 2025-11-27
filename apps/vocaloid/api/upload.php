<?php
// Accept uploaded phoneme recording and save under workspace/users/<username>/phonemes/<phoneme>.webm
$workspace = getenv('WORKSPACE') ?: '/workspace';
if(!file_exists($workspace)) mkdir($workspace,0775,true);
$user = $_POST['username'] ?? null;
$phoneme = $_POST['phoneme'] ?? null;
if(!$user || !$phoneme || !isset($_FILES['file'])){ http_response_code(400); echo json_encode(['error'=>'missing']); exit; }
$user = preg_replace('/[^a-zA-Z0-9_-]/','', $user);
$phoneme = preg_replace('/[^A-Z0-9_]/','', strtoupper($phoneme));
$destdir = $workspace . '/users/' . $user . '/phonemes';
if(!file_exists($destdir)) mkdir($destdir, 0775, true);
$fname = $destdir . '/' . $phoneme . '.webm';
if(move_uploaded_file($_FILES['file']['tmp_name'], $fname)){
  echo json_encode(['ok'=>true,'path'=>$fname]);
} else {
  http_response_code(500); echo json_encode(['error'=>'save_failed']);
}
?>
