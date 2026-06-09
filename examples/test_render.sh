#!/bin/bash
FFMPEG="/c/Users/asus/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe"
FFPROBE="/c/Users/asus/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffprobe.exe"
VIDEO="c:/Users/asus/Desktop/team/examples/sample_video.mp4"
BGM="c:/Users/asus/Desktop/team/examples/sample_bgm.m4a"
OUT="c:/Users/asus/Desktop/team/examples/output"
mkdir -p "$OUT"

echo "=== Full 3-clip render with transitions, effects, BGM ==="

"$FFMPEG" -y \
  -ss 0 -t 5 -i "$VIDEO" \
  -ss 5 -t 5 -i "$VIDEO" \
  -ss 10 -t 5 -i "$VIDEO" \
  -stream_loop -1 -i "$BGM" \
  -filter_complex "
    [0:v]trim=0:5,setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,zoompan=z='min(zoom+0.15/60,1.15)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=30[c0v];
    [1:v]trim=5:10,setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,hue=s=0[c1v];
    [2:v]trim=10:15,setpts=PTS-STARTPTS,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,vignette=PI/4[c2v];
    [c0v][c1v]xfade=transition=fade:duration=0.8:offset=4.2[xf0];
    [xf0][c2v]xfade=transition=wiperight:duration=0.6:offset=4.4[video_out];
    [0:a]atrim=0:5,asetpts=PTS-STARTPTS,volume=0.8[ac0];
    [1:a]atrim=0:5,asetpts=PTS-STARTPTS,volume=0.8[ac1];
    [2:a]atrim=0:5,asetpts=PTS-STARTPTS,volume=0.8[ac2];
    [ac0][ac1][ac2]concat=n=3:v=0:a=1[voice_mix];
    [3:a]volume=0.3,afade=t=in:st=0:d=2,afade=t=out:st=12:d=3[bgm_processed];
    [voice_mix][bgm_processed]amix=inputs=2:duration=longest[audio_out]
  " \
  -map "[video_out]" -map "[audio_out]" \
  -c:v libx264 -preset fast -b:v 8M -crf 23 \
  -c:a aac -b:a 192k -pix_fmt yuv420p -shortest \
  "$OUT/demo_full.mp4" 2>&1 | tail -5

echo "exit: $?"

echo "=== Verify output ==="
"$FFPROBE" -v quiet -print_format json -show_format -show_streams "$OUT/demo_full.mp4" | python -c "
import sys, json
d = json.load(sys.stdin)
v = [s for s in d['streams'] if s['codec_type']=='video'][0]
a = [s for s in d['streams'] if s['codec_type']=='audio'][0]
print(f\"Video: {v['width']}x{v['height']}, {v['r_frame_rate']}, codec={v['codec_name']}\")
print(f\"Audio: codec={a['codec_name']}, sr={a['sample_rate']}Hz\")
print(f\"Duration: {float(d['format']['duration']):.2f}s\")
"

ls -la "$OUT/demo_full.mp4"
