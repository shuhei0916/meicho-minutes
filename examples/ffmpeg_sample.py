import ffmpeg

stream = ffmpeg.input('data/warm-up.mp4').hflip().output('data/output.mp4')
ffmpeg.run(stream)
