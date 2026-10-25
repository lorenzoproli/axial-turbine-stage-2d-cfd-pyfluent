"""Offline encoding of the authoritative M3 interval; no Fluent session or CFD replay."""
from common import *
from cfd import node_processes
import imageio_ffmpeg, subprocess

def main():
    assert project_path(ROOT / 'PROJECT_CLOSURE.json').exists() and (not node_processes())
    meta = json.loads((case_directory('M3_HYBRID35') / 'progress.json').read_text(encoding='utf-8'))
    native = project_path(meta['native_animation_directory'])
    index = json.loads((native / 'frame_index.json').read_text(encoding='utf-8'))
    assert [r['step'] for r in index['frames']] == list(range(2000, 14001, 10))
    directory = native.parent / 'final_delivery'
    directory.mkdir(exist_ok=False)
    output = directory / 'M3_Mach_verified_interval_5T_to_35T.mp4'
    partial = directory / 'encoding.partial.mp4'
    sources = []
    for item in index['frames']:
        p = native / item['manifest']
        assert sha(p) == item['sha256']
        record = json.loads(p.read_text(encoding='utf-8'))
        assert record['configuration']['fixed_ranges']['mach'] == [0.0, 1.2] and record['upper_colour_saturation_disclosed']
        assert abs(record['solution_time_s'] - item['step'] * meta['dt_s']) < 1e-12
        source = record['files'][0]
        q = project_path(source['file'])
        assert q.stat().st_size == source['byte'] and sha(q) == source['sha256']
        sources.append(dict(step=item['step'], solution_time_s=record['solution_time_s'], source_PNG=str(q), byte=source['byte'], sha256=source['sha256'], source_manifest=str(p), manifest_sha256=item['sha256']))
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'warning', '-nostdin', '-n', '-f', 'image2pipe', '-framerate', '25', '-vcodec', 'png', '-i', 'pipe:0', '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-threads', '8', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(partial)]
    jwrite(directory / 'encoding_configuration.json', dict(utc=now(), command=command, renderer='Native Fluent PNGs; offline FFmpeg H.264 encoding only', CFD_steps_executed=0, fixed_Mach_range=[0.0, 1.2], physical_frame_interval_s=10 * meta['dt_s'], FPS=25, first_time_s=sources[0]['solution_time_s'], last_time_s=sources[-1]['solution_time_s'], source_frame_count=len(sources), full_startup=False, periodically_converged=False))
    with (directory / 'ffmpeg.log').open('wb') as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        try:
            for i, item in enumerate(sources):
                with safe_read(project_path(item['source_PNG'])) as stream:
                    shutil.copyfileobj(stream, process.stdin, 1024 * 1024)
                if i % 100 == 0:
                    print('M3_OFFLINE_VIDEO_FRAME', i, '/', len(sources), flush=True)
            process.stdin.close()
            assert process.wait() == 0, 'FFmpeg failed; inspect ffmpeg.log'
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait()
    frames, seconds = imageio_ffmpeg.count_frames_and_secs(str(partial))
    assert frames == 1201 and abs(seconds - 48.04) < 0.01
    reader = imageio_ffmpeg.read_frames(str(partial))
    metadata = next(reader)
    reader.close()
    assert metadata['size'] == (1920, 1080) and abs(metadata['fps'] - 25) < 1e-09
    partial.rename(output)
    csvwrite(directory / 'source_frames_SHA256.csv', sources)
    qa = directory / 'visual_review'
    qa.mkdir()
    selection = '+'.join(('eq(n\\,' + str(i) + ')' for i in [0, 10, 600, 1200]))
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-hide_banner', '-loglevel', 'error', '-i', str(output), '-vf', 'select=' + selection, '-vsync', 'vfr', str(qa / 'sample_%02d.png')], check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    receipt = dict(utc=now(), state='AVAILABLE_INTERVAL_ENCODED_INTEGRITY_PASSED_VISUAL_REVIEW_PENDING', run_id='M3_HYBRID35', file=str(output), byte=output.stat().st_size, sha256=sha(output), encoded_frames=frames, playback_seconds=seconds, FPS=25, resolution=[1920, 1080], first_native_step=2000, last_native_step=14000, first_physical_time_s=sources[0]['solution_time_s'], last_physical_time_s=sources[-1]['solution_time_s'], native_frame_interval_s=10 * meta['dt_s'], fixed_Mach_range=[0.0, 1.2], legend_upper_saturation_disclosed=True, CFD_steps_executed=0, encoding_method='Offline FFmpeg H.264 from unchanged native Fluent PNGs; not Fluent Playback', full_from_zero=False, periodicity_confirmed=False, early_replay_frames_used=0, decoded_sample_indices=[0, 10, 600, 1200], decoded_samples=[str(p) for p in sorted(qa.glob('sample_*.png'))])
    jwrite(directory / 'video_manifest.json', receipt)
    append_status('COMPLETED offline encoding and integrity check of the authoritative M3 Mach interval5T–35T:1201 native Fluent PNGs,1920x1080,25 FPS,48.04s,H.264. No Fluent session,solver advancement or auxiliary replay executed. Fixed0-1.2 limits and actual Solution time retained. This clip is explicitly transient/unconfirmed and does not replace the unverified full-from-zero video. Decoded visual samples are ready for inspection. Evidence: ' + str((directory / 'video_manifest.json').relative_to(ROOT)))
    print(json.dumps(receipt, indent=2))
if __name__ == '__main__':
    main()
