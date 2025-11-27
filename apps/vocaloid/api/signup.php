<?php
// Simple signup storing user in SQLite in workspace
$workspace = getenv('WORKSPACE') ?: '/workspace';
$dbfile = $workspace . '/vocaloid.db';
if(!file_exists(dirname($dbfile))){ @mkdir(dirname($dbfile), 0775, true); }
$db = new PDO('sqlite:'.$dbfile);
$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
$db->exec("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT)");

$input = json_decode(file_get_contents('php://input'), true);
if(!$input || !isset($input['username']) || !isset($input['password'])){ http_response_code(400); echo json_encode(['error'=>'missing']); exit; }
$user = preg_replace('/[^a-zA-Z0-9_-]/','', $input['username']);
$pass = $input['password'];
$hash = password_hash($pass, PASSWORD_DEFAULT);
try{
  $stmt = $db->prepare('INSERT INTO users(username,password_hash) VALUES(:u,:p)');
  $stmt->execute([':u'=>$user,':p'=>$hash]);
  echo json_encode(['ok'=>true]);
} catch(Exception $e){ http_response_code(400); echo json_encode(['error'=>'exists']); }
?>
