"use client";

type Props = {
  imageDataUrl: string | null;
  active: boolean;
};

export default function LoopingIdle({ imageDataUrl, active }: Props) {
  if (!active || !imageDataUrl) return null;

  return (
    <img
      src={imageDataUrl}
      alt="Idle frame"
      className="absolute inset-0 h-full w-full animate-pulse object-cover opacity-85"
    />
  );
}
