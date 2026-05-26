import argparse
from dataclasses import dataclass
from pathlib import Path

import cv2


@dataclass
class VideoInfo:
	path: Path
	fps: float
	frame_count: int
	width: int
	height: int

	@property
	def duration_seconds(self) -> float:
		if self.fps <= 0:
			return 0.0
		return self.frame_count / self.fps


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Read frames from an input video.")
	parser.add_argument("input_video", help="Path to the source video file.")
	parser.add_argument(
		"--max-frames",
		type=int,
		default=None,
		help="Stop after reading this many sampled frames.",
	)
	parser.add_argument(
		"--sample-every",
		type=int,
		default=1,
		help="Read one frame every N frames. Defaults to 1.",
	)
	return parser


def validate_args(args: argparse.Namespace) -> Path:
	video_path = Path(args.input_video).expanduser().resolve()
	if not video_path.exists():
		raise FileNotFoundError(f"Input video does not exist: {video_path}")
	if args.sample_every <= 0:
		raise ValueError("--sample-every must be greater than 0")
	if args.max_frames is not None and args.max_frames <= 0:
		raise ValueError("--max-frames must be greater than 0")
	return video_path


def open_video(video_path: Path) -> tuple[cv2.VideoCapture, VideoInfo]:
	capture = cv2.VideoCapture(str(video_path))
	if not capture.isOpened():
		raise RuntimeError(f"Failed to open video: {video_path}")

	info = VideoInfo(
		path=video_path,
		fps=float(capture.get(cv2.CAP_PROP_FPS) or 0.0),
		frame_count=int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0),
		width=int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0),
		height=int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0),
	)
	return capture, info


def iter_sampled_frames(capture: cv2.VideoCapture, sample_every: int):
	frame_index = 0
	while True:
		success, frame = capture.read()
		if not success:
			break
		if frame_index % sample_every == 0:
			yield frame_index, frame
		frame_index += 1


def process_video(video_path: Path, sample_every: int, max_frames: int | None) -> int:
	capture, info = open_video(video_path)
	print(
		"Loaded video:",
		{
			"path": str(info.path),
			"fps": round(info.fps, 3),
			"frame_count": info.frame_count,
			"width": info.width,
			"height": info.height,
			"duration_seconds": round(info.duration_seconds, 3),
		},
	)

	processed_frames = 0
	try:
		for frame_index, frame in iter_sampled_frames(capture, sample_every=sample_every):
			processed_frames += 1
			print(f"Read frame_index={frame_index}, shape={frame.shape}")
			if max_frames is not None and processed_frames >= max_frames:
				break
	finally:
		capture.release()

	print(f"Finished reading {processed_frames} sampled frame(s).")
	return processed_frames


def main() -> int:
	parser = build_parser()
	args = parser.parse_args()

	try:
		video_path = validate_args(args)
		process_video(
			video_path=video_path,
			sample_every=args.sample_every,
			max_frames=args.max_frames,
		)
	except Exception as exc:
		parser.exit(status=1, message=f"Error: {exc}\n")

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
