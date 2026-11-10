#!/usr/bin/env bash
# Retélécharge les plans Mixkit (licence Mixkit, gratuite) utilisés par src/render.py
set -e; cd "$(dirname "$0")"; mkdir -p clips
for i in 2846 33379 41420 40746 25251 26140 4542 32187 46707 9678 4893 9018 924 9673 48490 40654 4701 31942 4331 34372 8864 35830 45246 9317 52452 35873 4629 36985 1086 21168 ; do
  [ -s clips/$i.mp4 ] && continue
  curl -sf -o clips/$i.mp4 "https://assets.mixkit.co/videos/$i/$i-1080.mp4" || curl -sf -o clips/$i.mp4 "https://assets.mixkit.co/videos/$i/$i-720.mp4"
done
