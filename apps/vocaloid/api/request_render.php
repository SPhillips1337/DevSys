<?php
// Create a render job under workspace/render_jobs/<uuid>/job.json
// Use WORKSPACE env variable if present; prefer /workspace as canonical shared location
$workspace = getenv('WORKSPACE') ?: '/workspace';

// Ensure workspace exists and is writable
if (!is_dir($workspace)) {
    if (!@mkdir($workspace, 0775, true)) {
        http_response_code(500);
        echo json_encode(['error' => 'workspace_create_failed', 'message' => 'Failed to create workspace directory']);
        exit;
    }
}
if (!is_writable($workspace)) {
    http_response_code(500);
    echo json_encode(['error' => 'workspace_not_writable', 'message' => 'Workspace is not writable by the web process']);
    exit;
}

$input = json_decode(file_get_contents('php://input'), true);
if(!$input || !isset($input['username']) || !isset($input['text'])){ http_response_code(400); echo json_encode(['error'=>'missing']); exit; }
$user = preg_replace('/[^a-zA-Z0-9_-]/','', $input['username']);
$text = $input['text'];
$jobid = 'render-' . bin2hex(random_bytes(6));
$jobdir = $workspace . '/render_jobs/' . $jobid;

// Create job directory
if (!@mkdir($jobdir, 0775, true)) {
    http_response_code(500);
    echo json_encode(['error' => 'jobdir_create_failed', 'message' => 'Failed to create job directory']);
    exit;
}

$job = ['id'=>$jobid, 'user'=>$user, 'text'=>$text, 'status'=>'queued', 'created_at'=>date('c')];
$json = json_encode($job);
if (file_put_contents($jobdir . '/job.json', $json) === false) {
    http_response_code(500);
    echo json_encode(['error' => 'job_write_failed', 'message' => 'Failed to write job file']);
    exit;
}

// The renderer worker will pick up the job and write output file and update status
$public_url = '/workspace/render_jobs/' . $jobid . '/output.mp3';
// For demo return a placeholder URL (worker will update later)
echo json_encode(['job_id'=>$jobid, 'url'=>$public_url]);
?>
