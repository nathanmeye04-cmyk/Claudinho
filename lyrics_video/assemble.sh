#!/usr/bin/env bash
# Assemble les morceaux rendus, ajoute l'audio original et encode la version de publication
# (H.264 High, 2 passes ~3,8 Mb/s optimisé grain, AAC 192 kb/s, faststart) – < 100 Mo
set -e; cd "$(dirname "$0")"
printf "file 'chunk_%d.mp4'\n" 0 1 2 3 > frames/list.txt
ffmpeg -v error -y -f concat -safe 0 -i frames/list.txt -c copy frames/video_concat.mp4
ffmpeg -v error -y -i frames/video_concat.mp4 -c:v libx264 -preset slow -b:v 3800k -tune grain \
  -pass 1 -passlogfile frames/p2 -an -f mp4 /dev/null
ffmpeg -v error -y -i frames/video_concat.mp4 -i audio/ou_est_dieu.m4a -map 0:v -map 1:a \
  -c:v libx264 -preset slow -b:v 3800k -maxrate 7M -bufsize 10M -tune grain -profile:v high -pix_fmt yuv420p \
  -pass 2 -passlogfile frames/p2 -c:a aac -b:a 192k -ar 44100 -movflags +faststart -shortest \
  lyrics_video_ou_est_dieu_1080x1920.mp4
