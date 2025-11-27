#!/usr/bin/env python3
# Simple renderer worker skeleton: polls workspace/render_jobs for job.json and attempts a render
import os
import time
import json
import requests
import shlex
import subprocess

WORKSPACE = os.environ.get('WORKSPACE','/workspace')
OLLAMA_URL = os.environ.get('OLLAMA_URL','https://automatically-bedford-horse-solutions.trycloudflare.com/')
OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL','qwen2.5:7b-instruct-q4_K_M')
OLLAMA_KEY = os.environ.get('OLLAMA_KEY','dummy_key')

PHONEME_VOCAB = ['AA','AE','AH','AO','EH','ER','IH','IY','OW','UH','S','T','K']

def list_jobs():
    root = os.path.join(WORKSPACE,'render_jobs')
    if not os.path.exists(root):
        return []
    return [os.path.join(root,d) for d in os.listdir(root) if os.path.isdir(os.path.join(root,d))]

def read_job(jobdir):
    p = os.path.join(jobdir,'job.json')
    if not os.path.exists(p):
        return None
    with open(p,'r') as f:
        return json.load(f)

def write_job(jobdir, job):
    with open(os.path.join(jobdir,'job.json'),'w') as f:
        json.dump(job,f,indent=2)

def call_ollama_phoneticize(text):
    # Simple wrapper to call the Ollama-like endpoint; we expect JSON back {"phonemes": ["AH","T",...]}
    # This is a placeholder; adapt to actual Ollama API shape
    try:
        payload = {"model": OLLAMA_MODEL, "prompt": f"Phoneticize into ARPAbet tokens: {text}", "max_tokens": 256}
        headers = {'Content-Type':'application/json'}
        if OLLAMA_KEY:
            headers['Authorization'] = f"Bearer {OLLAMA_KEY}"
        r = requests.post(OLLAMA_URL + '/api/generate', json=payload, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            # naive extraction
            out = data.get('result') or data.get('output') or data
            # For PoC assume comma-separated tokens
            if isinstance(out, str):
                toks = [t.strip().upper() for t in out.replace(',', ' ').split()]
                return [t for t in toks if t in PHONEME_VOCAB]
            elif isinstance(out, dict):
                return out.get('phonemes', [])
    except Exception as e:
        print('Ollama call failed', e)
    return []

def build_concat_and_render(jobdir, job, phonemes):
    user = job['user']
    src_dir = os.path.join(WORKSPACE,'users',user,'phonemes')
    listfile = os.path.join(jobdir,'files.txt')
    parts = []
    for p in phonemes:
        f = os.path.join(src_dir, p + '.webm')
        if os.path.exists(f):
            # Convert to wav snippet
            wav = os.path.join(jobdir, p + '.wav')
            subprocess.run(['ffmpeg','-y','-i',f,'-ar','22050','-ac','1',wav], check=False)
            parts.append(wav)
        else:
            print('missing phoneme', p)
    if not parts:
        return False, 'no parts'
    concat_txt = os.path.join(jobdir,'concat.txt')
    with open(concat_txt,'w') as cf:
        for p in parts:
            cf.write(f"file '{p}'\n")
    out_mp3 = os.path.join(jobdir,'output.mp3')
    # Use ffmpeg concat demuxer
    cmd = ['ffmpeg','-y','-f','concat','-safe','0','-i',concat_txt,'-c:a','libmp3lame','-q:a','2', out_mp3]
    try:
        subprocess.run(cmd, check=True)
        return True, out_mp3
    except subprocess.CalledProcessError as e:
        return False, str(e)

if __name__ == '__main__':
    print('Renderer worker started, polling', os.path.join(WORKSPACE,'render_jobs'))
    while True:
        try:
            jobs = list_jobs()
            for jd in jobs:
                job = read_job(jd)
                if not job: continue
                if job.get('status') and job['status'] != 'queued':
                    continue
                job['status'] = 'processing'
                write_job(jd, job)
                phonemes = call_ollama_phoneticize(job['text'])
                if not phonemes:
                    job['status'] = 'failed'
                    job['error'] = 'phoneticize_failed'
                    write_job(jd, job)
                    continue
                ok, result = build_concat_and_render(jd, job, phonemes)
                if ok:
                    job['status'] = 'done'
                    job['output'] = result
                else:
                    job['status'] = 'failed'
                    job['error'] = result
                write_job(jd, job)
        except Exception as e:
            print('Worker error', e)
        time.sleep(5)
